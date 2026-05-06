# -*- coding: utf-8 -*-
"""
import_yearbook_2025.py
中国统计年鉴2025 第十二章 → market_kpi DB
用途：市場規模參考（非ROI基準值）
kpi_id: market_population / market_output
"""

import sqlite3
import uuid
from datetime import datetime

DB_PATH = r'D:\LLM\knowledge\market\market_data.db'
SOURCE_URL = 'https://www.stats.gov.cn/sj/ndsj/2025/'
SOURCE_TITLE = '中国统计年鉴2025 第十二章农业'
NOW = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

records = [
    # --- 12-13 存欄/出欄頭數 ---
    # species, production_stage, kpi_id, value, unit, year
    ('cattle',          'all',      'market_population',  10046.5,  '万头',  2024),
    ('cattle',          'all',      'market_population',  10508.5,  '万头',  2023),
    ('finisher_pig',    'all',      'market_slaughter',   42742.9,  '万头',  2024),
    ('finisher_pig',    'all',      'market_slaughter',   43422.3,  '万头',  2023),
    ('pig',             'all',      'market_population',  30049.3,  '万头',  2024),
    ('pig',             'all',      'market_population',  32232.6,  '万头',  2023),
    ('meat_goat',       'all',      'market_population',  11755.4,  '万只',  2024),
    ('meat_goat',       'all',      'market_population',  12934.2,  '万只',  2023),
    ('meat_sheep',      'all',      'market_population',  18293.9,  '万只',  2024),
    ('meat_sheep',      'all',      'market_population',  19298.4,  '万只',  2023),

    # --- 12-14 畜產品產量 ---
    ('finisher_pig',    'all',      'market_meat_output',  5706.0,  '万吨',  2024),
    ('finisher_pig',    'all',      'market_meat_output',  5794.3,  '万吨',  2023),
    ('beef_cattle',     'all',      'market_meat_output',   779.1,  '万吨',  2024),
    ('beef_cattle',     'all',      'market_meat_output',   752.7,  '万吨',  2023),
    ('meat_sheep',      'all',      'market_meat_output',   517.8,  '万吨',  2024),
    ('meat_sheep',      'all',      'market_meat_output',   531.3,  '万吨',  2023),
    ('dairy_cow',       'all',      'market_milk_output',  4079.4,  '万吨',  2024),
    ('dairy_cow',       'all',      'market_milk_output',  4196.7,  '万吨',  2023),
    ('layer_chicken',   'all',      'market_egg_output',   3588.5,  '万吨',  2024),
    ('layer_chicken',   'all',      'market_egg_output',   3563.0,  '万吨',  2023),
]

def make_id():
    return str(uuid.uuid4())

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

inserted = 0
skipped = 0

for species, stage, kpi_id, value, unit, year in records:
    # 避免重複：同 species + kpi_id + year + region
    existing = cur.execute(
        "SELECT id FROM market_kpi WHERE species=? AND kpi_id=? AND year=? AND region='CN_all'",
        (species, kpi_id, year)
    ).fetchone()

    if existing:
        skipped += 1
        continue

    cur.execute("""
        INSERT INTO market_kpi
            (id, region, country, species, production_stage, kpi_id,
             value, unit, year, credibility, source_type,
             source_url, source_title, raw_text, language, confirmed, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        make_id(),
        'CN_all', 'CN',
        species, stage, kpi_id,
        value, unit, year,
        4,                        # credibility: gov_stats = 4
        'gov_stats',
        SOURCE_URL, SOURCE_TITLE,
        f'{kpi_id} {value} {unit} {year}',
        'zh-CN', 1,               # confirmed=1（官方數據直接確認）
        NOW
    ))
    inserted += 1

conn.commit()
conn.close()

total = cur.execute if False else None
print(f'Done. Inserted: {inserted}, Skipped: {skipped}')
print(f'Total records in DB:')

# 驗證
conn2 = sqlite3.connect(DB_PATH)
total = conn2.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
print(f'  market_kpi: {total} rows')
conn2.close()
