import sqlite3
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')

print('=== FCR異常檢查 ===')
rows = conn.execute("""
    SELECT species, kpi_id, value, source_title FROM market_kpi 
    WHERE kpi_id LIKE '%fcr%' 
    AND (value > 15 OR value < 0.5)
    ORDER BY species
""").fetchall()
for r in rows:
    print(f"異常: {r}")

print('\n=== 主力物種FCR確認 ===')
species_list = ['finisher_pig','beef_cattle','meat_sheep','broiler','layer_chicken','duck','breeding_sow','dairy_cow']
for sp in species_list:
    r = conn.execute("""
        SELECT value, kpi_id, credibility FROM market_kpi 
        WHERE species=? AND kpi_id LIKE '%fcr%' 
        AND value BETWEEN 0.5 AND 15
        ORDER BY credibility DESC, year DESC LIMIT 1
    """, (sp,)).fetchone()
    print(f"{sp:20} FCR={r[0] if r else '❌缺'}")

print('\n=== 價格異常檢查 ===')
price_checks = [
    ('finisher_pig', 8, 20),
    ('beef_cattle', 20, 45),
    ('meat_sheep', 20, 45),
    ('broiler', 5, 15),
    ('layer_chicken', 5, 15),
    ('duck', 4, 12),
    ('dairy_cow', 2, 5),
]
for sp, low, high in price_checks:
    r = conn.execute("""
        SELECT value, kpi_id FROM market_kpi
        WHERE species=? AND kpi_id LIKE '%spot_price%'
        AND (value < ? OR value > ?)
    """, (sp, low, high)).fetchall()
    if r:
        for row in r:
            print(f"價格異常 {sp}: {row}")

print('\n=== WTP相關數值確認 ===')
for sp in ['finisher_pig','beef_cattle','meat_sheep','broiler','layer_chicken']:
    price = conn.execute("SELECT value FROM market_kpi WHERE species=? AND kpi_id LIKE '%spot_price%' ORDER BY year DESC,credibility DESC LIMIT 1",(sp,)).fetchone()
    fcr = conn.execute("SELECT value FROM market_kpi WHERE species=? AND kpi_id LIKE '%fcr%' AND value BETWEEN 0.5 AND 15 ORDER BY credibility DESC LIMIT 1",(sp,)).fetchone()
    feed = conn.execute("SELECT value FROM market_kpi WHERE species=? AND (kpi_id LIKE '%feed_cost%' OR kpi_id LIKE '%feed_price%') AND unit LIKE '%ton%' ORDER BY credibility DESC LIMIT 1",(sp,)).fetchone()
    print(f"{sp:20} 價格={price[0] if price else '❌'} FCR={fcr[0] if fcr else '❌'} 飼料={feed[0] if feed else '❌'}元/噸")

conn.close()
