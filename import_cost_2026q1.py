import sqlite3, uuid
from datetime import datetime

conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
NOW = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

data = [
    # 哺乳母豬（李安軍2025）
    ('breeding_sow', 'feed_consumption_sow_annual_kg', 1055.6, 'kg/year', 'CN_all', 4, '母豬年飼料總耗用1055.6kg（妊娠679.4+哺乳376.2）'),
    ('breeding_sow', 'feed_cost_sow_annual_cny', 3109.81, 'CNY/year', 'CN_all', 4, '母豬年飼料總費用3109.81元，妊娠料2.75元/kg，哺乳料3.3元/kg'),
    ('breeding_sow', 'feed_cost_per_weaned_piglet', 124.4, 'CNY/head', 'CN_all', 4, '每頭斷奶仔豬母豬飼料成本124.4元，PSY=25'),
    ('breeding_sow', 'daily_feed_lactation_kg', 5.2, 'kg/day', 'CN_all', 4, '哺乳母豬日採食量5.2kg，哺乳期28天'),
    ('breeding_sow', 'daily_feed_gestation_kg', 2.4, 'kg/day', 'CN_all', 4, '妊娠母豬日採食量2.4kg'),
    ('breeding_sow', 'psy_industry_avg', 25.0, 'head/year', 'CN_all', 4, 'PSY行業均值25頭/母豬/年'),
    ('breeding_sow', 'litter_per_year', 2.45, 'litter/year', 'CN_all', 4, '母豬年胎次2.45胎'),
    ('breeding_sow', 'weaned_per_litter', 10.2, 'head/litter', 'CN_all', 4, '每窩平均斷奶仔豬數10.2頭'),
    # 育肥豬完全成本（2026Q1山東官方）
    ('finisher_pig', 'total_cost_selfbred_per_kg', 12.81, 'CNY/kg', 'CN_all', 5, '2026Q1自繁自育完全成本12.81元/kg，120kg出欄，盈亏线13.20'),
    ('finisher_pig', 'total_cost_purchased_per_kg', 12.03, 'CNY/kg', 'CN_all', 5, '2026Q1外購仔豬育肥完全成本12.03元/kg，盈亏线12.39'),
    ('finisher_pig', 'total_cost_scale_farm_per_kg', 13.23, 'CNY/kg', 'CN_all', 5, '2026Q1規模場完全成本13.23元/kg，出欄132kg，頭均虧損80元'),
    ('finisher_pig', 'breakeven_price_selfbred', 13.20, 'CNY/kg', 'CN_all', 5, '2026Q1自繁自育盈亏線13.20元/kg'),
    ('finisher_pig', 'breakeven_price_purchased', 12.39, 'CNY/kg', 'CN_all', 5, '2026Q1外購仔豬育肥盈亏線12.39元/kg'),
    ('finisher_pig', 'cost_detail_feed_per_head', 948, 'CNY/head', 'CN_all', 5, '自繁自育飼料成本948元/頭'),
    ('finisher_pig', 'cost_detail_piglet', 300, 'CNY/head', 'CN_all', 5, '自繁自育仔豬成本300元/頭（21日齡斷奶）'),
    ('finisher_pig', 'other_cost_per_head', 160, 'CNY/head', 'CN_all', 4, '疫苗60-80+人工水電50-70+廠房20-40=160元/頭'),
    ('finisher_pig', 'feed_price_lactation', 3300, 'CNY/ton', 'CN_all', 4, '哺乳料3.3元/kg=3300元/噸'),
    ('finisher_pig', 'feed_price_gestation', 2750, 'CNY/ton', 'CN_all', 4, '妊娠料2.75元/kg=2750元/噸'),
    # 肉雞（2026Q1）
    ('broiler', 'total_cost_per_kg_2026q1', 7.01, 'CNY/kg', 'CN_all', 5, '2026Q1白羽肉雞完全成本7.01元/kg，40-42天，出欄2.75kg'),
    ('broiler', 'feed_price_broiler_2026q1', 3650, 'CNY/ton', 'CN_all', 5, '2026Q1肉雞飼料3.65元/kg=3650元/噸'),
    ('broiler', 'chick_cost_2026q1', 2.90, 'CNY/chick', 'CN_all', 5, '2026Q1雞苗2.90元/只'),
    # 肉鴨（2026Q1）
    ('duck', 'total_cost_per_kg_large_2026q1', 6.4, 'CNY/kg', 'CN_all', 5, '2026Q1大鴨完全成本6.4元/kg，36-37天，3kg出欄，19.1元/只'),
    ('duck', 'spot_price_duck_2026q1', 6.8, 'CNY/kg', 'CN_all', 5, '2026Q1白羽肉鴨均價6.8元/kg，大鴨盈利0.8-1.0元/只'),
    ('duck', 'spot_price_duck_guangdong_202605', 7.4, 'CNY/kg', 'CN_south', 4, '2026-05廣東白羽肉鴨3.7元/斤=7.4元/kg'),
    ('duck', 'feed_cost_duck_large', 15.5, 'CNY/bird', 'CN_all', 5, '大鴨飼料成本15.5元/只（36-37天）'),
    # 蛋雞（2026Q1）
    ('layer_chicken', 'total_cost_per_kg_egg_scale', 7.4, 'CNY/kg', 'CN_all', 5, '2026Q1規模場鷄蛋完全成本7.0-7.8元/kg均值7.4，扣淘汰雞後'),
    ('layer_chicken', 'breakeven_egg_price', 7.0, 'CNY/kg', 'CN_all', 5, '2026Q1蛋雞養殖盈亏線7.0元/kg（規模場）'),
    ('layer_chicken', 'feed_cost_layer_2026q1', 2800, 'CNY/ton', 'CN_all', 5, '2026Q1蛋雞全價料2800元/噸'),
    ('layer_chicken', 'rearing_cost_per_hen', 28, 'CNY/hen', 'CN_all', 5, '蛋雞育成成本28元/只（前期），總投入160元/只'),
    # 肉牛（2026Q1）
    ('beef_cattle', 'total_cost_feedlot_per_head', 16450, 'CNY/head', 'CN_all', 5, '2026Q1專業育肥完全成本16450元/頭（650kg出欄）：架子牛8000+飼草料7500+其他950'),
    ('beef_cattle', 'breakeven_price_feedlot', 25.0, 'CNY/kg', 'CN_all', 5, '2026Q1肉牛育肥盈亏線25元/kg'),
    ('beef_cattle', 'profit_per_head_feedlot', 1132, 'CNY/head', 'CN_all', 5, '2026Q1專業育肥頭均盈利1132元，均價27.05元/kg'),
    ('beef_cattle', 'feeder_cattle_cost', 8000, 'CNY/head', 'CN_all', 5, '2026Q1架子牛購入均價8000元/頭'),
    ('beef_cattle', 'feed_cost_feedlot_per_head', 7500, 'CNY/head', 'CN_all', 5, '2026Q1育肥牛飼草料成本7500元/頭'),
    # 肉羊（2026Q1）
    ('meat_sheep', 'total_cost_merino_selfbred', 1481, 'CNY/head', 'CN_all', 5, '2026Q1綿羊自繁自育完全成本1481元/只（60kg），24.68元/kg'),
    ('meat_sheep', 'total_cost_merino_feedlot', 1499, 'CNY/head', 'CN_all', 5, '2026Q1綿羊集中育肥完全成本1499元/只，24.98元/kg'),
    ('meat_sheep', 'total_cost_goat_selfbred', 1696, 'CNY/head', 'CN_all', 5, '2026Q1山羊自繁自育完全成本1696元/只，28.27元/kg'),
    ('meat_sheep', 'breakeven_price_merino', 24.98, 'CNY/kg', 'CN_all', 5, '2026Q1綿羊盈亏線約25元/kg'),
    ('meat_sheep', 'profit_merino_selfbred', 139, 'CNY/head', 'CN_all', 5, '2026Q1綿羊自繁自育每只盈利139元，均價27元/kg'),
    ('meat_sheep', 'profit_goat_selfbred', 344, 'CNY/head', 'CN_all', 5, '2026Q1山羊自繁自育每只盈利344元，均價34元/kg'),
    # 奶牛（2026Q1）
    ('dairy_cow', 'total_cost_per_kg_milk', 3.40, 'CNY/kg', 'CN_all', 5, '2026Q1奶牛全成本3.40元/kg生乳（含後備牛）'),
    ('dairy_cow', 'feed_cost_per_kg_milk', 2.75, 'CNY/kg', 'CN_all', 5, '2026Q1奶牛飼養成本2.75元/kg，精料1.99元/kg'),
    ('dairy_cow', 'milk_purchase_price_2026q1', 3.05, 'CNY/kg', 'CN_all', 5, '2026Q1生乳收購均價3.05元/kg，盈亏線3.35元/kg'),
    ('dairy_cow', 'breakeven_daily_yield', 33, 'kg/day', 'CN_all', 5, '奶牛盈亏平衡日產量33kg'),
    ('dairy_cow', 'loss_per_head_2026q1', 805, 'CNY/head', 'CN_all', 5, '2026Q1奶牛頭均虧損805元'),
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
            '', '2026Q1畜禽養殖成本收益測算_山東省畜牧獸醫局', raw, 'zh-CN', 1, NOW))
        n += 1

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
print(f'新增{n}筆，DB總計{total}筆')
conn.close()
