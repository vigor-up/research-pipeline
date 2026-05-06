"""
download_market.py
從 Cloudflare R2 下載市場數據 → Qwen3.6 抽取數值 → 寫入 market_data.db
EVO-X2 本地執行，或由 tg_commander.py 按鈕觸發

用法：
  python local\download_market.py
  python local\download_market.py --force-reanalyze   # 重新分析已存在記錄
  python local\download_market.py --species layer_hen # 只處理特定物種
  python local\download_market.py --dry-run           # 只印不寫入DB
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import logging
import argparse
import re
from datetime import datetime
from pathlib import Path

import boto3
import httpx
import yaml
from botocore.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)

# ── 路徑設定 ──────────────────────────────────────────────────────────────────
DB_PATH       = Path(r"D:\LLM\knowledge\market\market_data.db")
METRICS_PATH  = Path(r"D:\LLM\workflows\research-pipeline-v2\configs\species_metrics.yaml")
QWEN_ENDPOINT = "http://127.0.0.1:1234/v1/chat/completions"
CACHE_PATH    = Path(r"D:\LLM\knowledge\market\latest_raw.json")

# ── R2 設定 ───────────────────────────────────────────────────────────────────
def get_r2():
    acct = os.environ.get("CF_R2_ACCOUNT_ID") or os.environ.get("R2_ACCOUNT_ID")
    key  = os.environ.get("CF_R2_ACCESS_KEY_ID") or os.environ.get("R2_ACCESS_KEY_ID")
    sec  = os.environ.get("CF_R2_SECRET_ACCESS_KEY") or os.environ.get("R2_SECRET_ACCESS_KEY")
    bkt  = os.environ.get("CF_R2_BUCKET_NAME") or os.environ.get("R2_BUCKET", "richtrong-collect")
    if not all([acct, key, sec]):
        sys.exit("R2 env vars missing: CF_R2_ACCOUNT_ID / CF_R2_ACCESS_KEY_ID / CF_R2_SECRET_ACCESS_KEY")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{acct}.r2.cloudflarestorage.com",
        aws_access_key_id=key,
        aws_secret_access_key=sec,
        region_name="auto",
        config=Config(retries={"max_attempts": 3}),
    ), bkt


# ── 下載 R2 最新市場數據 ──────────────────────────────────────────────────────
def download_from_r2(force: bool = False) -> dict:
    if CACHE_PATH.exists() and not force:
        age_hours = (datetime.now().timestamp() - CACHE_PATH.stat().st_mtime) / 3600
        if age_hours < 6:
            log.info(f"Using cache ({age_hours:.1f}h old): {CACHE_PATH}")
            with open(CACHE_PATH, encoding="utf-8") as f:
                return json.load(f)

    log.info("Downloading market_data/latest.json from R2...")
    s3, bucket = get_r2()
    obj = s3.get_object(Bucket=bucket, Key="market_data/latest.json")
    data = json.loads(obj["Body"].read().decode("utf-8"))

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"Downloaded: kpi={data['market_kpi_total']} competitor={data['competitor_total']}")
    return data


# ── Qwen 數值抽取 ─────────────────────────────────────────────────────────────
EXTRACT_SYSTEM = """You are a data extraction specialist for animal nutrition market data.
Extract numerical values from text. Output ONLY valid JSON, no preamble.
If no clear numerical value found for the metric, set value to null.
Always output in this exact schema."""

EXTRACT_TEMPLATE = """Extract market data from this text.

Species: {species}
KPI: {kpi_id} ({kpi_label})
Expected unit: {unit}
Region: {region}
Year context: {year}

Text: {raw_text}

