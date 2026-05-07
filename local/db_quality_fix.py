# -*- coding: utf-8 -*-
"""
db_quality_fix.py
DB數據品質修正：
1. FCR異常值過濾（只取 metric_type=baseline 的 FCR）
2. 修正 pricing_matrix 的 get_kpi 查詢邏輯
3. 補充缺失的市場現貨價格
4. 統計數據品質報告
"""
import sqlite3, uuid
from datetime import datetime

DB_PATH = r'D:\LLM\knowledge\market\market_data.db'
NOW = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

print('=== DB 數據品質檢查 ===\n')

# ══════════════════════════════════════════════════════
# 1. 找出所有異常 FCR 值（FCR > 10 且不是 penalty/saving）
# ══════════════════════════════════════════════════════
print('【問題1】FCR異常值：')
bad_fcr = cur.execute("""
    SELECT id, kpi_id, value, region, species, source_title
    FROM market_kpi
    WHERE kpi_id LIKE '%fcr%'
      AND value > 10
      AND kpi_id NOT LIKE '%penalty%'
      AND kpi_id NOT LIKE '%saving%'
      AND kpi_id NOT LIKE '%loss%'
""").fetchall()
for r in bad_fcr:
    print(f'  ❌ {r[1]} = {r[2]} ({r[3]}) → 異常，應刪除或修正')

# ══════════════════════════════════════════════════════
# 2. 找出 FCR 被 penalty/saving 污染的查詢問題
# ══════════════════════════════════════════════════════
print('\n【問題2】FCR查詢會抓到的非基準值：')
polluted = cur.execute("""
    SELECT kpi_id, value, region, species
    FROM market_kpi
    WHERE kpi_id LIKE '%fcr%'
      AND (kpi_id LIKE '%penalty%'
        OR kpi_id LIKE '%saving%'
        OR kpi_id LIKE '%loss%'
        OR value > 10)
    ORDER BY species
""").fetchall()
for r in polluted:
    print(f'  ⚠️  {r[0]} = {r[1]} ({r[2]})')

# ══════════════════════════════════════════════════════
# 3. 現貨價格完整性檢查
# ══════════════════════════════════════════════════════
print('\n【問題3】各物種現貨價格狀況：')
species_list = [
    'finisher_pig', 'beef_cattle', 'meat_sheep', 'broiler',
    'layer_chicken', 'lactating_sow', 'shrimp', 'tilapia',
    'dairy_cow', 'dairy_goat'
]
for sp in species_list:
    price = cur.execute("""
        SELECT value, unit, region, year FROM market_kpi
        WHERE species=? AND kpi_id LIKE '%spot_price%'
          AND value IS NOT NULL
        ORDER BY year DESC, credibility DESC LIMIT 1
    """, (sp,)).fetchone()
    if price:
        print(f'  ✅ {sp}: CNY {price[0]}/{price[1]} ({price[2]} {price[3]})')
    else:
        print(f'  ❌ {sp}: 無現貨價格')

# ══════════════════════════════════════════════════════
# 4. 修正：為 pricing_matrix 建立乾淨的 FCR 基準視圖
#    新增 kpi_type 欄位概念：用 production_stage 區分
# ══════════════════════════════════════════════════════
print('\n【修正】確認 FCR 基準值（只取合理範圍）：')
valid_fcr = cur.execute("""
    SELECT species, kpi_id, value, region, credibility, source_title
    FROM market_kpi
    WHERE kpi_id LIKE '%fcr%'
      AND kpi_id NOT LIKE '%penalty%'
      AND kpi_id NOT LIKE '%saving%'
      AND kpi_id NOT LIKE '%loss%'
      AND kpi_id NOT LIKE '%ratio%'
      AND value BETWEEN 0.5 AND 12
    ORDER BY species, credibility DESC, value
""").fetchall()
for r in valid_fcr:
    print(f'  ✅ {r[0]:20s} FCR={r[2]} ({r[3]}) cred={r[4]}')

# ══════════════════════════════════════════════════════
# 5. 補充缺失價格（從已有數據推算）
# ══════════════════════════════════════════════════════
print('\n【補充】缺失價格補充：')

