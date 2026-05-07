"""
修復兩個問題：
1. source_type mapping (field_survey/epidemiology/intervention_trial -> 合法值)
2. 確保 DB 存在再寫入
3. import batch1_benchmarks
"""
import pathlib, sys, logging, sqlite3
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── source_type 映射表 ─────────────────────────────────────────
SOURCE_TYPE_MAP = {
    "field_survey":       "gov_stats",
    "epidemiology":       "gov_stats",
    "intervention_trial": "academic_background",
    "baseline":           "academic_background",
    "disease_penalty":    "academic_background",
    "market_report":      "market_report",
    # 合法值直接通過
    "gov_stats":          "gov_stats",
    "industry_media":     "industry_media",
    "vendor_whitepaper":  "vendor_whitepaper",
    "academic_background":"academic_background",
    "social":             "social",
}

def fix_source_type(r):
    st = r.get("source_type", "academic_background")
    r["source_type"] = SOURCE_TYPE_MAP.get(st, "academic_background")
    return r

# ── 確保 DB 存在 ──────────────────────────────────────────────
DB_PATH = pathlib.Path(r"D:\LLM\knowledge\market\market_data.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# 先載入 seed_benchmarks 模組（用 importlib 避免路徑問題）
import importlib.util
spec = importlib.util.spec_from_file_location(
    "seed_benchmarks",
    r"D:\LLM\workflows\research-pipeline-v2\local\seed_benchmarks.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# 確認 DB_PATH 一致
mod.DB_PATH = DB_PATH

# ── 載入 batch1 ───────────────────────────────────────────────
batch1_path = pathlib.Path(r"D:\LLM\workflows\research-pipeline-v2\batch1_benchmarks.py")
ns = {}
exec(batch1_path.read_text(encoding="utf-8"), ns)
batch1 = ns["batch1_benchmarks"]

# 轉換 batch1 schema -> seed schema
converted = []
for r in batch1:
    converted.append({
        "kpi_id":          r["kpi_id"],
        "species":         r["species"],
        "region":          r["region"],
        "value":           r["value_mid"],
        "value_min":       r["value_low"],
        "value_max":       r["value_high"],
        "unit":            r["unit"],
        "credibility":     4 if r["data_quality"] == "A" else 3,
        "source_type":     SOURCE_TYPE_MAP.get(r.get("metric_type","academic_background"), "academic_background"),
        "source_title":    r["source"],
        "note":            r.get("notes", ""),
        "production_stage": r.get("condition", ""),
        "year":            2023,
    })

print(f"batch1 converted: {len(converted)} records")

# ── fix MG patch source_type in BENCHMARKS ───────────────────
for r in mod.BENCHMARKS:
    fix_source_type(r)

# ── append batch1 ─────────────────────────────────────────────
original_len = len(mod.BENCHMARKS)
mod.BENCHMARKS.extend(converted)
print(f"BENCHMARKS: {original_len} + {len(converted)} = {len(mod.BENCHMARKS)}")

# ── 建立 DB 表（若不存在）────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
conn.executescript("""
CREATE TABLE IF NOT EXISTS market_kpi (
    id              TEXT PRIMARY KEY,
    region          TEXT NOT NULL DEFAULT 'GLOBAL',
    country         TEXT NOT NULL DEFAULT '',
    species         TEXT NOT NULL,
    production_stage TEXT,
    kpi_id          TEXT NOT NULL,
    value           REAL NOT NULL,
    value_min       REAL,
    value_max       REAL,
    unit            TEXT NOT NULL,
    year            INTEGER NOT NULL DEFAULT 2022,
    credibility     INTEGER NOT NULL DEFAULT 3
                    CHECK(credibility BETWEEN 1 AND 5),
    source_type     TEXT NOT NULL DEFAULT 'academic_background'
                    CHECK(source_type IN (
                        'gov_stats','industry_media','vendor_whitepaper',
                        'academic_background','market_report','social')),
    source_url      TEXT NOT NULL DEFAULT '',
    source_title    TEXT NOT NULL DEFAULT '',
    raw_text        TEXT NOT NULL DEFAULT '',
    language        TEXT NOT NULL DEFAULT 'en',
    confirmed       INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL
);
""")
conn.commit()
conn.close()
print(f"DB ready: {DB_PATH}")

# ── 執行 seed ─────────────────────────────────────────────────
mod.seed(dry_run=False, species_filter="")
