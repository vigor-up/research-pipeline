# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
# -*- coding: utf-8 -*-
"""
補入 2026-05-08 現貨價格到 market_data.db
來源：微信行情截圖 + 牛肉/羊肉文字
"""
import sqlite3, uuid
from datetime import datetime

DB_PATH = r'D:\LLM\knowledge\market\market_data.db'
NOW = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
SOURCE = '微信行情截圖/市場公開資訊 2026-05-08'

records = []

def r(species, region, kpi_id, value, unit, vmin=None, vmax=None, cred=3, note=''):
    records.append({
        'id': str(uuid.uuid4()),
        'region': region, 'country': '', 'species': species,
        'production_stage': '', 'kpi_id': kpi_id,
        'value': value, 'value_min': vmin, 'value_max': vmax,
        'unit': unit, 'year': 2026, 'credibility': cred,
        'source_type': 'market_monitor',
        'source_url': '', 'source_title': SOURCE,
        'raw_text': note, 'language': 'zh',
        'confirmed': 1, 'updated_at': NOW, 'sample_count': 1,
    })

# ── 肉雞現貨價（元/斤）→ 換算元/kg ×2 ──────────────────
# 東北（遼吉黑平均）
r('broiler','CN_northeast','spot_price_broiler_ne_20260508', 7.70, 'CNY/kg', 7.50,8.10, 4,
  '遼寧3.80-3.90/大連,吉林3.75-3.85,黑龍江3.60-4.10 均值×2')
# 華北（京津冀晉蒙）
r('broiler','CN_north','spot_price_broiler_north_20260508', 7.96, 'CNY/kg', 7.86,8.40, 4,
  '北京4.20,天津3.93,河北3.93-4.18,山西4.10-4.35,內蒙古3.93-4.10 均值×2')
# 華東（蘇浙皖魯）
r('broiler','CN_east','spot_price_broiler_east_20260508', 8.80, 'CNY/kg', 7.54,10.10, 3,
  '山東3.77-4.25,江蘇4.10-4.50,浙江4.35-4.60,安徽4.10-4.50 均值×2')
# 華中（豫鄂湘贛）
r('broiler','CN_central','spot_price_broiler_central_20260508', 8.72, 'CNY/kg', 7.94,9.86, 3,
  '河南3.64-4.35,湖北4.10-4.80,湖南4.80-4.93,江西4.45-4.55')
# 華南（廣東）
r('broiler','CN_south','spot_price_broiler_south_20260508', 8.45, 'CNY/kg', 7.00,9.90, 3,
  '廣東3.50-4.95 均值×2')

# ── 生豬現貨價（元/斤×2=元/kg）────────────────────────
r('finisher_pig','CN_northeast','spot_price_pig_ne_20260508', 9.74, 'CNY/kg', 9.36,10.16, 4,
  '遼寧4.85-5.08,吉林4.75-4.95,黑龍江4.68-4.88 均值×2')
r('finisher_pig','CN_north','spot_price_pig_north_20260508', 10.26, 'CNY/kg', 9.80,10.40, 4,
  '北京/天津5.08-5.20,河北5.02-5.18,河南5.00-5.15 均值×2')
r('finisher_pig','CN_east','spot_price_pig_east_20260508', 10.44, 'CNY/kg', 9.80,10.64, 4,
  '上海5.25,山東5.15-5.32,江蘇5.10-5.28,浙江5.05-5.25,安徽5.00-5.30 均值×2')
r('finisher_pig','CN_south','spot_price_pig_south_20260508', 10.70, 'CNY/kg', 10.30,10.70, 4,
  '廣東5.25-5.35(全國最高),廣西5.15,海南5.20 均值×2')
r('finisher_pig','CN_central','spot_price_pig_central_20260508', 9.78, 'CNY/kg', 9.40,10.00, 3,
  '湖北4.80-5.00,湖南4.70-4.92,江西4.75-4.95 均值×2')
r('finisher_pig','CN_southwest','spot_price_pig_sw_20260508', 9.10, 'CNY/kg', 8.90,9.50, 3,
  '四川4.65-4.75,重慶4.55-4.65,雲南4.50-4.70,貴州4.45-4.55 均值×2')

# ── 牛肉批發價 ────────────────────────────────────────
r('beef_cattle','CN_all','wholesale_price_beef_20260508', 66.57, 'CNY/kg', None,None, 3,
  '全國牛肉平均批發價2026-05-08')
r('beef_cattle','GLOBAL','import_price_beef_brazil_20260508', 56.9, 'CNY/kg', 55.9,58.9, 3,
  '巴西草飼牛前八件套 2026-05-08')
r('beef_cattle','GLOBAL','import_price_beef_australia_20260508', 66.3, 'CNY/kg', 66.0,68.0, 3,
  '澳大利亞草飼西冷/保乐肩 2026-05-08')

# ── 羊肉出欄價 ────────────────────────────────────────
r('meat_sheep','CN_all','wholesale_price_mutton_20260508', 72.56, 'CNY/kg', None,None, 3,
  '農業農村部監測全國均價2026-04-16（最新）')
r('meat_sheep','CN_north','slaughter_price_sheep_north_20260508', 27.6, 'CNY/kg', 25.6,25.2, 3,
  '內蒙古育肥綿羊出欄13.8/kg×2=27.6,山羊16-18/kg')
r('meat_sheep','CN_southwest','slaughter_price_sheep_sw_20260508', 24.5, 'CNY/kg', 24.0,26.0, 3,
  '四川綿羊12-13/kg,山羊11-17/kg 均值×2')

conn = sqlite3.connect(DB_PATH)
inserted = 0
for rec in records:
    try:
        conn.execute("""INSERT OR IGNORE INTO market_kpi
            (id,region,country,species,production_stage,kpi_id,
             value,value_min,value_max,unit,year,credibility,
             source_type,source_url,source_title,raw_text,language,
             confirmed,updated_at,sample_count)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            rec['id'],rec['region'],rec['country'],rec['species'],
            rec['production_stage'],rec['kpi_id'],
            rec['value'],rec['value_min'],rec['value_max'],
            rec['unit'],rec['year'],rec['credibility'],
            rec['source_type'],rec['source_url'],rec['source_title'],
            rec['raw_text'],rec['language'],
            rec['confirmed'],rec['updated_at'],rec['sample_count']))
        inserted += 1
    except Exception as e:
        print(f'SKIP {rec["kpi_id"]}: {e}')
conn.commit()
print(f'插入 {inserted}/{len(records)} 筆')
print('market_kpi total:', conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0])
conn.close()
