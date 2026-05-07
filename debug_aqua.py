import sqlite3
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
for sp in ['shrimp','tilapia']:
    r = conn.execute("""
        SELECT kpi_id, value, region FROM market_kpi
        WHERE species=? AND kpi_id LIKE '%spot_price%'
        AND (region='CN_south' OR region='CN_all')
        ORDER BY year DESC, credibility DESC LIMIT 1
    """, (sp,)).fetchone()
    print(sp, r)
