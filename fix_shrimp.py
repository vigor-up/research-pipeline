import sqlite3, uuid
from datetime import datetime
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
NOW = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
conn.execute('''INSERT INTO market_kpi
    (id,region,country,species,production_stage,kpi_id,
     value,unit,year,credibility,source_type,
     source_url,source_title,raw_text,language,confirmed,updated_at)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
    str(uuid.uuid4()), 'CN_all', 'CN',
    'shrimp', 'market_price', 'spot_price_shrimp_national_avg',
    32.0, 'CNY/kg', 2026, 4, 'industry_media',
    '', '2026-05水產現貨價格', '南美白蝦全國均價32元/kg', 'zh-CN', 1, NOW))
conn.commit()
print('done')
