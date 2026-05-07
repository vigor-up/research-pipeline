import sqlite3
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
soy = conn.execute("SELECT value FROM market_kpi WHERE kpi_id LIKE '%soybean_meal%' AND (region='CN_northeast' OR region='CN_all') ORDER BY year DESC LIMIT 1").fetchone()
corn = conn.execute("SELECT value FROM market_kpi WHERE kpi_id LIKE '%corn%' AND (region='CN_northeast' OR region='CN_all') ORDER BY year DESC LIMIT 1").fetchone()
print('soy:', soy)
print('corn:', corn)
print('feed_cost:', round((corn[0]*0.60 + soy[0]*0.20 + 2800*0.20)/1000, 3) if soy and corn else 'N/A')
conn.close()
