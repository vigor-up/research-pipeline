import sqlite3, uuid
from datetime import datetime
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
NOW = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

data = [
    # 仔豬現貨價 2026-05-07（元/kg，10kg規格）
    ('finisher_pig', 'spot_price_piglet_10kg_northeast', 28.0, 'CNY/kg', 'CN_northeast', 5, '東北10kg仔豬均價28元/kg（黑龍江巴彦28、吉林長嶺30、遼寧黑山20）2026-05-07'),
    ('finisher_pig', 'spot_price_piglet_10kg_cn_all', 26.0, 'CNY/kg', 'CN_all', 5, '全國10kg仔豬均值26元/kg（四川26、江蘇28、河北25-28）2026-05-07'),
    ('finisher_pig', 'spot_price_piglet_10kg_cn_all_yuan', 260, 'CNY/head', 'CN_all', 5, '10kg仔豬均值260元/頭（26元/kg×10kg）2026-05-07'),
    # 仔豬成本（頭均，用於完全成本計算）
    ('finisher_pig', 'piglet_cost_per_head_low', 260, 'CNY/head', 'CN_all', 5, '仔豬成本低位260元/頭（10kg×26元/kg）2026-05-07'),
    ('finisher_pig', 'piglet_cost_per_head_mid', 300, 'CNY/head', 'CN_all', 5, '仔豬成本均值300元/頭（Q1官方數據）2026'),
    ('finisher_pig', 'piglet_cost_per_head_high', 460, 'CNY/head', 'CN_all', 5, '仔豬成本高位460元/頭（Q4外購，吉林30元/kg×15kg）2025Q4'),
    # 東北仔豬具體價格
    ('finisher_pig', 'spot_price_piglet_jilin', 30.0, 'CNY/kg', 'CN_northeast', 5, '吉林長嶺10kg仔豬30元/kg=300元/頭 2026-05-07'),
    ('finisher_pig', 'spot_price_piglet_heilongjiang', 28.0, 'CNY/kg', 'CN_northeast', 5, '黑龍江巴彦10kg仔豬28元/kg=280元/頭 2026-05-07'),
    ('finisher_pig', 'spot_price_piglet_liaoning', 20.0, 'CNY/kg', 'CN_northeast', 5, '遼寧黑山10kg仔豬20元/kg=200元/頭 2026-05-07'),
    ('finisher_pig', 'spot_price_piglet_northeast_avg', 26.0, 'CNY/kg', 'CN_northeast', 5, '東北10kg仔豬均值26元/kg=260元/頭 2026-05-07'),
]

n = 0
for species, kpi_id, value, unit, region, cred, raw in data:
    exists = conn.execute("SELECT id FROM market_kpi WHERE kpi_id=?", (kpi_id,)).fetchone()
    if not exists:
        conn.execute("""INSERT INTO market_kpi
            (id,region,country,species,production_stage,kpi_id,
             value,unit,year,credibility,source_type,
             source_url,source_title,raw_text,language,confirmed,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            str(uuid.uuid4()), region, 'CN', species, 'production',
            kpi_id, value, unit, 2026, cred, 'industry_media',
            '', '2026-05-07全國仔豬價格行情', raw, 'zh-CN', 1, NOW))
        n += 1

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
print(f'新增{n}筆，DB總計{total}筆')
conn.close()
