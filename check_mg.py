import sqlite3
conn = sqlite3.connect('local/market_data.db')
rows = conn.execute("SELECT kpi_id, value_mid, data_quality FROM market_kpi WHERE kpi_id LIKE 'mg_%'").fetchall()
for r in rows: print(r)
print('total MG rows:', len(rows))
