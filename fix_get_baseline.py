lines = open('local/formula_advisor.py', encoding='utf-8').readlines()

old = '''def get_baseline(conn, species, kpi, region='CN_northeast'):
    row = conn.execute("""
        SELECT value, value_min, value_max, unit, source_title
        FROM market_kpi
        WHERE species=? AND kpi_id LIKE ? AND region=?
          AND value IS NOT NULL
        ORDER BY credibility DESC, year DESC LIMIT 1
    """, (species, f'%{kpi}%', region)).fetchone()
    if not row:
        row = conn.execute("""
            SELECT value, value_min, value_max, unit, source_title
            FROM market_kpi
            WHERE species=? AND kpi_id LIKE ?
              AND value IS NOT NULL
            ORDER BY credibility DESC, year DESC LIMIT 1
        """, (species, f'%{kpi}%')).fetchone()
    return row'''

new = '''def get_baseline(conn, species, kpi, region='CN_northeast'):
    # 優先查手動核准的基準值（fcr_baseline_northeast_2026）
    if kpi == 'fcr':
        row = conn.execute("""
            SELECT value, NULL, NULL, unit, source_title
            FROM market_kpi
            WHERE species=? AND kpi_id='fcr_baseline_northeast_2026'
            ORDER BY credibility DESC LIMIT 1
        """, (species,)).fetchone()
        if row:
            return row
    # FCR需限制合理範圍，避免抓到懲罰值/相關係數
    if kpi == 'fcr':
        val_filter = "AND value BETWEEN 0.8 AND 12"
        extra = "AND kpi_id NOT LIKE '%penalty%' AND kpi_id NOT LIKE '%saving%' AND kpi_id NOT LIKE '%correlation%' AND kpi_id NOT LIKE '%improvement%'"
    elif kpi == 'adg':
        val_filter = "AND value BETWEEN 0.01 AND 500"
        extra = "AND unit IN ('g/day','kg/day','g/d') OR unit IS NULL"
        extra = "AND kpi_id NOT LIKE '%penalty%' AND kpi_id NOT LIKE '%pct%'"
    else:
        val_filter = "AND value IS NOT NULL"
        extra = ""
    row = conn.execute(f"""
        SELECT value, NULL, NULL, unit, source_title
        FROM market_kpi
        WHERE species=? AND kpi_id LIKE ? AND region=?
          {val_filter} {extra}
        ORDER BY credibility DESC, year DESC LIMIT 1
    """, (species, f'%{kpi}%', region)).fetchone()
    if not row:
        row = conn.execute(f"""
            SELECT value, NULL, NULL, unit, source_title
            FROM market_kpi
            WHERE species=? AND kpi_id LIKE ?
              {val_filter} {extra}
            ORDER BY credibility DESC, year DESC LIMIT 1
        """, (species, f'%{kpi}%')).fetchone()
    return row'''

content = open('local/formula_advisor.py', encoding='utf-8').read()
if old in content:
    content = content.replace(old, new)
    open('local/formula_advisor.py', 'w', encoding='utf-8').write(content)
    print('done')
else:
    print('ERROR: old string not found')
