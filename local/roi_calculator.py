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
    # ── 家禽 ──────────────────────────────────────────────────────────────────
    "broiler": {
        "FCR":              0.05,   # 飼料轉化率 -5%
        "breast_yield_pct": 0.03,   # 胸肉率 +3%
        "carcass_rate_pct": 0.02,   # 屠體率 +2%
        "mortality_rate":  -0.15,   # 死亡率 -15%
    },
    "layer_hen": {
        # 料蛋比 + 產蛋率 = 蛋雞 ROI 兩個核心驅動
        "egg_feed_ratio":       0.05,   # 料蛋比改善 5%（核心ROI指標1：節省飼料成本）
        "laying_rate":          0.04,   # 產蛋率 +4%（核心ROI指標2：直接增加收入）
        "peak_duration_weeks":  0.10,   # 高峰期延長 10%（長期收益）
        "mortality_rate":      -0.15,   # 死亡率 -15%
    },
    "breeder_chicken": {
        "fertility_rate":    0.02,
        "hatchability":      0.03,
        "healthy_chick_rate":0.02,
    },
    "duck": {
        "FCR":           0.05,
        "live_weight":   0.03,
        "mortality_rate":-0.15,
    },
    # ── 豬 ────────────────────────────────────────────────────────────────────
    "suckling_piglet": {
        "pre_weaning_mortality": -0.20,  # 死亡率 -20%
        "weaning_weight":         0.05,  # 斷奶體重 +5%
        "litter_weaning_rate":    0.03,  # 存活率 +3%
    },
    "nursery_pig": {
        "FCR":           0.05,
        "ADG":           0.05,
        "diarrhea_rate": -0.20,
        "mortality_rate":-0.20,
    },
    "finisher_pig": {
        "FCR":              0.05,
        "carcass_rate":     0.02,
        "ADG":              0.04,
        "mortality_rate":  -0.15,
    },
    "pregnant_sow": {
        "healthy_piglet_count":   0.05,  # 健仔數 +5%
        "healthy_piglet_weight":  0.04,  # 健仔體重 +4%
        "weak_piglet_rate":      -0.20,  # 弱仔率 -20%
        "stillborn_rate":        -0.15,  # 死胎率 -15%
        "farrowing_rate":         0.02,  # 分娩率 +2%
    },
    "lactating_sow": {
        "grade_a_weaner_rate":       0.05,
        "weaning_weight_uniformity": 0.04,
        "sow_weight_loss":          -0.10,
        "milk_yield_kg_day":         0.04,
    },
    "boar": {
        "sperm_motility":   0.05,
        "abnormality_rate":-0.15,
    },
    # ── 牛 ────────────────────────────────────────────────────────────────────
    "beef_cattle": {
        "FCR":    0.05,
        "ADG":    0.05,
        "carcass_dressing_pct": 0.02,
    },
    "dairy_cow": {
        "milk_yield_kg_per_day": 0.04,
        "fat_pct":               0.03,
        "SCC":                  -0.15,  # 體細胞數 -15% = 乳房炎減少
    },
    # ── 羊 ────────────────────────────────────────────────────────────────────
    "meat_sheep": {
        "FCR":    0.05,
        "ADG":    0.05,
    },
    "wool_sheep": {
        "wool_yield_kg":     0.05,
        "staple_strength_nkt":0.05,
        "lambing_rate":      0.03,
    },
    "meat_goat": {
        "FCR": 0.05,
        "ADG": 0.05,
    },
    "dairy_goat": {
        "milk_yield_kg_per_day": 0.04,
    },
    # ── 蝦 ────────────────────────────────────────────────────────────────────
    "shrimp": {
        "survival_rate":        0.08,
        "FCR":                  0.05,
        "vibrio_reduction_pct": 0.20,
    },
    "tiger_prawn": {
        "survival_rate": 0.07,
        "FCR":           0.05,
    },
    "giant_freshwater_prawn": {
        "survival_rate": 0.07,
        "FCR":           0.05,
    },
    # ── 魚 ────────────────────────────────────────────────────────────────────
    "tilapia": {
        "survival_rate":  0.06,
        "FCR":            0.05,
        "ADG":            0.05,
    },
    "milkfish": {
        "survival_rate":  0.05,
        "FCR":            0.05,
    },
    "grey_mullet": {
        "survival_rate":  0.05,
        "FCR":            0.05,
        "roe_yield_pct":  0.05,
    },
    "pangasius_catfish": {
        "survival_rate":  0.06,
        "FCR":            0.05,
    },
    "channel_catfish": {
        "survival_rate":  0.06,
        "FCR":            0.05,
    },
    "largemouth_catfish": {
        "survival_rate":  0.06,
        "FCR":            0.05,
    },
    "largemouth_bass": {
        "survival_rate":  0.06,
        "FCR":            0.05,
    },
    "grass_carp": {
        "survival_rate":  0.05,
        "FCR":            0.05,
    },
    "grouper": {
        "survival_rate":  0.07,
        "FCR":            0.05,
    },
    "atlantic_salmon": {
        "survival_rate":  0.05,
        "FCR":            0.04,
        "ADG":            0.05,
    },
    "seabass": {
        "survival_rate":  0.05,
        "FCR":            0.05,
    },
    "rice_field_eel": {
        "survival_rate":  0.07,
        "FCR":            0.05,
    },
    "pond_loach": {
        "survival_rate":  0.06,
        "FCR":            0.05,
    },
    # ── 毛皮 ──────────────────────────────────────────────────────────────────
    "mink": {
        "kit_survival_rate":       0.05,
        "kits_per_female":         0.04,
        "pelt_quality_grade_A_pct":0.05,
    },
    "fox": {
        "kits_per_female":         0.04,
        "pelt_quality_grade_A_pct":0.05,
    },
    "rabbit": {
        "FCR":              0.05,
        "ADG":              0.05,
        "mortality_rate":  -0.15,
        "kits_per_doe_year":0.04,
    },
    # ── 特種 ──────────────────────────────────────────────────────────────────
    "deer": {
        "velvet_yield_kg": 0.08,
        "ADG":             0.05,
    },
    "crocodile": {
        "survival_rate":            0.05,
        "skin_quality_grade_A_pct": 0.05,
    },
    "wild_boar_hybrid": {
        "FCR": 0.05,
        "ADG": 0.05,
    },
}

