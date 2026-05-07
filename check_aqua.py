import sqlite3
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
rows = conn.execute("SELECT kpi_id, value, unit, region FROM market_kpi WHERE species IN ('shrimp','tilapia') ORDER BY year DESC LIMIT 10").fetchall()
for r in rows:
    print(r)
