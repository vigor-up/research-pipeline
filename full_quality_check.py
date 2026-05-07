import sqlite3
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')

print('='*60)
print('數據品質全面排查報告')
print('='*60)

# 1. 各物種數據量分布
print('\n【1. 各物種數據量】')
rows = conn.execute("""
    SELECT species, COUNT(*) as cnt, 
    SUM(CASE WHEN confirmed=1 THEN 1 ELSE 0 END) as confirmed
    FROM market_kpi GROUP BY species ORDER BY cnt DESC
""").fetchall()
for r in rows:
    flag = '⚠️' if r[1] > 50 else '✅'
    print(f"{flag} {r[0]:30} 總計:{r[1]:4d} 確認:{r[2]:4d}")

# 2. 跨物種污染檢查（kpi_id包含其他物種名稱）
print('\n【2. 跨物種污染檢查】')
contamination_patterns = [
    ('finisher_pig', ['雞','鴨','牛','羊','蝦','魚','奶','母豬','layer','broiler','cattle','sheep','duck','dairy','sow']),
    ('beef_cattle',  ['豬','雞','蝦','魚','layer','broiler','pig','sheep','duck','dairy']),
    ('meat_sheep',   ['豬','雞','鴨','蝦','魚','牛','奶','layer','broiler','pig','cattle','duck','dairy']),
    ('broiler',      ['豬','鴨','牛','羊','蝦','魚','奶','pig','cattle','sheep','duck','dairy','sow']),
    ('layer_chicken',['豬','鴨','牛','羊','蝦','魚','奶','pig','cattle','sheep','duck','dairy','sow']),
    ('duck',         ['豬','雞','牛','羊','蝦','魚','奶','pig','cattle','sheep','layer','broiler','dairy']),
]
total_contaminated = 0
for species, patterns in contamination_patterns:
    for pat in patterns:
        rows = conn.execute("""
            SELECT kpi_id, value FROM market_kpi 
            WHERE species=? AND kpi_id LIKE ?
        """, (species, f'%{pat}%')).fetchall()
        for r in rows:
            print(f"❌ {species}: {r[0]} = {r[1]}")
            total_contaminated += 1
print(f"污染總計: {total_contaminated}筆")

# 3. 數值範圍異常檢查
print('\n【3. 數值範圍異常】')
range_checks = [
    ('spot_price%', 'finisher_pig',  0.1,  25,  '元/kg活豬'),
    ('spot_price%', 'beef_cattle',   15,   50,  '元/kg活牛'),
    ('spot_price%', 'meat_sheep',    15,   50,  '元/kg活羊'),
    ('spot_price%', 'broiler',        5,   20,  '元/kg毛雞'),
    ('spot_price%', 'layer_chicken',  5,   15,  '元/kg雞蛋'),
    ('spot_price%', 'duck',           4,   12,  '元/kg毛鴨'),
    ('spot_price%', 'dairy_cow',      2,    5,  '元/kg生乳'),
    ('%fcr%',       'finisher_pig',   1.5,  4,  'FCR育肥豬'),
    ('%fcr%',       'beef_cattle',    4,   12,  'FCR肉牛'),
    ('%fcr%',       'meat_sheep',     3,    9,  'FCR肉羊'),
    ('%fcr%',       'broiler',        1,    3,  'FCR肉雞'),
    ('%fcr%',       'layer_chicken',  1.5,  4,  'FCR蛋雞'),
    ('%fcr%',       'duck',           1.5,  4,  'FCR肉鴨'),
    ('%fcr%',       'dairy_cow',      1,    3,  'FCR奶牛（實為產乳）'),
]
total_range_err = 0
for kpi_pat, species, low, high, label in range_checks:
    rows = conn.execute("""
        SELECT kpi_id, value, source_title FROM market_kpi
        WHERE species=? AND kpi_id LIKE ? AND (value < ? OR value > ?)
    """, (species, kpi_pat, low, high)).fetchall()
    for r in rows:
        print(f"⚠️ {label} {species}: {r[0]}={r[1]} 來源:{r[2][:30]}")
        total_range_err += 1
print(f"範圍異常總計: {total_range_err}筆")

# 4. 低可信度數據
print('\n【4. 可信度<=2的數據（高風險）】')
rows = conn.execute("""
    SELECT species, kpi_id, value, credibility, source_title 
    FROM market_kpi WHERE credibility <= 2
    ORDER BY credibility, species
""").fetchall()
for r in rows:
    print(f"⚠️ cred={r[3]} {r[0]}: {r[1]}={r[2]} | {r[4][:40]}")
print(f"低可信度總計: {len(rows)}筆")

# 5. kpi_id重複檢查
print('\n【5. kpi_id重複（同一指標多個值）】')
rows = conn.execute("""
    SELECT kpi_id, COUNT(*) as cnt, MIN(value), MAX(value)
    FROM market_kpi 
    GROUP BY kpi_id HAVING cnt > 1
    ORDER BY cnt DESC LIMIT 20
""").fetchall()
for r in rows:
    diff = r[3] - r[2]
    flag = '❌' if diff > r[2]*0.2 else '✅'
    print(f"{flag} {r[0]}: {r[1]}筆, 值域{r[2]:.1f}~{r[3]:.1f} 差異{diff:.1f}")

conn.close()