# ── KPI 顯示名稱 ──────────────────────────────────────────────────────────────
KPI_LABELS = {
    "FCR":                      "飼料轉化率 (FCR)",
    "egg_feed_ratio":           "蛋料比",
    "laying_rate":              "產蛋率",
    "hen_day_production":       "當日產蛋率",
    "peak_duration_weeks":      "產蛋高峰期",
    "eggshell_strength":        "蛋殼強度",
    "egg_weight_g":             "蛋重",
    "mortality_rate":           "死亡率",
    "breast_yield_pct":         "胸肉率",
    "carcass_rate_pct":         "屠體率",
    "carcass_rate":             "屠體率",
    "carcass_dressing_pct":     "屠體率",
    "slaughter_weight_kg":      "出欄體重",
    "slaughter_weight":         "出欄體重",
    "live_weight":              "出欄體重",
    "ADG":                      "日增重",
    "healthy_piglet_rate":      "健仔率",
    "healthy_piglet_count":     "健仔數",
    "healthy_piglet_weight":    "健仔體重",
    "weak_piglet_rate":         "弱仔率",
    "stillborn_rate":           "死胎率",
    "birth_weight_uniformity":  "初生體重整齊度",
    "litter_size":              "窩產仔數",
    "farrowing_rate":           "分娩率",
    "wean_to_estrus_days":      "斷奶至發情天數",
    "npe_per_sow_year":         "每母豬年斷奶仔豬數",
    "pre_weaning_mortality":    "哺乳期死亡率",
    "weaning_weight":           "斷奶體重",
    "litter_weaning_rate":      "哺乳期存活率",
    "birth_weight":             "初生體重",
    "grade_a_weaner_rate":      "優質斷奶仔豬率",
    "weaning_weight_uniformity":"斷奶整齊度",
    "sow_weight_loss":          "哺乳期母豬體重損失",
    "milk_yield_kg_day":        "日產奶量",
    "litter_gain_g_day":        "窩日增重",
    "sperm_motility":           "精子活力",
    "semen_volume":             "射精量",
    "abnormality_rate":         "精子畸形率",
    "milk_yield_kg_per_day":    "日產奶量",
    "305d_milk_yield":          "305天泌乳量",
    "fat_pct":                  "乳脂率",
    "protein_pct":              "乳蛋白率",
    "SCC":                      "體細胞數",
    "conception_rate":          "受孕率",
    "lambing_rate":             "產羔率",
    "wool_yield_kg":            "羊毛產量",
    "wool_fibre_diameter":      "羊毛纖維直徑",
    "staple_length_mm":         "毛辮長度",
    "staple_strength_nkt":      "毛辮強度",
    "clean_fleece_pct":         "淨毛率",
    "survival_rate":            "育成率/存活率",
    "harvest_cycle_days":       "養殖週期",
    "vibrio_reduction_pct":     "弧菌降低率",
    "EMS_resistance":           "EMS抗性",
    "stocking_density":         "放養密度",
    "market_weight":            "收穫體重",
    "roe_yield_pct":            "卵巢率（烏魚子）",
    "streptococcus_survival_rate":"鏈球菌挑戰存活率",
    "kit_survival_rate":        "仔獸存活率",
    "kits_per_female":          "每母獸產仔數",
    "kits_per_doe_year":        "每母兔年產仔數",
    "pelt_quality_grade_A_pct": "頂級毛皮比例",
    "grow_out_days":            "育成天數",
    "velvet_yield_kg":          "鹿茸產量",
    "skin_quality_grade_A_pct": "頂級皮革比例",
    "fertility_rate":           "受精率",
    "hatchability":             "孵化率",
    "healthy_chick_rate":       "健雛率",
    "chicks_per_hen_housed":    "每母雞產健雛數",
    "marbling_score":           "大理石花紋評分",
    "rearing_cycle_days":       "育肥週期",
    "diarrhea_rate":            "腹瀉率",
    "weaning_to_finish_days":   "保育天數",
    "backfat_mm":               "背脂厚度",
}

