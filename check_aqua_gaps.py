import sqlite3
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')

# 檢查所有水產species的價格覆蓋狀況
aqua_species = [
    'shrimp', 'tilapia', 'grass_carp', 'crucian_carp', 'carp',
    'largemouth_bass', 'mandarin_fish', 'yellow_catfish', 'channel_catfish',
    'silver_carp', 'bighead_carp', 'snakehead', 'eel', 'loach',
    'grouper', 'large_yellow_croaker', 'seabass', 'black_porgy'
]

print('=== 水產價格覆蓋狀況 ===')
for sp in aqua_species:
    price = conn.execute("""
        SELECT value, unit, region, year FROM market_kpi
        WHERE species=? AND kpi_id LIKE '%spot_price%'
        ORDER BY year DESC, credibility DESC LIMIT 1
    """, (sp,)).fetchone()
    fcr = conn.execute("""
        SELECT value FROM market_kpi
        WHERE species=? AND kpi_id LIKE '%fcr%'
        AND value BETWEEN 0.8 AND 5.0
        ORDER BY year DESC LIMIT 1
    """, (sp,)).fetchone()
    survival = conn.execute("""
        SELECT value FROM market_kpi
        WHERE species=? AND kpi_id LIKE '%surviv%'
        ORDER BY year DESC LIMIT 1
    """, (sp,)).fetchone()
    
    price_str = f"{price[0]}{price[1]}({price[2]})" if price else "❌缺價格"
    fcr_str = f"FCR={fcr[0]}" if fcr else "❌缺FCR"
    surv_str = f"存活率={survival[0]}%" if survival else "❌缺存活率"
    print(f"{sp:25} | {price_str:25} | {fcr_str:12} | {surv_str}")

conn.close()
