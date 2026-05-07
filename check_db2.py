import sqlite3
conn = sqlite3.connect(r"D:\LLM\knowledge\market\market_data.db")
total = conn.execute("SELECT COUNT(*) FROM market_kpi").fetchone()[0]
by_species = conn.execute("SELECT species, COUNT(*) FROM market_kpi GROUP BY species ORDER BY COUNT(*) DESC").fetchall()
print(f"Total rows: {total}")
for row in by_species: print(f"  {row[0]}: {row[1]}")
