"""
seed_benchmarks.py  v2.0
一次性建立經濟動物生產效率基準值資料庫
精確度目標：全球前 10%，可作為 A/B 對照試驗的可信基準
資料來源層級：
  L5 = 品種公司官方手冊（Cobb/Aviagen/PIC/Hy-Line/Hendrix）
  L4 = 同行評審 meta-analysis / systematic review
  L3 = 單篇 RCT 田間試驗 / 行業協會報告
  L2 = 廠商白皮書 / 行業媒體
原則：
  - 生物性上限固定（FCR/產蛋率/存活率）= 種一次永久有效
  - 市場行情（價格/成本）= 由 market_collector 定期更新
  - 每筆含 value_min/value_max = AB試驗可用作對照組信賴區間
  - 物種無限擴充：只需在 BENCHMARKS 加 dict
用法：
  python local\\seed_benchmarks.py
  python local\\seed_benchmarks.py --dry-run
  python local\\seed_benchmarks.py --species broiler
  python local\\seed_benchmarks.py --reset
"""

import sqlite3
import argparse
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from collections import Counter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DB_PATH = Path(r"D:\LLM\knowledge\market\market_data.db")
NOW = datetime.now().isoformat()


def rid(*args):
    key = "|".join(str(a) for a in args)
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def b(species, kpi_id, value, unit, *,
      value_min=None, value_max=None,
      region="GLOBAL", production_stage=None,
      year=2022, credibility=4,
      source_type="academic_background",
      source_title="", note=""):
    return dict(
        species=species, kpi_id=kpi_id,
        value=value, value_min=value_min, value_max=value_max,
        unit=unit, region=region, production_stage=production_stage,
        year=year, credibility=credibility,
        source_type=source_type, source_title=source_title, note=note,
    )


BENCHMARKS = []

# ══════════════════════════════════════════════════════════════════════════════
# 一、家禽
# ══════════════════════════════════════════════════════════════════════════════

# ── 肉雞 (Broiler) ────────────────────────────────────────────────────────────
BENCHMARKS += [
    b("broiler","FCR",1.65,"ratio",value_min=1.55,value_max=1.80,
      production_stage="finisher_42d",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Cobb500 Broiler Performance & Nutrition Supplement 2022",
      note="Mixed sex 42d. Top 10%=1.55-1.60. AB對照組建議設1.72(CN平均)"),
    b("broiler","FCR",1.72,"ratio",value_min=1.62,value_max=1.85,
      region="CN_all",production_stage="finisher_42d",year=2023,
      source_type="industry_media",
      source_title="中國肉雞產業發展報告2023",
      note="中國商業平均，白羽/黃羽加權"),
    b("broiler","ADG",68.0,"g/day",value_min=62.0,value_max=75.0,
      production_stage="finisher_42d",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Ross 308 Broiler Performance Objectives 2022",
      note="0-42d mixed sex ADG"),
    b("broiler","live_weight",2800,"g",value_min=2500,value_max=3200,
      production_stage="market_42d",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Cobb500 Broiler Performance & Nutrition Supplement 2022",
      note="黃羽雞中國市場通常1.5-2.5kg"),
    b("broiler","breast_yield_pct",24.5,"%",value_min=22.0,value_max=27.0,
      production_stage="finisher_42d",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Cobb500 Broiler Performance & Nutrition Supplement 2022",
      note="Deboned breast/live weight. Top 10% >26%"),
    b("broiler","carcass_rate_pct",75.5,"%",value_min=73.0,value_max=77.5,
      production_stage="finisher_42d",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Ross 308 Broiler Performance Objectives 2022",
      note="EU style ready-to-cook carcass"),
    b("broiler","mortality_rate",3.5,"%",value_min=2.0,value_max=5.5,
      production_stage="finisher_42d",
      source_title="Poultry Science 2022 Global Broiler Review",
      note="Top 10% < 2.5%"),
]

# ── 蛋雞 (Layer Hen) ──────────────────────────────────────────────────────────
BENCHMARKS += [
    b("layer_hen","laying_rate",95.0,"%",value_min=93.0,value_max=97.0,
      production_stage="peak_280_320d",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Hy-Line W-36 Commercial Management Guide 2022",
      note="Peak 280-320d white egg. Brown egg peak ~94%"),
    b("layer_hen","laying_rate",90.5,"%",value_min=88.0,value_max=93.0,
      production_stage="full_cycle_hen_housed",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Lohmann Brown-Classic Layer Management Guide 2022",
      note="Hen-housed 18-80週均值，top 10% commercial"),
    b("layer_hen","laying_rate",88.0,"%",value_min=85.0,value_max=91.0,
      region="CN_all",production_stage="full_cycle_hen_housed",year=2023,
      source_type="industry_media",
      source_title="中國蛋雞產業發展報告2023",
      note="中國商業平均（海蘭/羅曼為主）"),
    b("layer_hen","laying_rate",82.0,"%",value_min=78.0,value_max=85.0,
      production_stage="late_500d_plus",
      source_title="Poultry Science 2021 Late-Cycle Layer Review",
      note=">500日齡，優秀場維持82-85%"),
    b("layer_hen","FCR",2.10,"ratio",value_min=1.95,value_max=2.25,
      production_stage="full_cycle",credibility=5,
      source_type="vendor_whitepaper",
      source_title="ISA Brown Layer Management Guide 2022",
      note="Feed kg/egg mass kg. Top 10%=1.95-2.05"),
    b("layer_hen","egg_feed_ratio",2.10,"ratio",value_min=1.95,value_max=2.25,
      production_stage="full_cycle",credibility=5,
      source_type="vendor_whitepaper",
      source_title="ISA Brown Layer Management Guide 2022",
      note="蛋料比（FCR另一叫法）"),
    b("layer_hen","peak_duration_weeks",30,"weeks",value_min=24,value_max=38,
      source_title="World Poultry Science Journal 2022 Layer Persistency",
      note="Production >90% sustained weeks. Top genetic lines 34-38wk"),
    b("layer_hen","eggshell_strength",38.0,"N",value_min=34.0,value_max=42.0,
      source_title="Poultry Science 2020 Eggshell Quality Review",
      note=">35N = acceptable commercial quality"),
    b("layer_hen","mortality_rate",5.0,"%",value_min=3.0,value_max=8.0,
      production_stage="full_cycle_80wk",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Hy-Line Brown Commercial Management Guide 2022",
      note="80週整體死淘率，top 10% < 4%"),
    b("layer_hen","egg_weight_g",63.0,"g",value_min=60.0,value_max=66.0,
      production_stage="peak",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Lohmann Brown-Classic Layer Management Guide 2022",
      note="Peak production egg weight"),
    b("layer_hen","hen_day_production",90.5,"%",value_min=88.0,value_max=93.0,
      production_stage="full_cycle",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Hy-Line W-36 Commercial Management Guide 2022",
      note="Hen-day production（存活母雞計算）"),
]

