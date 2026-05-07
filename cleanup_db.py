import sqlite3
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
deletions = []

rows = conn.execute("SELECT id, kpi_id, value FROM market_kpi WHERE species='dairy_cow' AND kpi_id LIKE '%fcr%'").fetchall()
for r in rows:
    print(f"dairy_cow FCR: {r[1]}={r[2]}")
    deletions.append(r[0])

rows = conn.execute("SELECT id, kpi_id, value FROM market_kpi WHERE species='finisher_pig' AND kpi_id LIKE '%spot_price%' AND (value < 5 OR value > 25) AND kpi_id NOT LIKE '%piglet%' AND kpi_id NOT LIKE '%carcass%'").fetchall()
for r in rows:
    print(f"pig異常價: {r[1]}={r[2]}")
    deletions.append(r[0])

rows = conn.execute("SELECT id, kpi_id, value FROM market_kpi WHERE species='meat_sheep' AND (kpi_id LIKE '%sow%' OR kpi_id LIKE '%pig%')").fetchall()
for r in rows:
    print(f"sheep污染: {r[1]}={r[2]}")
    deletions.append(r[0])

rows = conn.execute("SELECT id, kpi_id FROM market_kpi WHERE kpi_id LIKE '%penalty%' OR kpi_id LIKE '%prrs%'").fetchall()
for r in rows:
    print(f"PRRS: {r[1]}")
    deletions.append(r[0])

print(f'待刪: {len(deletions)}筆')
conn.close()
