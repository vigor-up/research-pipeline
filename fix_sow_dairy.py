import sqlite3, uuid
from datetime import datetime
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
NOW = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

data = [
    # 哺乳母豬
    ('breeding_sow', 'feed_cost_sow_lactation_ton2', 3300, 'CNY/ton', 'CN_all', 5, '哺乳母豬料3.3元/kg=3300元/噸 李安軍2025'),
    ('breeding_sow', 'total_cost_sow_per_year', 3110, 'CNY/year', 'CN_all', 5, '母豬年飼料總成本3110元（妊娠1868+哺乳1241）李安軍2025'),
    ('breeding_sow', 'total_cost_per_weaned_piglet_full', 124, 'CNY/head', 'CN_all', 5, '每頭斷奶仔豬母豬飼料成本124元/頭，PSY=25，李安軍2025'),
    ('breeding_sow', 'breakeven_sow_annual_revenue', 430, 'CNY/sow/year', 'CN_all', 4, '活力旺每頭母豬年增收430元（+0.5頭仔豬+存活率+3%）'),
    # 奶牛飼料成本
    ('dairy_cow', 'feed_cost_dairy_concentrate_ton', 1990, 'CNY/ton', 'CN_all', 5, '奶牛精料1.99元/kg=1990元/噸 2026Q1山東'),
    ('dairy_cow', 'feed_cost_dairy_total_ton', 2750, 'CNY/ton', 'CN_all', 5, '奶牛飼養成本2.75元/kg=2750元/噸 2026Q1'),
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
            '', '哺乳母豬奶牛飼料成本補齊', raw, 'zh-CN', 1, NOW))
        n += 1

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
print(f'新增{n}筆，DB總計{total}筆')
conn.close()
