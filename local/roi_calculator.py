"""
roi_calculator.py
ROI 計算工具 — 從 market_data.db 查基準值，自動算 1:X 比例
用途：銷售工具 / 客戶提案 / Telegram 快查

用法：
  python local\roi_calculator.py --species layer_hen --region CN_south
  python local\roi_calculator.py --species broiler --region SEA_thailand
  python local\roi_calculator.py --species finisher_pig --region CN_north
  python local\roi_calculator.py --list-species
  python local\roi_calculator.py --all --format markdown
"""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH      = Path(r"D:\LLM\knowledge\market\market_data.db")
METRICS_PATH = Path(r"D:\LLM\workflows\research-pipeline-v2\configs\species_metrics.yaml")

# ── 產品固定參數 ──────────────────────────────────────────────────────────────
PRODUCT_DOSE_KG_PER_TON = 20      # 每噸飼料添加量（固定）
ROI_RATIO_MIN           = 3       # 最低 1:3
ROI_RATIO_MAX           = 8       # 最高 1:8

# ── 各物種 FCR 改善預期（基於文獻/田間試驗）─────────────────────────────────
# 格式：{species: {kpi_id: improvement_pct}}
IMPROVEMENT_TABLE = {
    "broiler": {
        "FCR":             0.05,   # FCR 改善 5%
        "breast_yield_pct": 0.03,  # 胸肉率 +3%
        "carcass_rate_pct": 0.02,  # 屠體率 +2%
        "mortality_rate":  -0.15,  # 死亡率 -15%
    },
    "layer_hen": {
        "laying_rate":          0.04,   # 產蛋率 +4%
        "FCR":                 0.05,   # 蛋料比改善 5%
        "egg_feed_ratio":      0.05,
        "peak_duration_weeks": 0.10,   # 高峰期延長 10%
        "mortality_rate":     -0.15,
    },
    "finisher_pig": {
        "FCR":                  0.05,
        "carcass_rate":         0.02,
        "slaughter_weight_kg":  0.03,
    },
    "pregnant_sow": {
        "healthy_piglet_rate":       0.05,
        "birth_weight_uniformity":   0.05,
        "weak_piglet_rate":         -0.20,
    },
    "lactating_sow": {
        "grade_a_weaner_rate":       0.05,
        "weaning_weight_uniformity": 0.04,
        "sow_weight_loss":          -0.10,
    },
    "shrimp": {
        "survival_rate":        0.08,
        "FCR":                 0.05,
        "vibrio_reduction_pct": 0.20,
    },
    "tilapia": {
        "survival_rate":             0.06,
        "avg_body_weight_gain_pct":  0.05,
        "FCR":                      0.05,
    },
    "livestock": {
        "ADG_beef_pct":        0.05,
        "FCR_beef":           0.05,
        "milk_yield_kg_per_day": 0.04,
        "FCR_sheep":          0.05,
    },
}

# ── KPI 顯示名稱 ──────────────────────────────────────────────────────────────
KPI_LABELS = {
    "FCR":                   "飼料轉化率 (FCR)",
    "egg_feed_ratio":        "蛋料比",
    "laying_rate":           "產蛋率",
    "peak_duration_weeks":   "產蛋高峰期",
    "mortality_rate":        "死亡率",
    "breast_yield_pct":      "胸肉率",
    "carcass_rate_pct":      "屠體率",
    "carcass_rate":          "屠體率",
    "slaughter_weight_kg":   "出欄體重",
    "healthy_piglet_rate":   "健仔率",
    "weak_piglet_rate":      "弱仔率",
    "survival_rate":         "育成率",
    "vibrio_reduction_pct":  "弧菌降低率",
    "ADG_beef_pct":          "日增重",
    "milk_yield_kg_per_day": "日產奶量",
    "egg_price_per_500g":    "雞蛋價格",
    "live_price_per_500g":   "毛雞收購價",
    "slaughter_price_per_kg":"出欄豬價",
}

SPECIES_LABELS = {
    "broiler":       "肉雞",
    "layer_hen":     "蛋雞",
    "finisher_pig":  "育肥豬",
    "pregnant_sow":  "懷孕母豬",
    "lactating_sow": "哺乳母豬",
    "shrimp":        "白蝦/對蝦",
    "tilapia":       "吳郭魚/羅非魚",
    "livestock":     "肉牛/奶牛/肉羊",
}

REGION_LABELS = {
    "CN_north":        "中國北方",
    "CN_south":        "中國南方",
    "CN_central":      "中國中部",
    "CN_northwest":    "中國西北",
    "CN_all":          "中國全區",
    "TW_all":          "台灣",
    "SEA_vietnam":     "越南",
    "SEA_thailand":    "泰國",
    "SEA_indonesia":   "印尼",
    "SEA_malaysia":    "馬來西亞",
    "SEA_philippines": "菲律賓",
    "GLOBAL":          "全球均值",
}


# ── DB 查詢 ───────────────────────────────────────────────────────────────────