SPECIES_LABELS = {
    # 家禽
    "broiler":              "肉雞",
    "layer_hen":            "蛋雞",
    "breeder_chicken":      "種雞",
    "duck":                 "肉鴨",
    "goose":                "鵝",
    # 豬
    "suckling_piglet":      "哺乳仔豬",
    "nursery_pig":          "保育豬",
    "finisher_pig":         "育肥豬",
    "pregnant_sow":         "懷孕母豬",
    "lactating_sow":        "哺乳母豬",
    "boar":                 "公豬",
    # 牛
    "beef_cattle":          "肉牛",
    "dairy_cow":            "奶牛",
    # 羊
    "meat_sheep":           "肉羊",
    "wool_sheep":           "取毛綿羊",
    "meat_goat":            "肉山羊",
    "dairy_goat":           "乳山羊",
    # 蝦
    "shrimp":               "南美白對蝦",
    "tiger_prawn":          "草蝦/斑節對蝦",
    "giant_freshwater_prawn":"淡水長臂大蝦（泰國蝦）",
    # 魚
    "tilapia":              "吳郭魚/羅非魚",
    "milkfish":             "虱目魚",
    "grey_mullet":          "烏魚/鯔魚",
    "pangasius_catfish":    "巴沙魚/越南鯰",
    "channel_catfish":      "斑點叉尾鮰",
    "largemouth_catfish":   "大口鯰",
    "largemouth_bass":      "加州鱸",
    "grass_carp":           "草魚",
    "grouper":              "石斑魚",
    "atlantic_salmon":      "大西洋鮭",
    "seabass":              "海鱸",
    "rice_field_eel":       "黃鱔",
    "pond_loach":           "泥鰍",
    # 毛皮
    "mink":                 "水貂",
    "fox":                  "狐",
    "rabbit":               "兔",
    # 特種
    "deer":                 "鹿",
    "crocodile":            "鱷魚",
    "wild_boar_hybrid":     "野豬雜交",
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

        # ── ROI 金額估算（每噸飼料）────────────────────────────────────────
        # 蛋雞：料蛋比是核心 — 改善5% = 同產出省5%飼料成本
        # 蛋雞：產蛋率是核心 — +4% = 多產4顆蛋/百隻/天
        # 無市場價格時用保守行業均值估算
        FEED_COST_DEFAULTS = {
            # 物種: 每噸飼料成本（CNY）
            "layer_hen":      3200,   # 蛋雞料
            "broiler":        3000,   # 肉雞料
            "finisher_pig":   2800,   # 豬料
            "nursery_pig":    3500,
            "suckling_piglet":4500,
            "beef_cattle":    2600,
            "dairy_cow":      2800,
            "shrimp":         7000,   # 蝦料高
            "tilapia":        4500,
            "default":        3000,
        }
        feed_cost_default = FEED_COST_DEFAULTS.get(species, FEED_COST_DEFAULTS["default"])
        feed_cost_bench = get_benchmark(conn, species, "feed_cost_per_ton", region)
        feed_cost = feed_cost_bench["value"] if feed_cost_bench else feed_cost_default

        if kpi_id == "egg_feed_ratio":
            # 料蛋比改善 X% → 每噸飼料省 X% 飼料成本
            # 例：料蛋比 2.1→2.205，改善5% → 省 CNY 3200×5% = 160元/噸
            revenue_per_ton = feed_cost * abs(improvement_pct)

        elif kpi_id == "laying_rate":
            # 產蛋率 +4% → 每噸飼料（養約180隻蛋雞）多 180×0.04=7.2顆蛋/天
            # 每顆蛋重63g，蛋價 CNY 5.5/500g = 0.0693元/g
            # 月多收益 = 7.2顆 × 63g × (5.5/500) × 30天 ≈ 150元/噸
            birds_per_ton = 180
            egg_price_per_500g = 5.5   # 中國南方均值，無市場數據時使用
            if price_bench:
                egg_price_per_500g = price_bench["value"]
            extra_eggs_per_day = birds_per_ton * improvement_pct
            revenue_per_day = extra_eggs_per_day * 63 / 500 * egg_price_per_500g
            revenue_per_ton = revenue_per_day * 30  # 月收益換算

        elif kpi_id in ("FCR",) and species != "layer_hen":
            # 非蛋雞的 FCR 改善 = 省飼料成本
            revenue_per_ton = feed_cost * abs(improvement_pct)

        elif kpi_id == "survival_rate":
            # 存活率提升 = 少損失動物
            # 用飼料成本×改善幅度作保守估算
            revenue_per_ton = feed_cost * abs(improvement_pct) * 0.5

        elif kpi_id in ("healthy_piglet_count", "kits_per_female", "kits_per_doe_year",
                        "litter_size", "npe_per_sow_year"):
            # 產仔數提升 = 直接增加收入（保守：飼料成本的倍數）
            revenue_per_ton = feed_cost * abs(improvement_pct) * 0.8

        elif kpi_id in ("milk_yield_kg_per_day", "milk_yield_kg_day",
                        "305d_milk_yield", "wool_yield_kg", "velvet_yield_kg",
                        "roe_yield_pct"):
            # 產品量提升 = 直接收益
            revenue_per_ton = feed_cost * abs(improvement_pct) * 0.6

        elif kpi_id in ("mortality_rate", "pre_weaning_mortality", "diarrhea_rate",
                        "weak_piglet_rate", "stillborn_rate"):
            # 死亡率降低 = 少損失（以飼料成本的10%保守估算）
            revenue_per_ton = feed_cost * abs(improvement_pct) * 0.3

        elif kpi_id in ("peak_duration_weeks", "harvest_cycle_days"):
            # 週期延長/縮短 = 間接收益（保守）
            revenue_per_ton = feed_cost * abs(improvement_pct) * 0.2

        elif kpi_id in ("pelt_quality_grade_A_pct", "skin_quality_grade_A_pct"):
            # 皮毛品質提升 = 直接溢價
            revenue_per_ton = feed_cost * abs(improvement_pct) * 0.8

        if price_bench and kpi_id == "survival_rate":
            price = price_bench["value"]
            revenue_per_ton = abs(improvement_pct) * price * 50

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
