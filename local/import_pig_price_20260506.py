# -*- coding: utf-8 -*-
"""
import_pig_price_20260506.py
來源：飼料社網 2026-05-06 生豬價格行情
寫入 market_kpi table（price 類型）
"""
import sqlite3, uuid
from datetime import datetime

DB_PATH = r'D:\LLM\knowledge\market\market_data.db'
NOW = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
SOURCE_URL   = 'https://www.siliao.com/pig-price/20260506'
SOURCE_TITLE = '飼料社網 2026-05-06 全國生豬價格行情'

# (province, region_cn, tuzai, neisan, waishan) 單位：元/斤
pig_prices = [
    ('安徽', 'CN_east',  5.30, 5.15, 5.17),
    ('山東', 'CN_east',  4.99, 5.22, 5.16),
    ('浙江', 'CN_east',  4.83, 5.46, 5.22),
    ('江西', 'CN_east',  5.50, 5.65, 4.75),
    ('福建', 'CN_east',  5.50, 5.50, 5.01),
    ('江蘇', 'CN_east',  5.20, 5.45, 5.22),
    ('上海', 'CN_east',  5.00, 5.00, 5.17),
    ('新疆', 'CN_north', 4.23, 4.33, 4.64),
    ('陝西', 'CN_north', 4.85, 4.80, 4.98),
    ('甘肅', 'CN_north', 4.30, 4.95, 4.45),
    ('青海', 'CN_north', 4.02, 4.01, 4.58),
    ('寧夏', 'CN_north', 4.87, 4.80, 4.98),
    ('河南', 'CN_central',4.79, 4.87, 5.05),
    ('湖南', 'CN_central',4.84, 4.99, 4.72),
    ('湖北', 'CN_central',4.71, 4.47, 4.92),
    ('北京', 'CN_north', 5.25, 4.50, 4.99),
    ('天津', 'CN_north', 5.95, 6.25, 5.06),
    ('山西', 'CN_north', 4.84, 4.89, 4.98),
    ('河北', 'CN_north', 5.00, 5.21, 5.06),
    ('內蒙古','CN_north',5.50, 5.50, 4.89),
    ('廣西', 'CN_south', 5.00, 5.00, 4.56),
    ('廣東', 'CN_south', 5.00, 5.20, 5.17),
    ('海南', 'CN_south', 4.66, 4.74, 4.15),
    ('遼寧', 'CN_northeast',4.75,5.23,5.09),
    ('黑龍江','CN_northeast',4.60,4.78,4.73),
    ('吉林', 'CN_northeast',4.64,4.91,4.72),
    ('四川', 'CN_southwest',4.50,4.60,4.70),
    ('貴州', 'CN_southwest',5.50,5.50,4.51),
    ('雲南', 'CN_southwest',4.75,4.65,4.66),
    ('重慶', 'CN_southwest',5.00,6.00,4.68),
    ('西藏', 'CN_southwest',4.84,5.29,3.71),
]

# 全國均價
national_avg = {'今日': (4.96, 5.09, 4.84), '昨日': (4.97, 5.08, 4.87)}

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
inserted = skipped = 0

for province, region, tuzai, neisan, waishan in pig_prices:
    # 換算均價（元/斤 → 元/kg × 2）
    avg_price = round((tuzai + neisan + waishan) / 3 * 2, 2)  # 元/kg

    for grade, price_jin in [('tuzai', tuzai), ('neisan', neisan), ('waishan', waishan)]:
        kpi_id = f'spot_price_pig_{grade}_{province}'
        price_kg = round(price_jin * 2, 2)

        exists = cur.execute(
            "SELECT id FROM market_kpi WHERE kpi_id=? AND year=2026",
            (kpi_id,)).fetchone()
        if exists:
            skipped += 1
            continue

        cur.execute("""INSERT INTO market_kpi
            (id,region,country,species,production_stage,kpi_id,
             value,unit,year,credibility,source_type,
             source_url,source_title,raw_text,language,confirmed,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            str(uuid.uuid4()), region, 'CN',
            'finisher_pig', 'slaughter',
            kpi_id, price_kg, 'CNY/kg', 2026,
            4, 'industry_media',
            SOURCE_URL, SOURCE_TITLE,
            f'{province} {grade} {price_jin}元/斤 = {price_kg}元/kg 2026-05-06',
            'zh-CN', 1, NOW))
        inserted += 1

# 全國均價
for label, (t, n, w) in national_avg.items():
    avg = round((t+n+w)/3*2, 2)
    kpi_id = f'spot_price_pig_national_avg_{label}'
    if not cur.execute("SELECT id FROM market_kpi WHERE kpi_id=?", (kpi_id,)).fetchone():
        cur.execute("""INSERT INTO market_kpi
            (id,region,country,species,production_stage,kpi_id,
             value,unit,year,credibility,source_type,
             source_url,source_title,raw_text,language,confirmed,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            str(uuid.uuid4()), 'CN_all', 'CN',
            'finisher_pig', 'slaughter',
            kpi_id, avg, 'CNY/kg', 2026,
            4, 'industry_media',
            SOURCE_URL, SOURCE_TITLE,
            f'全國均價{label} tuzai={t} neisan={n} waishan={w} 元/斤',
            'zh-CN', 1, NOW))
        inserted += 1

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
print(f'Done. Inserted: {inserted}, Skipped: {skipped}')
print(f'market_kpi total: {total} rows')
conn.close()
