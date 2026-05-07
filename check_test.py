import sqlite3
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
rows = conn.execute("""
    SELECT species, kpi_id, value FROM market_kpi 
    WHERE source_title='2026-05-07多物種價格測試'
    ORDER BY species
""").fetchall()
for r in rows:
    print(f"{r[0]:20} {r[2]:8} {r[1]}")
conn.close()