Output JSON:
{{
  "value": <number or null>,
  "value_min": <number or null>,
  "value_max": <number or null>,
  "unit": "<unit string>",
  "year": <integer or null>,
  "confidence": <1-5>,
  "extracted_fragment": "<the exact phrase containing the number>"
}}"""


def qwen_extract(record: dict, metrics_cfg: dict) -> dict:
    species = record.get("species", "unknown")
    kpi_id  = record.get("kpi_id", "")
    raw     = record.get("raw_text", "")

    if not raw or len(raw) < 20:
        return {"value": None, "confidence": 0}

    # 找 kpi 的 unit
    unit = ""
    for sp_data in metrics_cfg.get("species_market_params", {}).values():
        for kpi in sp_data.get("kpis", []):
            if kpi["id"] == kpi_id:
                unit = kpi.get("unit", "")
                kpi_label = kpi.get("label", kpi_id)
                break

    prompt = EXTRACT_TEMPLATE.format(
        species=species,
        kpi_id=kpi_id,
        kpi_label=kpi_label if "kpi_label" in dir() else kpi_id,
        unit=unit,
        region=record.get("region", ""),
        year=record.get("year", datetime.now().year),
        raw_text=raw[:800],
    )

    try:
        resp = httpx.post(
            QWEN_ENDPOINT,
            json={
                "model": "Qwen3.6-35B-A3B-Q6_K.gguf",
                "messages": [
                    {"role": "system", "content": EXTRACT_SYSTEM},
                    {"role": "user",   "content": prompt},
                ],
                "max_tokens": 300,
                "temperature": 0.1,
            },
            timeout=45,
        )
        text = resp.json()["choices"][0]["message"]["content"].strip()
        # 清理可能的 markdown
        text = re.sub(r"```json|```", "", text).strip()
        return json.loads(text)
    except Exception as e:
        log.debug(f"Qwen extract error [{kpi_id}]: {e}")
        return {"value": None, "confidence": 0}


# ── DB 操作 ───────────────────────────────────────────────────────────────────
def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def record_exists(conn, record_id: str) -> bool:
    row = conn.execute(
        "SELECT id FROM market_kpi WHERE id=?", (record_id,)
    ).fetchone()
    return row is not None


def upsert_market_kpi(conn, record: dict, extracted: dict, dry_run: bool):
    value     = extracted.get("value")
    value_min = extracted.get("value_min")
    value_max = extracted.get("value_max")
    unit      = extracted.get("unit") or record.get("unit")
    year      = extracted.get("year") or record.get("year")

    row = {
        "id":             record["id"],
        "region":         record.get("region", ""),
        "country":        _region_to_country(record.get("region", "")),
        "species":        record.get("species", ""),
        "kpi_id":         record.get("kpi_id", ""),
        "value":          value,
        "value_min":      value_min,
        "value_max":      value_max,
        "unit":           unit,
        "year":           year,
        "credibility":    record.get("credibility", 2),
        "source_type":    record.get("source_type", ""),
        "source_url":     record.get("source_url", ""),
        "source_title":   record.get("source_title", ""),
        "raw_text":       record.get("raw_text", "")[:2000],
        "language":       record.get("language", "en"),
        "confirmed":      0,
        "updated_at":     datetime.now().isoformat(),
    }

    if dry_run:
        if value is not None:
            log.info(f"  [DRY] {row['species']} | {row['kpi_id']} | {value} {unit} | {row['region']}")
        return

    conn.execute("""
        INSERT OR REPLACE INTO market_kpi
        (id, region, country, species, kpi_id, value, value_min, value_max,
         unit, year, credibility, source_type, source_url, source_title,
         raw_text, language, confirmed, updated_at)
        VALUES
        (:id, :region, :country, :species, :kpi_id, :value, :value_min, :value_max,
         :unit, :year, :credibility, :source_type, :source_url, :source_title,
         :raw_text, :language, :confirmed, :updated_at)
    """, row)


def upsert_competitor(conn, record: dict, dry_run: bool):
    if dry_run:
        log.info(f"  [DRY] competitor: {record.get('competitor_name')} | {record.get('species')} | {record.get('claim_metric')}")
        return

    conn.execute("""
        INSERT OR REPLACE INTO competitor_market
        (id, competitor_id, competitor_name, region, market_claim,
         claim_metric, claim_value, claim_unit, species,
         source_url, source_type, credibility, year, raw_text,
         confirmed, created_at)
        VALUES
        (:id, :competitor_id, :competitor_name, :region, :market_claim,
         :claim_metric, :claim_value, :claim_unit, :species,
         :source_url, :source_type, :credibility, :year, :raw_text,
         :confirmed, :created_at)
    """, {
        "id":              record["id"],
        "competitor_id":   record.get("competitor_id", ""),
        "competitor_name": record.get("competitor_name", ""),
        "region":          record.get("region", "GLOBAL"),
        "market_claim":    record.get("market_claim", "")[:2000],
        "claim_metric":    record.get("claim_metric"),
        "claim_value":     record.get("claim_value"),
        "claim_unit":      record.get("claim_unit"),
        "species":         record.get("species", ""),
        "source_url":      record.get("source_url", ""),
        "source_type":     record.get("source_type", ""),
        "credibility":     record.get("credibility", 3),
        "year":            record.get("year", datetime.now().year),
        "raw_text":        record.get("raw_text", "")[:2000],
        "confirmed":       0,
        "created_at":      datetime.now().isoformat(),
    })


def _region_to_country(region: str) -> str:
    mapping = {
        "CN_north": "CN", "CN_south": "CN",
        "CN_central": "CN", "CN_northwest": "CN", "CN_all": "CN",
        "TW_all": "TW",
        "SEA_vietnam": "VN", "SEA_thailand": "TH",
        "SEA_indonesia": "ID", "SEA_malaysia": "MY",
        "SEA_philippines": "PH",
        "GLOBAL": "",
    }
    return mapping.get(region, "")


# ── 主程式 ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-reanalyze", action="store_true",
                        help="重新分析已存在的記錄")
    parser.add_argument("--force-download",  action="store_true",
                        help="強制重新下載 R2")
    parser.add_argument("--species",         default="",
                        help="只處理特定物種 (e.g. layer_hen)")
    parser.add_argument("--dry-run",         action="store_true",
                        help="只印不寫入DB")
    args = parser.parse_args()

    # 載入設定
    with open(METRICS_PATH, encoding="utf-8") as f:
        metrics_cfg = yaml.safe_load(f)

    # 下載
    data = download_from_r2(force=args.force_download)

    market_records     = data.get("market_kpi", [])
    competitor_records = data.get("competitor_market", [])

    # 物種過濾
    if args.species:
        market_records = [r for r in market_records if r.get("species") == args.species]
        competitor_records = [r for r in competitor_records if r.get("species") == args.species]
        log.info(f"Filtered to species={args.species}: kpi={len(market_records)} competitor={len(competitor_records)}")

    conn = db_connect() if not args.dry_run else None

    # ── 處理 market_kpi ────────────────────────────────────────────────────
    log.info(f"Processing {len(market_records)} market KPI records...")
    new_count = skip_count = error_count = 0

    for i, record in enumerate(market_records):
        rid = record.get("id", "")

        if not args.dry_run and not args.force_reanalyze:
            if record_exists(conn, rid):
                skip_count += 1
                continue

        # Qwen 抽取數值
        extracted = qwen_extract(record, metrics_cfg)

        if not args.dry_run:
            try:
                upsert_market_kpi(conn, record, extracted, dry_run=False)
                new_count += 1
            except Exception as e:
                log.warning(f"DB write error [{rid}]: {e}")
                error_count += 1
        else:
            upsert_market_kpi(None, record, extracted, dry_run=True)
            new_count += 1

        # 進度
        if (i + 1) % 20 == 0:
            log.info(f"  Progress: {i+1}/{len(market_records)} | new={new_count} skip={skip_count}")

        time.sleep(0.3)  # Qwen rate

    # ── 處理 competitor_market ────────────────────────────────────────────
    log.info(f"Processing {len(competitor_records)} competitor records...")
    comp_new = 0

    for record in competitor_records:
        rid = record.get("id", "")

        if not args.dry_run and not args.force_reanalyze:
            if conn.execute("SELECT id FROM competitor_market WHERE id=?", (rid,)).fetchone():
                continue

        try:
            upsert_competitor(conn, record, dry_run=args.dry_run)
            comp_new += 1
        except Exception as e:
            log.warning(f"Competitor DB error [{rid}]: {e}")

    # ── 提交 + 統計 ────────────────────────────────────────────────────────
    if not args.dry_run and conn:
        conn.commit()

        total_kpi  = conn.execute("SELECT COUNT(*) FROM market_kpi").fetchone()[0]
        with_value = conn.execute("SELECT COUNT(*) FROM market_kpi WHERE value IS NOT NULL").fetchone()[0]
        total_comp = conn.execute("SELECT COUNT(*) FROM competitor_market").fetchone()[0]

        conn.close()

        log.info("=" * 50)
        log.info(f"market_kpi  total={total_kpi} | with_value={with_value} | new={new_count} | skip={skip_count} | error={error_count}")
        log.info(f"competitor  total={total_comp} | new={comp_new}")
        log.info(f"DB: {DB_PATH}")
    else:
        log.info(f"[DRY RUN] Would write: kpi={new_count} competitor={comp_new}")


if __name__ == "__main__":
    main()
