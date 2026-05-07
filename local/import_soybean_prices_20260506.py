# -*- coding: utf-8 -*-
"""
import_soybean_prices_20260506.py
2026-05-06 豆粕現貨價格 + 大豆期貨市場分析
來源：鋼聯數據 + feedtrade
"""
import sqlite3, uuid
from datetime import datetime

DB_PATH = r'D:\LLM\knowledge\market\market_data.db'
NOW  = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
YEAR = 2026
SOURCE_TITLE = '鋼聯數據 豆粕價格匯總 2026-05-06'
SOURCE_URL   = 'https://m.feedtrade.com.cn/index/index'

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
n = 0

def ins(kpi_id, region, value, vmin, vmax, unit, note):
    global n
    if cur.execute("SELECT id FROM market_kpi WHERE kpi_id=? AND year=?",
                   (kpi_id, YEAR)).fetchone():
        return
    cur.execute("""INSERT INTO market_kpi
        (id,region,country,species,production_stage,kpi_id,
         value,value_min,value_max,unit,year,
         credibility,source_type,source_url,source_title,
         raw_text,language,confirmed,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        str(uuid.uuid4()), region, 'CN',
        'feed_ingredient', 'spot_price', kpi_id,
        value, vmin, vmax, unit, YEAR,
        4, 'industry_media', SOURCE_URL, SOURCE_TITLE,
        note, 'zh-CN', 1, NOW))
    n += 1

# ══════════════════════════════════════════════════════
# 1. 43%豆粕現貨價（省級）
# ══════════════════════════════════════════════════════
soy43 = [
    ('soybean_meal_43_liaoning',  'CN_northeast', 2980, None, None, '遼寧 43%豆粕 2980元/噸 +20'),
    ('soybean_meal_43_tianjin',   'CN_north',     2940, None, None, '天津 43%豆粕 2940元/噸 +10'),
    ('soybean_meal_43_shandong',  'CN_north',     2900, None, None, '山東 43%豆粕 2900元/噸 -20'),
    ('soybean_meal_43_jiangsu',   'CN_east',      2900, None, None, '江蘇 43%豆粕 2900元/噸 -10'),
    ('soybean_meal_43_guangdong', 'CN_south',     2920, None, None, '廣東 43%豆粕 2920元/噸 -30'),
]
for kid, reg, val, vmin, vmax, note in soy43:
    ins(kid, reg, val, vmin, vmax, 'CNY/ton', note)

# ══════════════════════════════════════════════════════
# 2. 高蛋白豆粕（45-46%）
# ══════════════════════════════════════════════════════
soy_hp = [
    ('soybean_meal_45_yingkou',   'CN_northeast', 3100, None, None, '盈錦45% 3100元/噸 -10'),
    ('soybean_meal_46_tianjin',   'CN_north',     3160, None, None, '天津46% 3160元/噸 0'),
    ('soybean_meal_46_rizhao',    'CN_north',     3090, None, None, '日照46% 3090元/噸 -20'),
    ('soybean_meal_46_nantong',   'CN_east',      3090, None, None, '南通46% 3090元/噸 0'),
    ('soybean_meal_46_dongguan',  'CN_south',     3110, None, None, '東莞46% 3110元/噸 -20'),
]
for kid, reg, val, vmin, vmax, note in soy_hp:
    ins(kid, reg, val, vmin, vmax, 'CNY/ton', note)

# ══════════════════════════════════════════════════════
# 3. 東北均價（ROI計算用）
# ══════════════════════════════════════════════════════
ins('soybean_meal_43_northeast_avg', 'CN_northeast',
    2980, 2940, 3100, 'CNY/ton',
    '東北豆粕均值 遼寧2980/盈錦3100 均約2980元/噸 2026-05-06')

ins('soybean_meal_national_avg', 'CN_all',
    2940, 2900, 3160, 'CNY/ton',
    '全國43%豆粕均值約2940元/噸 2026-05-06')

# ══════════════════════════════════════════════════════
# 4. 大豆期貨市場背景（影響未來豆粕走勢）
# ══════════════════════════════════════════════════════
futures_context = [
    ('soybean_futures_cbot_20260506', 'GLOBAL',
     1210.25, None, None, 'USD_cents/bushel',
     'CBOT大豆期貨 1210.25美分/蒲 獲利了結+農戶拋售'),
    ('brazil_soybean_harvest_rate_2026', 'GLOBAL',
     94.7, None, None, '%_harvested',
     '巴西大豆收割率94.7% StoneX預計產量1.816億噸'),
    ('us_soybean_planting_rate_20260503', 'GLOBAL',
     33.0, None, None, '%_planted',
     '美國大豆種植率33%（截至5月3日），五年均值23%，偏快'),
    ('china_soybean_arrival_may2026', 'CN_all',
     1.0, None, None, 'high_arrival_flag',
     '5月起國內大豆大量到港，供強需弱，現貨基差承壓'),
    ('soybean_meal_outlook_2026q2', 'CN_all',
     -1.0, None, None, 'bearish_signal',
     '下游養殖端持續虧損，供強需弱，豆粕現貨價格承壓'),
]
for kid, reg, val, vmin, vmax, unit, note in futures_context:
    ins(kid, reg, val, vmin, vmax, unit, note)

# ══════════════════════════════════════════════════════
# 5. 更新飼料成本計算基準
# ══════════════════════════════════════════════════════
# 東北配合飼料成本（玉米2220 + 豆粕2980）
corn_ne   = 2220  # 元/噸
soy_ne    = 2980  # 元/噸
other     = 2800  # 其他原料估算
feed_cost_ne = (corn_ne*0.60 + soy_ne*0.20 + other*0.20) / 1000  # 元/kg

ins('feed_compound_cost_northeast_20260507', 'CN_northeast',
    round(feed_cost_ne, 3), None, None, 'CNY/kg',
    f'東北配合飼料成本 玉米60%×{corn_ne}+豆粕20%×{soy_ne}+其他20%×{other} = {feed_cost_ne:.3f}元/kg')

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
feed  = conn.execute(
    "SELECT COUNT(*) FROM market_kpi WHERE species='feed_ingredient'"
).fetchone()[0]
conn.close()

print(f'Done. Inserted: {n}')
print(f'DB total: {total} | feed_ingredient: {feed}')
print()
print('=== 東北飼料成本更新 ===')
print(f'玉米（東北）: 2,220 元/噸 = 2.220 元/kg')
print(f'豆粕43%（東北）: 2,980 元/噸 = 2.980 元/kg')
print(f'配合飼料成本: {feed_cost_ne:.3f} 元/kg')
print()
print('=== 豆粕走勢：偏空 ===')
print('• 5月大豆大量到港 → 供給增加')
print('• 養殖端持續虧損 → 需求疲弱')
print('• 基差承壓 → 豆粕短期難漲')
print('• 對配方師話術：現在豆粕不漲，FCR改善節省的是真實成本')