# ── 種雞 (Broiler Breeder) ────────────────────────────────────────────────────
BENCHMARKS += [
    b("breeder_chicken","fertility_rate",95.0,"%",value_min=93.0,value_max=97.0,
      production_stage="peak_30_45wk",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Cobb Broiler Breeder Management Guide 2022"),
    b("breeder_chicken","hatchability",85.0,"%",value_min=82.0,value_max=88.0,
      production_stage="full_cycle",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Ross Broiler Breeder Performance Objectives 2022",
      note="Hatchability of fertile eggs"),
    b("breeder_chicken","healthy_chick_rate",92.0,"%",value_min=90.0,value_max=95.0,
      credibility=5,source_type="vendor_whitepaper",
      source_title="Cobb Broiler Breeder Management Guide 2022"),
    b("breeder_chicken","chicks_per_hen_housed",158,"head/hen",value_min=145,value_max=170,
      production_stage="full_cycle_60wk",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Ross Broiler Breeder Performance Objectives 2022",
      note="60週產期"),
]

# ── 鴨 (Pekin Duck) ───────────────────────────────────────────────────────────
BENCHMARKS += [
    b("duck","FCR",2.35,"ratio",value_min=2.10,value_max=2.60,
      production_stage="finisher_42d",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Cherry Valley Duck Performance Standards 2022",
      note="Pekin 0-42d. Top 10%=2.1-2.2"),
    b("duck","FCR",2.50,"ratio",value_min=2.30,value_max=2.75,
      region="CN_all",production_stage="finisher_42d",year=2023,
      source_type="industry_media",
      source_title="中國肉鴨行業白皮書2023"),
    b("duck","ADG",65.0,"g/day",value_min=58.0,value_max=72.0,
      production_stage="finisher_42d",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Cherry Valley Duck Performance Standards 2022"),
    b("duck","live_weight",3200,"g",value_min=2900,value_max=3600,
      production_stage="market_42d",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Cherry Valley Duck Performance Standards 2022"),
    b("duck","mortality_rate",3.0,"%",value_min=1.5,value_max=5.0,
      source_title="Poultry Science 2021 Duck Production Review"),
]

# ── 鵝 (Goose) ────────────────────────────────────────────────────────────────
BENCHMARKS += [
    b("goose","FCR",3.20,"ratio",value_min=2.80,value_max=3.60,
      production_stage="grow_out_70d",credibility=3,
      source_title="Poultry Science 2021 Goose Production Review"),
    b("goose","live_weight",5800,"g",value_min=5000,value_max=7000,
      production_stage="market_70d",credibility=3,
      source_title="Poultry Science 2021 Goose Production Review"),
    b("goose","mortality_rate",5.0,"%",value_min=3.0,value_max=8.0,
      credibility=3,source_title="Poultry Science 2021"),
]

# ══════════════════════════════════════════════════════════════════════════════
# 二、豬
# ══════════════════════════════════════════════════════════════════════════════

# ── 仔豬 / 哺乳仔豬 (Suckling Piglet) ─────────────────────────────────────────
BENCHMARKS += [
    b("suckling_piglet","pre_weaning_mortality",10.0,"%",value_min=6.0,value_max=15.0,
      production_stage="birth_to_weaning",credibility=5,
      source_type="vendor_whitepaper",
      source_title="PIC Sow Performance Standards 2023",
      note="Top 10% <7%, EU average ~10-12%"),
    b("suckling_piglet","weaning_weight",7.2,"kg",value_min=6.0,value_max=8.5,
      production_stage="weaning_21d",credibility=5,
      source_type="vendor_whitepaper",
      source_title="TOPIGS Norsvin Piglet Survival Guide 2022",
      note="21d weaning. Top >7.5kg. <6kg = high PWMS risk"),
    b("suckling_piglet","weaning_weight",6.5,"kg",value_min=5.5,value_max=7.5,
      region="CN_all",production_stage="weaning_28d",year=2023,
      source_type="industry_media",
      source_title="中國養豬行業年度報告2023",
      note="中國多為28日齡斷奶"),
    b("suckling_piglet","ADG",230,"g/day",value_min=200,value_max=270,
      production_stage="birth_to_weaning",
      source_title="Journal of Animal Science 2022 Piglet Growth",
      note="Birth to 21d. Top 10% >250g/day"),
    b("suckling_piglet","litter_weaning_rate",92.0,"%",value_min=87.0,value_max=96.0,
      credibility=5,source_type="vendor_whitepaper",
      source_title="PIC Sow Performance Standards 2023",
      note="% born alive surviving to weaning. Top >93%"),
    b("suckling_piglet","birth_weight",1.45,"kg",value_min=1.30,value_max=1.65,
      source_title="Journal of Animal Science 2022 Piglet Birth Weight",
      note=">1.5kg = excellent, <1.0kg = weak/runt"),
]

# ── 保育豬 (Nursery Pig 7-25kg) ───────────────────────────────────────────────
BENCHMARKS += [
    b("nursery_pig","FCR",1.65,"ratio",value_min=1.50,value_max=1.80,
      production_stage="nursery_7_25kg",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Genus PIC Nursery Management Guide 2022",
      note="Top 10%=1.50-1.58"),
    b("nursery_pig","FCR",1.75,"ratio",value_min=1.60,value_max=1.95,
      region="CN_all",production_stage="nursery_7_25kg",year=2023,
      source_type="industry_media",
      source_title="中國養豬行業年度報告2023"),
    b("nursery_pig","ADG",470,"g/day",value_min=400,value_max=550,
      production_stage="nursery_7_25kg",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Genus PIC Nursery Management Guide 2022",
      note="Top 10% >500g/day"),
    b("nursery_pig","diarrhea_rate",8.0,"%",value_min=3.0,value_max=15.0,
      source_title="Preventive Veterinary Medicine 2022 Post-weaning Diarrhea",
      note="Top herds <5%"),
    b("nursery_pig","mortality_rate",2.5,"%",value_min=1.0,value_max=5.0,
      production_stage="nursery_7_25kg",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Topigs Norsvin Nursery Performance Standards 2022",
      note="Top 10% <1.5%"),
    b("nursery_pig","weaning_to_finish_days",42,"days",value_min=35,value_max=50,
      credibility=5,source_type="vendor_whitepaper",
      source_title="Genus PIC Nursery Management Guide 2022"),
]

# ── 育肥豬 (Finisher Pig >80kg) ───────────────────────────────────────────────
BENCHMARKS += [
    b("finisher_pig","FCR",2.65,"ratio",value_min=2.45,value_max=2.85,
      production_stage="finisher_25_115kg",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Genus PIC Commercial Pig Production Guide 2022",
      note="25-115kg. Top 10%=2.45-2.55"),
    b("finisher_pig","FCR",2.80,"ratio",value_min=2.65,value_max=3.00,
      region="CN_all",production_stage="finisher_25_115kg",year=2023,
      source_type="industry_media",
      source_title="中國養豬行業年度報告2023"),
    b("finisher_pig","ADG",900,"g/day",value_min=800,value_max=1050,
      production_stage="finisher_25_115kg",credibility=5,
      source_type="vendor_whitepaper",
      source_title="Topigs Norsvin Terminal Line Production Standard 2022",
      note="Top 10% >950g/day"),
    b("finisher_pig","live_weight",115.0,"kg",value_min=100.0,value_max=125.0,
      production_stage="market_weight",
      source_title="Animal Production Science 2022 Global Pig Production"),
    b("finisher_pig","carcass_rate",76.0,"%",value_min=73.0,value_max=79.0,
      source_title="Meat Science 2022 Pork Carcass Quality"),
    b("finisher_pig","mortality_rate",2.0,"%",value_min=1.0,value_max=4.0,
      production_stage="finisher_25_115kg",
      source_title="Genus PIC Commercial Pig Production Guide 2022",
      note="Top 10% <1.2%"),
    b("finisher_pig","backfat_mm",14.0,"mm",value_min=10.0,value_max=18.0,
      source_title="Meat Science 2022",
      note="P2 backfat at 115kg. Lean breeds target <12mm"),
]

# ── 懷孕母豬 (Pregnant Sow) ───────────────────────────────────────────────────
BENCHMARKS += [
    b("pregnant_sow","healthy_piglet_rate",92.0,"%",value_min=88.0,value_max=95.0,
      credibility=5,source_type="vendor_whitepaper",
      source_title="PIC Sow Performance Standards 2023",
      note="Born alive/total born. Top >93%"),
    b("pregnant_sow","litter_size",14.2,"head/litter",value_min=12.5,value_max=16.0,
      credibility=5,source_type="vendor_whitepaper",
      source_title="PIC Sow Performance Standards 2023",
      note="Total born. Top 10% 15-16 born alive"),
    b("pregnant_sow","healthy_piglet_count",13.0,"head/litter",value_min=11.5,value_max=14.5,
      credibility=5,source_type="vendor_whitepaper",
      source_title="Hypor Magnus Sow Performance Standards 2022"),
    b("pregnant_sow","healthy_piglet_weight",1.45,"kg",value_min=1.30,value_max=1.65,
      source_title="Journal of Animal Science 2022 Piglet Birth Weight"),
    b("pregnant_sow","birth_weight_uniformity",85.0,"%",value_min=80.0,value_max=90.0,
      source_title="Livestock Science 2022 Sow Reproductive Performance",
      note="% within ±15% of litter mean"),
    b("pregnant_sow","weak_piglet_rate",5.0,"%",value_min=2.0,value_max=9.0,
      source_title="Livestock Science 2022",note="Top <3%"),
    b("pregnant_sow","stillborn_rate",6.5,"%",value_min=4.0,value_max=10.0,
      source_title="Livestock Science 2022",note="Top <5%"),
    b("pregnant_sow","wean_to_estrus_days",5.5,"days",value_min=4.0,value_max=7.5,
      credibility=5,source_type="vendor_whitepaper",
      source_title="PIC Sow Performance Standards 2023",note="Top <5d"),
    b("pregnant_sow","farrowing_rate",88.0,"%",value_min=83.0,value_max=93.0,
      credibility=5,source_type="vendor_whitepaper",
      source_title="PIC Sow Performance Standards 2023",note="Top 10% >90%"),
    b("pregnant_sow","npe_per_sow_year",27.5,"head/sow/year",value_min=24.0,value_max=31.0,
      credibility=5,source_type="vendor_whitepaper",
      source_title="Topigs Norsvin TN70 Sow Guide 2023",note="Top >30"),
]

# ── 哺乳母豬 (Lactating Sow) ──────────────────────────────────────────────────
BENCHMARKS += [
    b("lactating_sow","grade_a_weaner_rate",88.0,"%",value_min=83.0,value_max=93.0,
      source_title="Animal 2022 Sow Lactation Performance Review"),
    b("lactating_sow","weaning_weight_uniformity",82.0,"%",value_min=75.0,value_max=88.0,
      source_title="Animal 2022"),
    b("lactating_sow","sow_weight_loss",15.0,"kg",value_min=10.0,value_max=22.0,
      source_title="Journal of Animal Science 2021 Sow Body Condition",
      note=">20kg = excessive catabolism"),
    b("lactating_sow","milk_yield_kg_day",9.5,"kg/day",value_min=8.0,value_max=12.0,
      source_title="Journal of Animal Science 2022 Sow Milk",note="Top >11kg/day"),
    b("lactating_sow","litter_gain_g_day",2800,"g/day",value_min=2400,value_max=3200,
      source_title="Animal 2022",note="Whole litter daily gain = milk proxy"),
]

# ── 公豬 (Boar) ───────────────────────────────────────────────────────────────
BENCHMARKS += [
    b("boar","sperm_motility",80.0,"%",value_min=75.0,value_max=90.0,
      source_title="Theriogenology 2022 Boar Semen Quality",note="Top AI studs >85%"),
    b("boar","semen_volume",250.0,"mL",value_min=150.0,value_max=350.0,
      source_title="Theriogenology 2022"),
    b("boar","abnormality_rate",15.0,"%",value_min=8.0,value_max=25.0,
      source_title="Theriogenology 2022",note="<15% = acceptable AI"),
    b("boar","sperm_concentration",280,"million/mL",value_min=200,value_max=380,
      source_title="Theriogenology 2022"),
]

# ══════════════════════════════════════════════════════════════════════════════
# 三、牛
# ══════════════════════════════════════════════════════════════════════════════

BENCHMARKS += [
    b("beef_cattle","FCR",6.20,"ratio",value_min=5.5,value_max=7.0,
      production_stage="feedlot",
      source_title="Animal Feed Science and Technology 2022 Beef FCR",
      note="Feedlot DM basis. Top 10%=5.5-5.8"),
    b("beef_cattle","ADG",1.40,"kg/day",value_min=1.2,value_max=1.7,
      production_stage="feedlot",
      source_title="Journal of Animal Science 2022 Feedlot Performance",
      note="Top Angus/Simmental >1.5kg/day"),
    b("beef_cattle","slaughter_weight",550.0,"kg",value_min=480.0,value_max=650.0,
      production_stage="market",
      source_title="Meat Science 2022 Global Beef Production"),
    b("beef_cattle","carcass_dressing_pct",62.0,"%",value_min=58.0,value_max=65.0,
      source_title="Meat Science 2022",note="Top Angus >63%"),
    b("beef_cattle","rearing_cycle_days",180,"days",value_min=150,value_max=240,
      production_stage="feedlot",source_title="Animal Production Science 2022"),
    b("beef_cattle","marbling_score",3.5,"score",value_min=2.0,value_max=6.0,
      source_title="Meat Science 2022",note="BMS 1-12 scale"),
    b("dairy_cow","milk_yield_kg_per_day",35.0,"kg/day",value_min=28.0,value_max=45.0,
      production_stage="peak_lactation",
      source_title="Journal of Dairy Science 2022 Global Dairy Performance",
      note="305d total top 10%=10000-12000kg. Holstein"),
    b("dairy_cow","305d_milk_yield",10500,"kg",value_min=8500,value_max=13000,
      production_stage="305d",source_title="Journal of Dairy Science 2022",
      note="Top Holstein >12000kg"),
    b("dairy_cow","SCC",150000,"cells/mL",value_min=50000,value_max=250000,
      source_title="Journal of Dairy Science 2021",
      note="EU legal limit 400k. Top <100k"),
    b("dairy_cow","fat_pct",3.8,"%",value_min=3.4,value_max=4.3,
      credibility=5,source_type="vendor_whitepaper",
      source_title="Holstein Association USA 2022"),
    b("dairy_cow","protein_pct",3.2,"%",value_min=2.9,value_max=3.5,
      credibility=5,source_type="vendor_whitepaper",
      source_title="Holstein Association USA 2022"),
]

# ══════════════════════════════════════════════════════════════════════════════
# 四、羊
# ══════════════════════════════════════════════════════════════════════════════

BENCHMARKS += [
    b("meat_sheep","FCR",4.5,"ratio",value_min=3.8,value_max=5.5,
      production_stage="finishing",
      source_title="Small Ruminant Research 2022 Lamb Finishing",
      note="Feedlot 30-50kg. Top 10% <4.0"),
    b("meat_sheep","ADG",280,"g/day",value_min=220,value_max=350,
      production_stage="finishing",source_title="Small Ruminant Research 2022"),
    b("meat_sheep","slaughter_weight",42.0,"kg",value_min=35.0,value_max=55.0,
      production_stage="market",source_title="Meat Science 2022 Lamb Quality"),
    b("meat_sheep","lambing_rate",130,"%",value_min=110,value_max=165,
      source_title="Small Ruminant Research 2022",note="Prolific breeds 160-180%"),
    b("meat_sheep","carcass_dressing_pct",50.0,"%",value_min=46.0,value_max=54.0,
      source_title="Meat Science 2022"),
    b("wool_sheep","wool_yield_kg",5.5,"kg/head/year",value_min=4.0,value_max=9.0,
      source_type="vendor_whitepaper",
      source_title="Australian Wool Innovation Production Standards 2022",
      note="Merino top 10%=7-9kg. Corriedale=4-5kg. Poll Merino=6-8kg"),
    b("wool_sheep","wool_yield_kg",4.2,"kg/head/year",value_min=3.5,value_max=5.5,
      region="CN_all",source_type="industry_media",
      source_title="中國羊毛行業發展報告2022",note="新疆/內蒙古"),
    b("wool_sheep","wool_fibre_diameter",19.5,"micron",value_min=15.0,value_max=28.0,
      credibility=5,source_type="vendor_whitepaper",
      source_title="IWTO Wool Fibre Diameter Standards 2022",
      note="Fine <18.5μm, Medium 18.5-22μm, Broad >22μm"),
    b("wool_sheep","staple_length_mm",90,"mm",value_min=70,value_max=120,
      source_title="Small Ruminant Research 2022 Merino Wool Quality",
      note="Top auction premium 90-110mm"),
    b("wool_sheep","staple_strength_nkt",35,"N/ktex",value_min=25,value_max=45,
      source_title="Wool Technology and Sheep Breeding 2022",
      note=">30 = acceptable. <25 = tender wool heavy discount"),
    b("wool_sheep","clean_fleece_pct",68.0,"%",value_min=60.0,value_max=76.0,
      source_title="Australian Wool Innovation 2022",note="Top 10% >72%"),
    b("wool_sheep","lambing_rate",118,"%",value_min=95,value_max=145,
      source_title="Australian Wool Innovation Production Standards 2022"),
    b("dairy_goat","milk_yield_kg_per_day",3.5,"kg/day",value_min=2.5,value_max=5.0,
      production_stage="peak_lactation",credibility=3,
      source_title="Small Ruminant Research 2022 Goat Milk",
      note="Saanen/Alpine. Top >4.5kg/day"),
    b("meat_goat","FCR",5.5,"ratio",value_min=4.5,value_max=6.5,
      production_stage="finishing",credibility=3,
      source_title="Small Ruminant Research 2021 Meat Goat",note="Boer goat"),
    b("meat_goat","ADG",180,"g/day",value_min=140,value_max=230,
      production_stage="finishing",credibility=3,
      source_title="Small Ruminant Research 2021",note="Top 10% >200g/day"),
]

# ══════════════════════════════════════════════════════════════════════════════
# 五、蝦類
# ══════════════════════════════════════════════════════════════════════════════

BENCHMARKS += [
    b("shrimp","FCR",1.35,"ratio",value_min=1.15,value_max=1.55,
      production_stage="grow_out",
      source_title="Aquaculture 2023 Vannamei Production Performance",
      note="Intensive. Top 10%=1.15-1.25"),
    b("shrimp","FCR",1.45,"ratio",value_min=1.25,value_max=1.65,
      region="SEA_vietnam",production_stage="grow_out",year=2023,
      source_title="Aquaculture Reports 2023 Vietnam Shrimp"),
    b("shrimp","FCR",1.50,"ratio",value_min=1.30,value_max=1.70,
      region="CN_south",production_stage="grow_out",year=2023,
      source_type="industry_media",source_title="中國對蝦養殖技術報告2023"),
    b("shrimp","survival_rate",75.0,"%",value_min=60.0,value_max=88.0,
      production_stage="grow_out",
      source_title="Reviews in Aquaculture 2023 Shrimp Survival",
      note="Top 10% >85%. EMS endemic <60%"),
    b("shrimp","survival_rate",72.0,"%",value_min=55.0,value_max=85.0,
      region="CN_south",production_stage="grow_out",year=2023,
      source_type="industry_media",source_title="中國對蝦養殖技術報告2023"),
    b("shrimp","harvest_cycle_days",120,"days",value_min=90,value_max=150,
      production_stage="grow_out",
      source_title="Aquaculture 2023 Vannamei Production",note="PL10 to 20g, 28°C"),
    b("shrimp","ADG",0.17,"g/day",value_min=0.13,value_max=0.22,
      production_stage="grow_out",source_title="Aquaculture 2023 Vannamei"),
    b("shrimp","vibrio_reduction_pct",40.0,"%",value_min=25.0,value_max=60.0,
      source_title="Aquaculture 2022 Vibrio Control Shrimp",
      note="Probiotic vs control. AB指標"),
    b("tiger_prawn","FCR",1.65,"ratio",value_min=1.40,value_max=1.90,
      production_stage="grow_out",
      source_title="Aquaculture 2022 Penaeus monodon SEA",note="Top 10%=1.4-1.5"),
    b("tiger_prawn","survival_rate",65.0,"%",value_min=50.0,value_max=80.0,
      production_stage="grow_out",source_title="Aquaculture 2022 Penaeus monodon SEA"),
    b("tiger_prawn","harvest_cycle_days",150,"days",value_min=120,value_max=180,
      production_stage="grow_out",source_title="Aquaculture 2022 Penaeus monodon SEA"),
    b("giant_freshwater_prawn","FCR",2.10,"ratio",value_min=1.80,value_max=2.50,
      region="SEA_thailand",production_stage="grow_out",
      source_title="Aquaculture 2022 Macrobrachium Thailand",note="頂級場1.8-2.0"),
    b("giant_freshwater_prawn","FCR",2.20,"ratio",value_min=1.90,value_max=2.60,
      region="TW_all",production_stage="grow_out",
      source_title="台灣水產試驗所年報2022",note="桃竹苗/彰化"),
    b("giant_freshwater_prawn","survival_rate",65.0,"%",value_min=50.0,value_max=78.0,
      production_stage="grow_out",source_title="Aquaculture 2022 Macrobrachium Asia",
      note="雄蝦打架損失"),
    b("giant_freshwater_prawn","harvest_cycle_days",150,"days",value_min=120,value_max=180,
      production_stage="grow_out",source_title="Aquaculture 2022 Macrobrachium Asia",
      note="PL15 to 25-40g, 28-30°C"),
    b("giant_freshwater_prawn","harvest_cycle_days",180,"days",value_min=150,value_max=210,
      region="TW_all",production_stage="grow_out",
      source_title="台灣水產試驗所年報2022",note="冬季生長期延長"),
    b("giant_freshwater_prawn","market_weight",35.0,"g",value_min=25.0,value_max=60.0,
      production_stage="harvest",source_title="Aquaculture 2022",
      note="台灣偏好>50g"),
]

# ══════════════════════════════════════════════════════════════════════════════
# 六、魚類
# ══════════════════════════════════════════════════════════════════════════════

BENCHMARKS += [
    b("tilapia","FCR",1.60,"ratio",value_min=1.35,value_max=1.85,
      production_stage="grow_out",
      source_title="Reviews in Aquaculture 2022 Tilapia Global Production",
      note="Intensive 28-32°C. Top 10%=1.35-1.45"),
    b("tilapia","survival_rate",85.0,"%",value_min=75.0,value_max=93.0,
      production_stage="grow_out",source_title="Reviews in Aquaculture 2022",
      note="Top 10% >90%"),
    b("tilapia","harvest_cycle_days",180,"days",value_min=150,value_max=210,
      production_stage="grow_out",source_title="Aquaculture 2022 Nile Tilapia",
      note="Fingerling to 500-700g"),
    b("tilapia","ADG",3.0,"g/day",value_min=2.5,value_max=3.8,
      production_stage="grow_out",source_title="Reviews in Aquaculture 2022"),
    b("tilapia","streptococcus_survival_rate",72.0,"%",value_min=60.0,value_max=85.0,
      source_title="Aquaculture 2021 Streptococcosis Tilapia",note="AB基準"),
    b("milkfish","FCR",1.85,"ratio",value_min=1.60,value_max=2.10,
      production_stage="grow_out",
      source_title="Aquaculture 2022 Milkfish Production Asia"),
    b("milkfish","FCR",1.75,"ratio",value_min=1.55,value_max=1.95,
      region="TW_all",production_stage="grow_out",
      source_title="台灣水產試驗所年報2022",note="台南/屏東"),
    b("milkfish","survival_rate",80.0,"%",value_min=70.0,value_max=90.0,
      production_stage="grow_out",source_title="Aquaculture 2022 Milkfish"),
    b("milkfish","harvest_cycle_days",180,"days",value_min=150,value_max=240,
      production_stage="grow_out",source_title="Aquaculture 2022 Milkfish",
      note="5-10g to 300-500g, 28-32°C"),
    b("milkfish","harvest_cycle_days",210,"days",value_min=180,value_max=270,
      region="TW_all",production_stage="grow_out",
      source_title="台灣水產試驗所年報2022",note="冬季延長，目標500-600g"),
    b("milkfish","ADG",2.8,"g/day",value_min=2.0,value_max=3.8,
      production_stage="grow_out",credibility=3,
      source_title="FAO Fisheries Technical Paper 2021 Milkfish"),
    b("grey_mullet","FCR",1.70,"ratio",value_min=1.45,value_max=2.00,
      region="TW_all",production_stage="grow_out",credibility=3,
      source_title="台灣水產試驗所年報2022 烏魚"),
    b("grey_mullet","survival_rate",85.0,"%",value_min=75.0,value_max=92.0,
      region="TW_all",production_stage="grow_out",credibility=3,
      source_title="台灣水產試驗所年報2022"),
    b("grey_mullet","harvest_cycle_days",270,"days",value_min=210,value_max=330,
      region="TW_all",production_stage="grow_out",credibility=3,
      source_title="台灣水產試驗所年報2022",note="冬至前採收烏魚子"),
    b("grey_mullet","roe_yield_pct",8.0,"%",value_min=6.0,value_max=12.0,
      region="TW_all",production_stage="harvest",credibility=3,
      source_type="industry_media",source_title="台灣烏魚產業報告2022"),
    b("pangasius_catfish","FCR",1.65,"ratio",value_min=1.45,value_max=1.85,
      region="SEA_vietnam",production_stage="grow_out",year=2023,
      source_title="Aquaculture 2023 Pangasius Vietnam",note="頂級場1.45-1.55"),
    b("pangasius_catfish","FCR",1.80,"ratio",value_min=1.60,value_max=2.00,
      region="SEA_thailand",production_stage="grow_out",credibility=3,
      source_type="industry_media",source_title="Thai Fisheries Gazette 2022"),
    b("pangasius_catfish","survival_rate",80.0,"%",value_min=70.0,value_max=90.0,
      region="SEA_vietnam",production_stage="grow_out",year=2023,
      source_title="Aquaculture 2023 Pangasius Vietnam"),
    b("pangasius_catfish","harvest_cycle_days",180,"days",value_min=150,value_max=210,
      region="SEA_vietnam",production_stage="grow_out",year=2023,
      source_title="Aquaculture 2023 Pangasius Vietnam",note="20g to 800-1000g"),
    b("pangasius_catfish","ADG",5.5,"g/day",value_min=4.5,value_max=6.5,
      region="SEA_vietnam",production_stage="grow_out",year=2023,
      source_title="Aquaculture 2023 Pangasius Vietnam"),
    b("channel_catfish","FCR",1.95,"ratio",value_min=1.70,value_max=2.20,
      region="CN_all",production_stage="grow_out",
      source_title="中國水產科學2022 斑點叉尾鮰"),
    b("channel_catfish","survival_rate",82.0,"%",value_min=72.0,value_max=90.0,
      region="CN_all",production_stage="grow_out",source_title="中國水產科學2022"),
    b("channel_catfish","harvest_cycle_days",240,"days",value_min=180,value_max=300,
      region="CN_all",production_stage="grow_out",source_title="中國水產科學2022"),
    b("largemouth_catfish","FCR",2.20,"ratio",value_min=1.90,value_max=2.50,
      region="CN_all",production_stage="grow_out",credibility=3,
      source_title="水產學報2022 大口鯰"),
    b("largemouth_catfish","survival_rate",75.0,"%",value_min=65.0,value_max=85.0,
      region="CN_all",production_stage="grow_out",credibility=3,
      source_title="水產學報2022"),
    b("largemouth_bass","FCR",1.35,"ratio",value_min=1.15,value_max=1.55,
      region="CN_all",production_stage="grow_out",year=2023,
      source_title="水產學報2023 加州鱸"),
    b("largemouth_bass","survival_rate",78.0,"%",value_min=65.0,value_max=88.0,
      region="CN_all",production_stage="grow_out",year=2023,
      source_title="水產學報2023"),
    b("largemouth_bass","harvest_cycle_days",270,"days",value_min=210,value_max=330,
      region="CN_all",production_stage="grow_out",year=2023,
      source_title="水產學報2023"),
    b("largemouth_bass","ADG",2.8,"g/day",value_min=2.2,value_max=3.5,
      region="CN_all",production_stage="grow_out",year=2023,
      source_title="水產學報2023"),
    b("grass_carp","FCR",1.90,"ratio",value_min=1.60,value_max=2.20,
      region="CN_all",production_stage="grow_out",
      source_title="中國水產科學2022 草魚",note="飼料+青草混合"),
    b("grass_carp","survival_rate",82.0,"%",value_min=72.0,value_max=90.0,
      region="CN_all",production_stage="grow_out",source_title="中國水產科學2022"),
    b("grass_carp","harvest_cycle_days",360,"days",value_min=270,value_max=480,
      region="CN_all",production_stage="grow_out",source_title="中國水產科學2022"),
    b("grass_carp","ADG",6.5,"g/day",value_min=5.0,value_max=8.5,
      region="CN_all",production_stage="grow_out",credibility=3,
      source_title="中國水產科學2022"),
    b("grouper","FCR",2.20,"ratio",value_min=1.80,value_max=2.60,
      production_stage="grow_out",credibility=3,
      source_title="Aquaculture 2022 Grouper Production Asia"),
    b("grouper","survival_rate",75.0,"%",value_min=60.0,value_max=85.0,
      production_stage="grow_out",credibility=3,
      source_title="Aquaculture 2022 Grouper"),
    b("grouper","harvest_cycle_days",360,"days",value_min=270,value_max=450,
      production_stage="grow_out",credibility=3,
      source_title="Aquaculture 2022 Grouper"),
    b("atlantic_salmon","FCR",1.20,"ratio",value_min=1.10,value_max=1.35,
      production_stage="seawater_phase",year=2023,
      source_title="Aquaculture 2023 Atlantic Salmon Norway",
      note="Top Norwegian=1.10-1.15"),
    b("atlantic_salmon","survival_rate",85.0,"%",value_min=78.0,value_max=92.0,
      production_stage="seawater_phase",year=2023,
      source_title="Aquaculture 2023 Atlantic Salmon Norway"),
    b("atlantic_salmon","harvest_cycle_days",540,"days",value_min=450,value_max=630,
      production_stage="full_cycle",source_title="Reviews in Aquaculture 2022 Salmon"),
    b("atlantic_salmon","ADG",8.5,"g/day",value_min=7.0,value_max=10.5,
      production_stage="seawater_phase",year=2023,
      source_title="Aquaculture 2023 Atlantic Salmon Norway"),
    b("seabass","FCR",1.75,"ratio",value_min=1.55,value_max=1.95,
      production_stage="grow_out",source_title="Aquaculture 2022 Mediterranean Seabass"),
    b("seabass","survival_rate",88.0,"%",value_min=80.0,value_max=93.0,
      production_stage="grow_out",source_title="Aquaculture 2022 Mediterranean Seabass"),
    b("seabass","harvest_cycle_days",600,"days",value_min=500,value_max=720,
      production_stage="grow_out",source_title="Aquaculture 2022 Mediterranean Seabass"),
    b("rice_field_eel","FCR",3.20,"ratio",value_min=2.60,value_max=3.80,
      region="CN_all",production_stage="grow_out",credibility=3,
      source_title="中國水產科學2022 黃鱔",note="膨化料FCR 2.6-3.5"),
    b("rice_field_eel","survival_rate",72.0,"%",value_min=60.0,value_max=82.0,
      region="CN_all",production_stage="grow_out",credibility=3,
      source_title="中國水產科學2022"),
    b("rice_field_eel","harvest_cycle_days",180,"days",value_min=150,value_max=240,
      region="CN_all",production_stage="grow_out",credibility=3,
      source_title="中國水產科學2022",note="苗10-20g到100-200g"),
    b("pond_loach","FCR",1.80,"ratio",value_min=1.50,value_max=2.10,
      region="CN_all",production_stage="grow_out",credibility=3,
      source_title="中國水產科學2021 泥鰍"),
    b("pond_loach","survival_rate",75.0,"%",value_min=62.0,value_max=85.0,
      region="CN_all",production_stage="grow_out",credibility=3,
      source_title="中國水產科學2021"),
    b("pond_loach","harvest_cycle_days",120,"days",value_min=90,value_max=150,
      region="CN_all",production_stage="grow_out",credibility=3,
      source_title="中國水產科學2021"),
]

# ══════════════════════════════════════════════════════════════════════════════
# 七、毛皮動物
# ══════════════════════════════════════════════════════════════════════════════

BENCHMARKS += [
    b("mink","kit_survival_rate",82.0,"%",value_min=75.0,value_max=90.0,
      production_stage="weaning",
      source_title="Acta Agriculturae Scandinavica 2022 Mink Production"),
    b("mink","kits_per_female",5.2,"head/female",value_min=4.5,value_max=6.2,
      source_title="Scientifur 2022 Mink Reproduction"),
    b("mink","FCR",3.8,"ratio",value_min=3.2,value_max=4.5,
      production_stage="grow_out",source_title="AAS 2022 Mink Nutrition",
      note="Wet feed as-fed. DM basis ~1.0-1.2"),
    b("mink","pelt_quality_grade_A_pct",70.0,"%",value_min=60.0,value_max=80.0,
      production_stage="harvest",credibility=3,
      source_type="industry_media",source_title="Kopenhagen Fur Auction Standards 2022"),
    b("mink","grow_out_days",180,"days",value_min=165,value_max=195,
      production_stage="grow_out",source_title="AAS 2022",note="May whelping to Nov/Dec harvest"),
    b("fox","kits_per_female",5.5,"head/female",value_min=4.0,value_max=7.0,
      credibility=3,source_title="Scientifur 2022 Fox Production"),
    b("fox","pelt_quality_grade_A_pct",65.0,"%",value_min=55.0,value_max=75.0,
      production_stage="harvest",credibility=3,
      source_type="industry_media",source_title="Kopenhagen Fur Auction Standards 2022"),
    b("fox","FCR",5.0,"ratio",value_min=4.0,value_max=6.5,
      production_stage="grow_out",credibility=3,
      source_title="Scientifur 2022",note="Wet feed as-fed"),
    b("rabbit","FCR",3.2,"ratio",value_min=2.8,value_max=3.6,
      production_stage="grow_out_28_70d",
      source_title="World Rabbit Science 2022",note="Top 10%=2.8-3.0"),
    b("rabbit","ADG",42,"g/day",value_min=35,value_max=52,
      production_stage="grow_out_28_70d",source_title="World Rabbit Science 2022"),
    b("rabbit","slaughter_weight",2.5,"kg",value_min=2.2,value_max=2.8,
      production_stage="market_70d",source_title="World Rabbit Science 2022"),
    b("rabbit","kits_per_doe_year",48,"head/doe/year",value_min=40,value_max=58,
      source_title="World Rabbit Science 2022",note="Top 10% >55"),
    b("rabbit","mortality_rate",8.0,"%",value_min=5.0,value_max=12.0,
      production_stage="grow_out",source_title="World Rabbit Science 2022",
      note="Top 10% <5%"),
]

# ══════════════════════════════════════════════════════════════════════════════
# 八、特種動物
# ══════════════════════════════════════════════════════════════════════════════

BENCHMARKS += [
    b("deer","velvet_yield_kg",2.8,"kg/head/year",value_min=2.0,value_max=4.5,
      credibility=3,source_type="industry_media",
      source_title="New Zealand Deer Industry Annual Report 2022",
      note="Red Deer NZ top 10%=4-5kg"),
    b("deer","FCR",8.0,"ratio",value_min=6.5,value_max=10.0,
      production_stage="finishing",credibility=3,
      source_title="Animal Production Science 2021 Deer Venison"),
    b("deer","ADG",220,"g/day",value_min=180,value_max=280,
      production_stage="finishing",credibility=3,
      source_title="Animal Production Science 2021"),
    b("crocodile","FCR",5.5,"ratio",value_min=4.5,value_max=7.0,
      region="SEA_thailand",production_stage="grow_out",year=2021,credibility=3,
      source_title="FAO Crocodile Aquaculture Report 2021"),
    b("crocodile","survival_rate",85.0,"%",value_min=75.0,value_max=92.0,
      region="SEA_thailand",production_stage="grow_out",year=2021,credibility=3,
      source_title="FAO Crocodile Aquaculture Report 2021"),
    b("crocodile","harvest_cycle_days",1095,"days",value_min=730,value_max=1460,
      production_stage="skin_harvest",year=2021,credibility=3,
      source_title="FAO Crocodile Aquaculture Report 2021",note="3-4 years to 1.8m+"),
    b("crocodile","skin_quality_grade_A_pct",65.0,"%",value_min=55.0,value_max=75.0,
      region="SEA_thailand",production_stage="harvest",year=2021,credibility=3,
      source_type="industry_media",source_title="CITES Crocodile Working Group 2021"),
    b("wild_boar_hybrid","FCR",3.5,"ratio",value_min=3.0,value_max=4.2,
      production_stage="finishing",credibility=3,
      source_title="Animal Science 2021 Wild Boar Hybrid",note="Premium niche market"),
    b("wild_boar_hybrid","ADG",350,"g/day",value_min=280,value_max=430,
      production_stage="finishing",credibility=3,
      source_title="Animal Science 2021"),
    b("wild_boar_hybrid","slaughter_weight",80.0,"kg",value_min=65.0,value_max=95.0,
      production_stage="market",credibility=3,
      source_title="Animal Science 2021"),
]


# ══════════════════════════════════════════════════════════════════════════════
# DB 寫入引擎
# ══════════════════════════════════════════════════════════════════════════════

def seed(dry_run: bool = False, species_filter: str = ""):
    records = BENCHMARKS
    if species_filter:
        records = [r for r in records if r["species"] == species_filter]
        log.info(f"Filtered: species={species_filter} → {len(records)} records")

    log.info(f"Total benchmark records to process: {len(records)}")

    if dry_run:
        cnt = Counter(r["species"] for r in records)
        log.info("[DRY RUN] Species breakdown:")
        for sp in sorted(cnt):
            log.info(f"  {sp:<32} {cnt[sp]:>3} records")
        log.info(f"  {'TOTAL':<32} {sum(cnt.values()):>3}")
        return

    if not DB_PATH.exists():
        log.error(f"DB not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    written = skipped = error = 0

    for r in records:
        record_id = rid("seed_v2", r["species"], r["kpi_id"],
                        r.get("region", "GLOBAL"),
                        r.get("production_stage", ""))

        existing = conn.execute(
            "SELECT credibility FROM market_kpi WHERE id=?", (record_id,)
        ).fetchone()

        if existing and existing[0] >= r["credibility"]:
            skipped += 1
            continue

        try:
            conn.execute("""
                INSERT OR REPLACE INTO market_kpi
                (id, region, country, species, production_stage, kpi_id,
                 value, value_min, value_max, unit, year,
                 credibility, source_type, source_url, source_title,
                 raw_text, language, confirmed, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                record_id,
                r.get("region", "GLOBAL"), "",
                r["species"], r.get("production_stage"),
                r["kpi_id"], r["value"],
                r.get("value_min"), r.get("value_max"),
                r["unit"], r.get("year", 2022),
                r["credibility"],
                r.get("source_type", "academic_background"), "",
                r.get("source_title", ""), r.get("note", ""),
                "en", 1, NOW,
            ))
            written += 1
        except Exception as e:
            log.warning(f"DB error [{r['species']}:{r['kpi_id']}]: {e}")
            error += 1

    conn.commit()

    total     = conn.execute("SELECT COUNT(*) FROM market_kpi").fetchone()[0]
    confirmed = conn.execute("SELECT COUNT(*) FROM market_kpi WHERE confirmed=1").fetchone()[0]
    rows      = conn.execute(
        "SELECT species, COUNT(*) c FROM market_kpi GROUP BY species ORDER BY species"
    ).fetchall()
    conn.close()

    log.info("=" * 65)
    log.info(f"Written={written} | Skipped={skipped} | Error={error}")
    log.info(f"DB total={total} | confirmed={confirmed}")
    log.info("Species in DB:")
    for sp, cnt in rows:
        log.info(f"  {sp:<32} {cnt}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--species",  default="")
    parser.add_argument("--reset",    action="store_true",
                        help="Delete all confirmed=1 rows first")
    args = parser.parse_args()

    if args.reset and not args.dry_run:
        conn = sqlite3.connect(DB_PATH)
        deleted = conn.execute("DELETE FROM market_kpi WHERE confirmed=1").rowcount
        conn.commit()
        conn.close()
        log.info(f"Reset: deleted {deleted} seeded records")

    seed(dry_run=args.dry_run, species_filter=args.species)


if __name__ == "__main__":
    main()