def get_benchmark(conn, species: str, kpi_id: str, region: str) -> dict | None:
    """查詢基準值，優先：指定地區 > CN_all > GLOBAL，credibility 優先"""
    regions_priority = [region, "CN_all", "GLOBAL"]

    for reg in regions_priority:
        row = conn.execute("""
            SELECT value, value_min, value_max, unit, year, credibility,
                   source_title, source_url, region
            FROM market_kpi
            WHERE species=? AND kpi_id=? AND region=?
              AND value IS NOT NULL
              AND confirmed >= 0
            ORDER BY credibility DESC, year DESC
            LIMIT 1
        """, (species, kpi_id, reg)).fetchone()

        if row:
            return dict(row)

    return None


def get_price_benchmark(conn, species: str, region: str) -> dict | None:
    """查詢收益相關價格"""
    price_kpis = {
        "layer_hen":    "egg_price_per_500g",
        "broiler":      "live_price_per_500g",
        "finisher_pig": "slaughter_price_per_kg",
    }
    kpi_id = price_kpis.get(species)
    if not kpi_id:
        return None
    return get_benchmark(conn, species, kpi_id, region)


# ── ROI 計算核心 ──────────────────────────────────────────────────────────────

def calculate_roi(species: str, region: str, conn) -> dict:
    improvements = IMPROVEMENT_TABLE.get(species, {})
    if not improvements:
        return {"error": f"No improvement table for species: {species}"}

    results = []
    roi_values = []

    for kpi_id, improvement_pct in improvements.items():
        bench = get_benchmark(conn, species, kpi_id, region)
        if not bench or bench["value"] is None:
            continue

        baseline = bench["value"]
        improved = baseline * (1 + improvement_pct)
        delta    = improved - baseline

        # 計算收益（僅對有直接價格連結的 KPI）
        revenue_per_ton = None
        price_bench = get_price_benchmark(conn, species, region)

        if price_bench and kpi_id in ("FCR", "egg_feed_ratio"):
            # FCR 改善 → 每噸飼料少用多少 → 節省飼料成本
            # 簡化：FCR 改善 X% → 同樣產出少吃 X% 飼料
            feed_cost = get_benchmark(conn, species, "feed_cost_per_ton", region)
            if feed_cost:
                saved_feed = feed_cost["value"] * abs(improvement_pct)
                revenue_per_ton = saved_feed
            else:
                # 用市場均價估算（CNY 2,800/噸 飼料成本）
                revenue_per_ton = 2800 * abs(improvement_pct)

        elif kpi_id == "laying_rate" and price_bench:
            # 產蛋率提升 → 多產蛋 → 多收益
            # 每隻雞每天多產 improvement_pct 顆蛋
            # 每噸飼料約養 200 隻雞（簡化）
            birds_per_ton = 200
            egg_price = price_bench["value"]  # CNY/500g
            # 每隻每天多 0.04 顆蛋，每顆蛋約 60g
            extra_egg_per_bird_day = 0.04
            extra_revenue_per_bird_day = extra_egg_per_bird_day * (60/500) * egg_price
            revenue_per_ton = extra_revenue_per_bird_day * birds_per_ton * 30  # 月收益

        elif kpi_id == "survival_rate" and price_bench:
            price = price_bench["value"]
            revenue_per_ton = abs(improvement_pct) * price * 50  # 估算每噸養殖數量

        results.append({
            "kpi_id":           kpi_id,
            "kpi_label":        KPI_LABELS.get(kpi_id, kpi_id),
            "baseline":         round(baseline, 3),
            "improved":         round(improved, 3),
            "improvement_pct":  improvement_pct,
            "unit":             bench["unit"] or "",
            "revenue_per_ton":  round(revenue_per_ton, 1) if revenue_per_ton else None,
            "data_source":      bench["source_title"] or "",
            "data_year":        bench["year"],
            "data_region":      bench["region"],
            "credibility":      bench["credibility"],
        })

        if revenue_per_ton:
            roi_values.append(revenue_per_ton)

    # 計算 ROI 比例
    product_cost_per_ton = PRODUCT_DOSE_KG_PER_TON  # 暫以 20 為基數（成本留空）
    total_benefit = sum(roi_values)

    # ROI 區間（保守/樂觀）
    roi_conservative = max(ROI_RATIO_MIN, min(ROI_RATIO_MAX,
                          total_benefit / max(product_cost_per_ton, 1)))
    roi_optimistic   = min(ROI_RATIO_MAX, roi_conservative * 1.3)

    return {
        "species":          species,
        "species_label":    SPECIES_LABELS.get(species, species),
        "region":           region,
        "region_label":     REGION_LABELS.get(region, region),
        "product_dose":     f"{PRODUCT_DOSE_KG_PER_TON}kg/噸飼料",
        "kpi_details":      results,
        "roi_conservative": round(roi_conservative, 1),
        "roi_optimistic":   round(roi_optimistic, 1),
        "roi_display":      f"1:{roi_conservative:.0f} ～ 1:{roi_optimistic:.0f}",
        "data_coverage":    f"{len(results)}/{len(improvements)} KPIs 有基準值",
        "calculated_at":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note":             "ROI 以飼料成本為基準，需填入實際產品成本後校正",
    }