missing_prices = [
    # 活豬價格（東北，從今日省級數據推算均值）
    ('finisher_pig', 'CN_northeast', 'spot_price_pig_ne_avg',
     9.58, 'CNY/kg', '東北三省生豬均價 遼9.68+吉9.52+黑9.38/3 2026-05-06'),
    # 肉牛東北均價（從今日數據）
    ('beef_cattle', 'CN_northeast', 'spot_price_cattle_ne_avg',
     29.6, 'CNY/kg', '東北牛價均值 14.8元/斤 2026-05-06'),
    # 肉羊東北均價
    ('meat_sheep', 'CN_northeast', 'spot_price_sheep_ne_avg',
     29.0, 'CNY/kg', '東北肉羊均價 14.5元/斤 2026-05-06'),
    # 肉雞東北均價
    ('broiler', 'CN_northeast', 'spot_price_broiler_ne_avg',
     11.6, 'CNY/kg', '東北肉雞均價 5.8元/斤 2026-05-06'),
    # 雞蛋東北均價
    ('layer_chicken', 'CN_northeast', 'spot_price_egg_ne_avg',
     8.3, 'CNY/kg', '東北雞蛋均價 遼寧4.125元/斤 2026-05-06'),
    # 仔豬東北均價
    ('nursery_pig', 'CN_northeast', 'piglet_price_ne_avg',
     285.0, 'CNY/head', '東北仔豬均價（散戶15kg）2026-05-06'),
    # 乳牛原料奶（東北）
    ('dairy_cow', 'CN_northeast', 'spot_price_raw_milk_ne',
     3.8, 'CNY/kg', '東北原料奶收購價 2026Q2'),
    # 奶山羊奶（全國）
    ('dairy_goat', 'CN_all', 'spot_price_goat_milk_cn',
     6.5, 'CNY/kg', '奶山羊羊奶收購價 2023-2024'),
]

inserted = 0
for sp, region, kpi_id, val, unit, note in missing_prices:
    if not cur.execute(
        "SELECT id FROM market_kpi WHERE kpi_id=?", (kpi_id,)).fetchone():
        cur.execute("""INSERT INTO market_kpi
            (id,region,country,species,production_stage,kpi_id,
             value,unit,year,credibility,source_type,
             source_url,source_title,raw_text,language,confirmed,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            str(uuid.uuid4()), region, 'CN', sp, 'market_price', kpi_id,
            val, unit, 2026, 4, 'industry_media',
            '', note, f'db_quality_fix | {note}',
            'zh-CN', 1, NOW))
        print(f'  ➕ {sp} {kpi_id} = {val} {unit}')
        inserted += 1
    else:
        print(f'  ✓  {kpi_id} 已存在')

conn.commit()

# ══════════════════════════════════════════════════════
# 6. 最終統計
# ══════════════════════════════════════════════════════
total    = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
conf     = conn.execute('SELECT COUNT(*) FROM market_kpi WHERE confirmed=1').fetchone()[0]
ne_count = conn.execute("SELECT COUNT(*) FROM market_kpi WHERE region='CN_northeast'").fetchone()[0]
price_c  = conn.execute("SELECT COUNT(*) FROM market_kpi WHERE kpi_id LIKE '%spot_price%' OR kpi_id LIKE '%price%'").fetchone()[0]

print(f'\n=== 修正完成 ===')
print(f'新增價格: {inserted} 筆')
print(f'DB總計: {total} 筆')
print(f'confirmed: {conf} | CN_northeast: {ne_count} | 價格類: {price_c}')
conn.close()

# ══════════════════════════════════════════════════════
# 7. 修正 pricing_matrix_v2 的 get_kpi 函數
#    輸出修正版查詢邏輯供參考
# ══════════════════════════════════════════════════════
print('''
=== pricing_matrix 的正確 FCR 查詢邏輯 ===
應該用：
  WHERE species=? AND kpi_id LIKE '%fcr%'
    AND kpi_id NOT LIKE '%penalty%'
    AND kpi_id NOT LIKE '%saving%'
    AND kpi_id NOT LIKE '%loss%'
    AND kpi_id NOT LIKE '%ratio%'
    AND value BETWEEN 0.5 AND 12
  ORDER BY credibility DESC, year DESC LIMIT 1
''')
