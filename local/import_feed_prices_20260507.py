# -*- coding: utf-8 -*-
"""
import_feed_prices_20260507.py
2026-05-07 玉米現貨價格（省級）
來源：中國飼料行業信息網 feedtrade.com.cn
"""
import sqlite3, uuid
from datetime import datetime

DB_PATH = r'D:\LLM\knowledge\market\market_data.db'
NOW  = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
YEAR = 2026
SOURCE_URL   = 'https://m.feedtrade.com.cn/index/index'
SOURCE_TITLE = '中國飼料行業信息網 2026-05-07 玉米現貨價格'

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
n = 0

def ins(kpi_id, region, value_mid, value_min, value_max, note):
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
        'feed_ingredient', 'spot_price',
        kpi_id, value_mid, value_min, value_max,
        'CNY/ton', YEAR, 4, 'industry_media',
        SOURCE_URL, SOURCE_TITLE,
        note, 'zh-CN', 1, NOW))
    n += 1

# ══════════════════════════════════════════════════════
# 東北（對東北出差最重要）
# ══════════════════════════════════════════════════════
# 黑龍江
ins('corn_purchase_price_heilongjiang',   'CN_northeast', 2200, 2190, 2210,
    '黑龍江哈爾濱/佳木斯 水分15% 收購價 2190-2210元/噸')
ins('corn_ex_price_heilongjiang',         'CN_northeast', 2240, 2230, 2250,
    '黑龍江出庫價 2230-2250元/噸')
ins('corn_purchase_price_qiqihar',        'CN_northeast', 2140, 2130, 2150,
    '齊齊哈爾/青岡 收購價 2130-2150元/噸')

# 吉林
ins('corn_purchase_price_jilin_changchun','CN_northeast', 2230, 2220, 2240,
    '吉林長春/德惠 收購價 2220-2240元/噸')
ins('corn_ex_price_jilin_changchun',      'CN_northeast', 2310, 2300, 2320,
    '吉林長春出庫價 2300-2320元/噸')
ins('corn_purchase_price_jilin_west',     'CN_northeast', 2230, 2210, 2250,
    '吉林鎮賚/松原 收購價 2210-2250元/噸')

# 遼寧
ins('corn_purchase_price_liaoning',       'CN_northeast', 2280, 2270, 2290,
    '遼寧瀋陽/鐵嶺 收購價 2270-2290元/噸')
ins('corn_ex_price_liaoning',             'CN_northeast', 2350, 2340, 2360,
    '遼寧出庫價 2340-2360元/噸')

# 東北均價（飼料成本計算用）
ins('corn_spot_price_northeast_avg',      'CN_northeast', 2220, 2190, 2290,
    '東北玉米現貨均價 2026-05-07 加權估算')

# ══════════════════════════════════════════════════════
# 華北
# ══════════════════════════════════════════════════════
ins('corn_purchase_price_shandong',       'CN_north',     2430, 2370, 2484,
    '山東深加工企業收購均價 2370-2484元/噸')
ins('corn_purchase_price_hebei',          'CN_north',     2370, 2360, 2380,
    '河北收購價 2360-2380元/噸')
ins('corn_purchase_price_henan',          'CN_central',   2390, 2380, 2400,
    '河南收購價 2380-2400元/噸')

# ══════════════════════════════════════════════════════
# 南方
# ══════════════════════════════════════════════════════
ins('corn_spot_price_guangdong_port',     'CN_south',     2505, 2500, 2510,
    '廣東蛇口港 水分15% 散糧成交價 2500-2510元/噸')
ins('corn_spot_price_guangdong_grade1',   'CN_south',     2535, 2530, 2540,
    '廣東蛇口港 一級玉米 2530-2540元/噸')
ins('corn_purchase_price_jiangsu_zhejiang','CN_east',     2365, 2350, 2380,
    '江蘇浙江收購價 2350-2380元/噸')

# ══════════════════════════════════════════════════════
# 全國均價（ROI計算基準）
# ══════════════════════════════════════════════════════
ins('corn_spot_price_national_avg',       'CN_all',       2320, 2190, 2540,
    '全國玉米現貨均價估算 2026-05-07 東北低南方高')

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
feed  = conn.execute(
    "SELECT COUNT(*) FROM market_kpi WHERE species='feed_ingredient'"
).fetchone()[0]
ne_corn = conn.execute(
    "SELECT AVG(value) FROM market_kpi "
    "WHERE kpi_id LIKE '%corn%purchase%' AND region='CN_northeast'"
).fetchone()[0]
conn.close()

print(f'Done. Inserted: {n}')
print(f'DB total: {total} | feed_ingredient: {feed}')
print(f'東北玉米收購均價: CNY {ne_corn:.0f}/噸' if ne_corn else '無東北均價')
print()
print('=== 飼料成本更新 ===')
print(f'東北玉米: ~2220元/噸 = 2.22元/kg')
print(f'東北豆粕: ~3200元/噸 = 3.20元/kg（待補充今日價）')
print(f'東北配合飼料成本: {2220*0.60 + 3200*0.20 + 2800*0.20:.0f}元/噸 = {(2220*0.60 + 3200*0.20 + 2800*0.20)/1000:.3f}元/kg')
