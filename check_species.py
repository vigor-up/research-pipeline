import sqlite3
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
rows = conn.execute("SELECT DISTINCT species FROM market_kpi").fetchall()
for r in rows:
    print(r[0])
