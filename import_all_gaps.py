import sqlite3, uuid
from datetime import datetime
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
NOW = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

data = [
    # 哺乳母豬淘汰價 2026-05-07
    ('breeding_sow', 'spot_price_sow_slaughter_cn', 9.6, 'CNY/kg', 'CN_all', 5, '哺乳母豬淘汰價全國均值4.8元/斤=9.6元/kg 2026-05-07'),
    ('breeding_sow', 'spot_price_sow_northeast', 9.3, 'CNY/kg', 'CN_northeast', 5, '東北哺乳母豬淘汰價均值4.65元/斤=9.3元/kg 黑龍江/吉林/遼寧'),
    ('breeding_sow', 'spot_price_sow_east', 10.2, 'CNY/kg', 'CN_east', 5, '華東哺乳母豬淘汰價均值5.1元/斤=10.2元/kg 山東/江蘇/浙江'),
    # 能繁母豬（懷孕母豬）售價
    ('breeding_sow', 'price_pregnant_sow_1parity_40d', 3300, 'CNY/head', 'CN_all', 5, '1胎40-60孕齡懷孕母豬3300元/頭 2026-05'),
    ('breeding_sow', 'price_pregnant_sow_23parity_100d', 4900, 'CNY/head', 'CN_all', 5, '2-3胎100日齡以上懷孕母豬4900元/頭 市場最活躍 2026-05'),
    ('breeding_sow', 'price_pregnant_sow_avg', 4300, 'CNY/head', 'CN_all', 5, '能繁懷孕母豬均值4300元/頭（2-3胎中段孕齡）2026-05'),
    # 能繁母豬存欄與豬周期
    ('finisher_pig', 'breeding_sow_inventory_202512', 3961, '10k_head', 'CN_all', 5, '2025年12月能繁母豬存欄3961萬頭，調減目標3950萬頭'),
    ('finisher_pig', 'psy_national_202512', 24.3, 'head/sow/year', 'CN_all', 5, 'PSY全國2025年12月24.3頭'),
    ('finisher_pig', 'sow_inventory_price_corr', -0.80, 'correlation', 'CN_all', 5, '能繁母豬存欄與滯後10個月豬價相關係數-0.80（極強負相關）'),
    # 肉羊育肥實測分階段數據
    ('meat_sheep', 'adg_phase1_1_30d', 0.33, 'kg/day', 'CN_all', 4, '肉羊育肥前期1-30天日增重0.33kg，料肉比5.24，造肉成本10.7元/kg'),
    ('meat_sheep', 'adg_phase2_31_60d', 0.292, 'kg/day', 'CN_all', 4, '肉羊育肥中期31-60天日增重0.292kg，料肉比6.69，造肉成本13.7元/kg'),
    ('meat_sheep', 'adg_phase3_61_90d', 0.346, 'kg/day', 'CN_all', 4, '肉羊育肥後期61-90天日增重0.346kg，料肉比6.63，造肉成本13.6元/kg'),
    ('meat_sheep', 'feed_cost_90d_total', 367.8, 'CNY/head', 'CN_all', 4, '肉羊90天育肥飼料費用367.8元/只（106.4+120.2+141.2）'),
    ('meat_sheep', 'total_cost_90d_complete', 967.8, 'CNY/head', 'CN_all', 4, '肉羊90天完全成本967.8元/只（購羊540+飼料367.8+其他60）'),
    ('meat_sheep', 'feed_cost_sheep_concentrate_ton', 2800, 'CNY/ton', 'CN_all', 4, '肉羊精料均值2800元/噸（玉米豆粕型2800-3000，棉粕型2600-2800）'),
    ('meat_sheep', 'feed_formula_cost_early', 2053, 'CNY/ton', 'CN_all', 4, '肉羊育肥前期配方成本2053元/噸（玉米43%+豆粕13.5%+苜蓿15%+秸稈20%）'),
    ('meat_sheep', 'feed_formula_cost_late', 2095, 'CNY/ton', 'CN_all', 4, '肉羊育肥後期配方成本2095元/噸（玉米50%+豆粕11.5%+苜蓿15%+秸稈15%）'),
    # 肉牛飼料成本實測
    ('beef_cattle', 'feed_cost_per_kg_gain_small', 17.04, 'CNY/kg', 'CN_all', 4, '小規模育肥牛每kg增重飼料成本17.04元，日增重1.14kg，日費用19.4元 2026-03'),
    ('beef_cattle', 'total_feed_cost_300d', 5820, 'CNY/head', 'CN_all', 4, '育肥牛300天總飼料成本5820元/頭（小中規模均值）'),
    ('beef_cattle', 'feed_cost_cattle_conc_ton', 2825, 'CNY/ton', 'CN_all', 4, '肉牛育肥成品配合飼料2800-2850元/噸均值2825元/噸 2026-05'),
    ('beef_cattle', 'daily_feed_cost_tmr', 27.29, 'CNY/head/day', 'CN_all', 4, 'TMR日糧總成本27.29元/頭/天，造肉成本18.19元/kg增重'),
    ('beef_cattle', 'daily_intake_concentrate_kg', 5.85, 'kg/day', 'CN_all', 4, '育肥牛日採食精料5.85kg（玉米3.51+豆粕1.02+豆餅0.58+麩0.29+其他0.45）'),
    ('beef_cattle', 'mother_cow_annual_feed_cost', 5090, 'CNY/year', 'CN_all', 4, '繁殖母牛年飼料成本均值5090元（4540-5640元/頭）'),
    # 奶牛盈亏線修正
    ('dairy_cow', 'breakeven_milk_price', 3.35, 'CNY/kg', 'CN_all', 5, '奶牛盈亏線生乳價格3.35元/kg（泌乳牛成本），全群3.40元/kg'),
    ('dairy_cow', 'breakeven_daily_yield_q1', 33, 'kg/day', 'CN_all', 5, '奶牛盈亏平衡日產量33kg（2026Q1），Q4為32kg'),
    ('dairy_cow', 'low_yield_breakeven', 17, 'kg/day', 'CN_all', 4, '奶牛低產牛盈亏線17kg/天（牛奶3.8元/kg，飼料65元/頭/天假設）'),
    # 肉雞盈亏線補充
    ('broiler', 'breakeven_price_2026q1', 7.01, 'CNY/kg', 'CN_all', 5, '肉雞盈亏線7.01元/kg（完全成本），市場盈亏平衡約6.9-7.0元/kg'),
    # 肉鴨盈亏線補充
    ('duck', 'breakeven_price_large_duck', 6.4, 'CNY/kg', 'CN_all', 5, '大鴨養殖端盈亏線6.4元/kg（2026Q1完全成本），微利需>6.4元/kg'),
    ('duck', 'feed_cost_large_duck_per_ton', 2900, 'CNY/ton', 'CN_all', 4, '肉鴨飼料成本北方3000-3200元/噸，南方2300-2800元/噸，均值2900元/噸'),
]

n = 0
for species, kpi_id, value, unit, region, cred, raw in data:
    exists = conn.execute("SELECT id FROM market_kpi WHERE kpi_id=?", (kpi_id,)).fetchone()
    if not exists:
        conn.execute("""INSERT INTO market_kpi
            (id,region,country,species,production_stage,kpi_id,
             value,unit,year,credibility,source_type,
             source_url,source_title,raw_text,language,confirmed,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            str(uuid.uuid4()), region, 'CN', species, 'production',
            kpi_id, value, unit, 2026, cred, 'industry_media',
            '', '2026-05主力物種成本盈亏線完整版', raw, 'zh-CN', 1, NOW))
        n += 1

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
print(f'新增{n}筆，DB總計{total}筆')
conn.close()
