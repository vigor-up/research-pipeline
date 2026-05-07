import sqlite3
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
deletions = []

rows = conn.execute("SELECT id FROM market_kpi WHERE species='dairy_cow' AND kpi_id LIKE '%fcr%'").fetchall()
deletions += [r[0] for r in rows]

rows = conn.execute("SELECT id FROM market_kpi WHERE species='finisher_pig' AND kpi_id LIKE '%spot_price%' AND (value < 5 OR value > 25) AND kpi_id NOT LIKE '%piglet%' AND kpi_id NOT LIKE '%carcass%'").fetchall()
deletions += [r[0] for r in rows]

rows = conn.execute("SELECT id FROM market_kpi WHERE species='meat_sheep' AND (kpi_id LIKE '%sow%' OR kpi_id LIKE '%pig%')").fetchall()
deletions += [r[0] for r in rows]

rows = conn.execute("SELECT id FROM market_kpi WHERE kpi_id LIKE '%penalty%' OR kpi_id LIKE '%prrs%'").fetchall()
deletions += [r[0] for r in rows]

for id in deletions:
    conn.execute("DELETE FROM market_kpi WHERE id=?", (id,))
conn.commit()
total = conn.execute("SELECT COUNT(*) FROM market_kpi").fetchone()[0]
print(f'刪除{len(deletions)}筆，DB總計{total}筆')
conn.close()
