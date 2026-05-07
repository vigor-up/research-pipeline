import sqlite3, uuid
from datetime import datetime

conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
NOW = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

data = [
    # 哺乳母豬飼料成本（實測數據，credibility=4）
    ('breeding_sow', 'feed_consumption_sow_annual_kg', 1055.6, 'kg/year', 'CN_all', 4, '母豬年飼料總耗用1055.6kg（妊娠679.4+哺乳376.2）李安軍動態營養2025'),
    ('breeding_sow', 'feed_cost_sow_annual_cny', 3109.81, 'CNY/year', 'CN_all', 4, '母豬年飼料總費用3109.81元，妊娠料2.75元/kg，哺乳料3.3元/kg'),
    ('breeding_sow', 'feed_cost_per_weaned_piglet', 124.4, 'CNY/head', 'CN_all', 4, '每頭斷奶仔豬耗用母豬飼料成本124.4元，PSY=25'),
    ('breeding_sow', 'daily_feed_lactation_kg', 5.2, 'kg/day', 'CN_all', 4, '哺乳母豬日採食量5.2kg，哺乳期28天'),
    ('breeding_sow', 'daily_feed_gestation_kg', 2.4, 'kg/day', 'CN_all', 4, '妊娠母豬日採食量2.4kg'),
    ('breeding_sow', 'psy_industry_avg', 25.0, 'head/sow/year', 'CN_all', 4, 'PSY行業均值25頭/母豬/年（李安軍計算基準）'),
    ('breeding_sow', 'litter_per_year', 2.45, 'litter/year', 'CN_all', 4, '母豬年胎次2.45胎'),
    ('breeding_sow', 'weaned_per_litter', 10.2, 'head/litter', 'CN_all', 4, '每窩平均斷奶仔豬數10.2頭'),
    # 商品豬完全成本基準
    ('finisher_pig', 'total_cost_per_kg_avg', 13.5, 'CNY/kg', 'CN_all', 4, '商品豬完全成本均值：PSY=20,FCR=2.8,死淘10%，13.5元/kg'),
    ('finisher_pig', 'total_cost_per_kg_good', 11.4, 'CNY/kg', 'CN_all', 4, '商品豬完全成本優良：PSY=25,FCR=2.4,死淘5%，11.4元/kg'),
    ('finisher_pig', 'total_cost_per_kg_poor', 16.3, 'CNY/kg', 'CN_all', 4, '商品豬完全成本差：PSY=15,FCR=3.3,死淘15%，16.3元/kg'),
    ('finisher_pig', 'other_cost_per_head', 160, 'CNY/head', 'CN_all', 4, '商品豬其他成本：疫苗60-80+人工水電50-70+廠房20-40=160元/頭'),
    ('finisher_pig', 'feed_price_gestation', 2750, 'CNY/ton', 'CN_all', 4, '妊娠料2.75元/kg=2750元/噸'),
    ('finisher_pig', 'feed_price_lactation', 3300, 'CNY/ton', 'CN_all', 4, '哺乳料3.3元/kg=3300元/噸'),
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
            kpi_id, value, unit, 2025, cred, 'industry_expert',
            '', '李安軍動態營養AB料成本計算2025', raw, 'zh-CN', 1, NOW))
        n += 1

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
print(f'新增{n}筆，DB總計{total}筆')
conn.close()
