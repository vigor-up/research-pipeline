# -*- coding: utf-8 -*-
"""
import_soybean_20260507.py
2026-05-07 豆粕報價（每月更新一次即可）
"""
import sqlite3, uuid
from datetime import datetime

DB_PATH = r'D:\LLM\knowledge\market\market_data.db'
NOW  = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
YEAR = 2026
SRC  = '豆粕現貨報價 2026-05-07'

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
n = 0

def ins(kpi_id, region, val, note):
    global n
    if cur.execute("SELECT id FROM market_kpi WHERE kpi_id=?", (kpi_id,)).fetchone():
        return
    cur.execute("""INSERT INTO market_kpi
        (id,region,country,species,production_stage,kpi_id,
         value,unit,year,credibility,source_type,
         source_url,source_title,raw_text,language,confirmed,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        str(uuid.uuid4()), region, 'CN', 'feed_ingredient',
        'spot_price', kpi_id, val, 'CNY/ton', YEAR,
        4, 'industry_media', '', SRC, note, 'zh-CN', 1, NOW))
    n += 1

# 東北（對出差最重要）
ins('soybean_meal_43_northeast_avg_20260507', 'CN_northeast', 3010,
    '東北均值 鐵嶺3000/長春3050/大連3000/丹東3020/盤錦2980/營口2980')
ins('soybean_meal_43_shandong_avg_20260507',  'CN_north',     2916,
    '山東均值約2916 日照2870-2980區間')
ins('soybean_meal_43_north_avg_20260507',     'CN_north',     2935,
    '華北均值 北京2950/天津2910-2950')
ins('soybean_meal_43_east_avg_20260507',      'CN_east',      2930,
    '華東均值 江蘇2900-2980')
ins('soybean_meal_43_south_avg_20260507',     'CN_south',     2945,
    '華南均值 東莞2930/湛江2960')
ins('soybean_meal_43_national_avg_20260507',  'CN_all',       2940,
    '全國43%豆粕均值約2940元/噸 2026-05-07')

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
conn.close()
print(f'Done. Inserted: {n} | DB: {total}')
print()
print('東北飼料成本（月度基準）：')
corn = 2220; soy = 3010
cost = (corn*0.60 + soy*0.20 + 2800*0.20)/1000
print(f'  玉米 {corn}元/噸 × 60% = {corn*0.6:.0f}')
print(f'  豆粕 {soy}元/噸 × 20% = {soy*0.2:.0f}')
print(f'  其他 2800元/噸 × 20% = {2800*0.2:.0f}')
print(f'  配合飼料成本 = {cost:.3f}元/kg')