# ── 輸出格式 ──────────────────────────────────────────────────────────────────

def format_markdown(roi: dict) -> str:
    lines = [
        f"## ROI 估算｜{roi['species_label']} × {roi['region_label']}",
        f"",
        f"**添加量**：{roi['product_dose']}",
        f"**ROI 區間**：{roi['roi_display']}",
        f"**資料覆蓋**：{roi['data_coverage']}",
        f"",
        f"### KPI 改善明細",
        f"",
        f"| 指標 | 基準值 | 添加後 | 改善 | 單位 | 來源年份 |",
        f"|------|--------|--------|------|------|----------|",
    ]

    for kpi in roi["kpi_details"]:
        pct = kpi["improvement_pct"]
        pct_str = f"+{pct*100:.0f}%" if pct > 0 else f"{pct*100:.0f}%"
        lines.append(
            f"| {kpi['kpi_label']} | {kpi['baseline']} | {kpi['improved']} "
            f"| {pct_str} | {kpi['unit']} | {kpi['data_year'] or 'N/A'} |"
        )

    lines += [
        f"",
        f"> 計算時間：{roi['calculated_at']}",
        f"> {roi['note']}",
    ]
    return "\n".join(lines)


def format_telegram(roi: dict) -> str:
    lines = [
        f"📊 *ROI 估算*",
        f"物種：{roi['species_label']}",
        f"地區：{roi['region_label']}",
        f"添加量：{roi['product_dose']}",
        f"",
        f"💰 *預期 ROI：{roi['roi_display']}*",
        f"",
        f"主要改善：",
    ]
    for kpi in roi["kpi_details"][:4]:
        pct = kpi["improvement_pct"]
        arrow = "📈" if pct > 0 else "📉"
        pct_str = f"+{pct*100:.0f}%" if pct > 0 else f"{pct*100:.0f}%"
        lines.append(f"  {arrow} {kpi['kpi_label']} {pct_str}")

    lines.append(f"\n資料覆蓋：{roi['data_coverage']}")
    return "\n".join(lines)


# ── 主程式 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--species",      default="",     help="物種 ID")
    parser.add_argument("--region",       default="CN_south", help="地區 ID")
    parser.add_argument("--format",       default="text",
                        choices=["text","markdown","telegram","json"],
                        help="輸出格式")
    parser.add_argument("--all",          action="store_true", help="輸出所有物種")
    parser.add_argument("--list-species", action="store_true", help="列出可用物種")
    parser.add_argument("--output",       default="",     help="輸出到檔案")
    args = parser.parse_args()

    if args.list_species:
        print("可用物種：")
        for sid, label in SPECIES_LABELS.items():
            has_table = sid in IMPROVEMENT_TABLE
            print(f"  {sid:<20} {label}  {'✓' if has_table else '（無改善表）'}")
        print("\n可用地區：")
        for rid, label in REGION_LABELS.items():
            print(f"  {rid:<20} {label}")
        return

    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}")
        print("先執行：python local\\download_market.py")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 檢查 DB 有無數據
    count = conn.execute("SELECT COUNT(*) FROM market_kpi WHERE value IS NOT NULL").fetchone()[0]
    if count == 0:
        print("market_kpi 尚無數據，先執行：python local\\download_market.py")
        print("（GitHub Actions 跑完後才有數據）")
        print()
        print("--- 使用預設改善參數輸出估算框架 ---")

    species_list = list(IMPROVEMENT_TABLE.keys()) if args.all else [args.species]

    if not args.species and not args.all:
        parser.print_help()
        return

    output_lines = []

    for species in species_list:
        if species not in IMPROVEMENT_TABLE:
            print(f"Unknown species: {species}")
            continue

        roi = calculate_roi(species, args.region, conn)

        if "error" in roi:
            print(f"Error: {roi['error']}")
            continue

        if args.format == "json":
            out = json.dumps(roi, ensure_ascii=False, indent=2)
        elif args.format == "markdown":
            out = format_markdown(roi)
        elif args.format == "telegram":
            out = format_telegram(roi)
        else:
            # text
            out = (
                f"\n{'='*50}\n"
                f"物種：{roi['species_label']} | 地區：{roi['region_label']}\n"
                f"添加量：{roi['product_dose']}\n"
                f"ROI：{roi['roi_display']}\n"
                f"資料覆蓋：{roi['data_coverage']}\n"
                f"\nKPI 明細：\n"
            )
            for kpi in roi["kpi_details"]:
                pct = kpi["improvement_pct"]
                pct_str = f"+{pct*100:.0f}%" if pct > 0 else f"{pct*100:.0f}%"
                out += (
                    f"  {kpi['kpi_label']:<20} "
                    f"{kpi['baseline']} → {kpi['improved']} {kpi['unit']} "
                    f"({pct_str})\n"
                )
            out += f"\n{roi['note']}\n"

        output_lines.append(out)
        print(out)

    conn.close()

    if args.output and output_lines:
        Path(args.output).write_text("\n".join(output_lines), encoding="utf-8")
        print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()
