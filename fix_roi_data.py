import sqlite3
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')

# 1. 刪除PRRS懲罰值和錯誤分類數據
delete_kpis = [
    'prrs_fcr_penalty_finisher_pig_cn_all',
    'prrs_fcr_penalty_finisher_pig_cn_northeast',
    'pig_fcr_saving_value_per_head',
    'fcr_broiler_activity_correlation',
    'mg_lcfa_fcr_improvement',
]
for kpi in delete_kpis:
    n = conn.execute("DELETE FROM market_kpi WHERE kpi_id=?", (kpi,)).rowcount
    print(f"DELETE {kpi}: {n}筆")

# 2. 刪除species錯誤的數據（肉羊裡的母豬價格）
wrong_sheep = conn.execute("""
    DELETE FROM market_kpi WHERE species='meat_sheep' 
    AND (kpi_id LIKE '%母豬%' OR kpi_id LIKE '%sow%' OR kpi_id LIKE '%piglet%'
    OR value > 500)
""").rowcount
print(f"刪除meat_sheep錯誤分類: {wrong_sheep}筆")

# 3. 刪除finisher_pig裡的其他物種價格
wrong_pig = conn.execute("""
    DELETE FROM market_kpi WHERE species='finisher_pig'
    AND (kpi_id LIKE '%肉雞%' OR kpi_id LIKE '%肉鴨%' OR kpi_id LIKE '%奶牛%'
    OR kpi_id LIKE '%layer%' OR kpi_id LIKE '%duck%' OR kpi_id LIKE '%dairy%'
    OR kpi_id LIKE '%全價料%' OR kpi_id LIKE '%carcass%')
""").rowcount
print(f"刪除finisher_pig錯誤分類: {wrong_pig}筆")

# 4. 更新正確FCR基準值
from datetime import datetime
NOW = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
import uuid

fcr_correct = [
    ('finisher_pig', 'fcr_baseline_northeast_2026', 2.75, '育肥豬東北FCR基準2.75（80-160kg）2026Q1山東官方'),
    ('beef_cattle',  'fcr_baseline_northeast_2026', 7.2,  '肉牛東北FCR基準7.2（育肥期）東北肉牛育肥技術規範'),
    ('meat_sheep',   'fcr_baseline_northeast_2026', 5.8,  '肉羊東北FCR基準5.8（育肥90天）2026實測'),
    ('broiler',      'fcr_baseline_northeast_2026', 1.85, '肉雞東北FCR基準1.85（40-42天）2026Q1山東官方'),
    ('layer_chicken','fcr_baseline_northeast_2026', 2.2,  '蛋雞FCR基準2.2（產蛋期）2026Q1山東官方'),
    ('duck',         'fcr_baseline_northeast_2026', 2.1,  '肉鴨FCR基準2.1（大鴨36-37天）2026Q1'),
]

for species, kpi_id, value, raw in fcr_correct:
    exists = conn.execute("SELECT id FROM market_kpi WHERE kpi_id=? AND species=?", (kpi_id, species)).fetchone()
    if exists:
        conn.execute("UPDATE market_kpi SET value=?, updated_at=? WHERE kpi_id=? AND species=?",
                    (value, NOW, kpi_id, species))
        print(f"UPDATE {species} FCR={value}")
    else:
        conn.execute("""INSERT INTO market_kpi
            (id,region,country,species,production_stage,kpi_id,
             value,unit,year,credibility,source_type,
             source_url,source_title,raw_text,language,confirmed,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            str(uuid.uuid4()), 'CN_northeast', 'CN', species, 'production',
            kpi_id, value, 'kg/kg', 2026, 5, 'industry_media',
            '', '2026東北主力物種FCR基準修正版', raw, 'zh-CN', 1, NOW))
        print(f"INSERT {species} FCR={value}")

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
print(f'\nDB總計: {total}筆')
conn.close()
