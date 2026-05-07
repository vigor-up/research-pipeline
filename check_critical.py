import sqlite3
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')

# 最影響ROI的關鍵指標詳細查看
critical = ['FCR', 'ADG', 'fcr_baseline_northeast_2026', 'milk_yield_dairy_cow_cn_all']
for kpi in critical:
    print(f'\n=== {kpi} ===')
    rows = conn.execute("""
        SELECT species, kpi_id, value, unit, credibility, source_title
        FROM market_kpi WHERE kpi_id=? OR kpi_id LIKE ?
        ORDER BY species, credibility DESC
    """, (kpi, f'%{kpi}%')).fetchall()
    for r in rows:
        print(f"  {r[0]:20} val={r[2]:10} unit={r[3]:15} cred={r[4]} | {r[5][:35]}")

conn.close()
