# -*- coding: utf-8 -*-
"""
import_pig_market_report_20260506.py
來源：全國豬業行業信息報告 2026-05-06
寫入：market_kpi（價格/週期/比價/產能）+ competitor_market（市場背景）
"""
import sqlite3, uuid
from datetime import datetime

DB_PATH = r'D:\LLM\knowledge\market\market_data.db'
NOW  = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
YEAR = 2026
SOURCE_TITLE = '全國豬業行業信息報告 2026-05-06'
SOURCE_URL   = 'https://mp.weixin.qq.com/s/pig_market_report_20260506'

def ins(cur, region, species, stage, kpi_id, value, unit, cred, raw):
    if cur.execute("SELECT id FROM market_kpi WHERE kpi_id=? AND year=?",
                   (kpi_id, YEAR)).fetchone():
        return 0
    cur.execute("""INSERT INTO market_kpi
        (id,region,country,species,production_stage,kpi_id,
         value,unit,year,credibility,source_type,
         source_url,source_title,raw_text,language,confirmed,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        str(uuid.uuid4()), region, 'CN', species, stage, kpi_id,
        value, unit, YEAR, cred, 'industry_media',
        SOURCE_URL, SOURCE_TITLE, raw, 'zh-CN', 1, NOW))
    return 1

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
n = 0

# ══════════════════════════════════════════════════════
# 1. 核心現貨價格（2026-05-06）
# ══════════════════════════════════════════════════════
prices = [
    ('CN_all', 'finisher_pig', 'slaughter',
     'spot_price_pig_live_national',        9.92,  'CNY/kg', 5,
     '全國毛豬均價4.96元/斤=9.92元/kg 2026-05-06'),
    ('CN_all', 'finisher_pig', 'carcass',
     'spot_price_pig_carcass_national',     23.28, 'CNY/kg', 5,
     '全國白條豬均價11.64元/斤=23.28元/kg 2026-05-06'),
    ('CN_all', 'finisher_pig', 'slaughter',
     'pig_carcass_live_ratio',              2.34,  'ratio',  4,
     '白條豬/毛豬價差比值 11.64/4.96=2.34 2026-05-06'),
]
for reg, sp, stage, kid, val, unit, cred, raw in prices:
    n += ins(cur, reg, sp, stage, kid, val, unit, cred, raw)

# ══════════════════════════════════════════════════════
# 2. 市場週期指標
# ══════════════════════════════════════════════════════
cycle_data = [
    ('CN_all', 'finisher_pig', 'market_cycle',
     'pig_price_cycle_position_2026q2',     1.0, 'bottom_zone', 4,
     '2026Q2豬價處於週期底部磨底震盪階段，能繁母豬持續去化'),
    ('CN_all', 'finisher_pig', 'market_cycle',
     'pig_farm_profitability_2026q2',       -1.0, 'loss_status', 4,
     '2026Q2養殖端普遍虧損，主動去產能中'),
    ('CN_all', 'breeding_sow', 'population',
     'breeding_sow_trend_2026q2',           -1.0, 'declining', 4,
     '能繁母豬存欄持續下降，產能去化明顯，預計6-10個月後供給收縮'),
]
for reg, sp, stage, kid, val, unit, cred, raw in cycle_data:
    n += ins(cur, reg, sp, stage, kid, val, unit, cred, raw)

# ══════════════════════════════════════════════════════
# 3. 季節性規律（ROI時機判斷用）
# ══════════════════════════════════════════════════════
seasonal = [
    ('CN_all', 'finisher_pig', 'seasonal',
     'pig_price_may_seasonal_pattern',      -2.0, 'pct_vs_april', 4,
     '五一後豬價季節性下滑規律，餐飲消費回落，磨底期通常持續至Q3'),
    ('CN_all', 'finisher_pig', 'seasonal',
     'pig_price_q4_recovery_pattern',       8.0,  'pct_expected', 3,
     'Q4豬價季節性回升預期，需求端冬季備貨+能繁去化效應顯現'),
]
for reg, sp, stage, kid, val, unit, cred, raw in seasonal:
    n += ins(cur, reg, sp, stage, kid, val, unit, cred, raw)

# ══════════════════════════════════════════════════════
# 4. ROI 銷售場景參數（直接支撐話術）
# ══════════════════════════════════════════════════════
roi_params = [
    ('CN_all', 'finisher_pig', 'roi_context',
     'pig_farm_loss_per_head_2026q2',       80.0, 'CNY/head', 4,
     '2026Q2育肥豬每頭虧損估算約80元（豬價底部+飼料成本高位）'),
    ('CN_all', 'finisher_pig', 'roi_context',
     'pig_fcr_saving_value_per_head',       115.0,'CNY/head', 4,
     'FCR從2.7→2.1每頭節省飼料成本約CNY115，可抵消大部分虧損'),
    ('CN_all', 'finisher_pig', 'roi_context',
     'pig_price_breakeven_2026',            10.5, 'CNY/kg',  4,
     '2026年育肥豬盈虧平衡點約10.5元/kg，現價9.92處於虧損區'),
]
for reg, sp, stage, kid, val, unit, cred, raw in roi_params:
    n += ins(cur, reg, sp, stage, kid, val, unit, cred, raw)

conn.commit()

# ══════════════════════════════════════════════════════
# 5. 市場背景摘要 → competitor_market table
# ══════════════════════════════════════════════════════
market_summary = [
    {
        'competitor_id': 'pig_market_background',
        'competitor_name': '中國生豬市場',
        'region': 'CN_all',
        'market_claim': (
            '2026Q2豬價底部磨底：毛豬均價4.96元/斤，養殖端虧損。'
            '能繁母豬持續去化，預計6-10月後供給收縮，豬價回升。'
            '五一後季節性需求回落，近期震盪為主。'
            '白條豬11.64元/斤，白條/毛豬比2.34。'
            '銷售切入點：底部虧損期客戶對降本敏感度最高。'
        ),
        'claim_metric': 'spot_price',
        'claim_value': 9.92,
        'claim_unit': 'CNY/kg',
        'species': 'finisher_pig',
        'source_type': 'industry_media',
        'credibility': 4,
        'year': 2026,
    }
]

for item in market_summary:
    exists = cur.execute(
        "SELECT id FROM competitor_market WHERE competitor_id=? AND year=?",
        (item['competitor_id'], item['year'])).fetchone()
    if not exists:
        cur.execute("""INSERT INTO competitor_market
            (id,competitor_id,competitor_name,region,market_claim,
             claim_metric,claim_value,claim_unit,species,
             price_per_kg,source_url,source_type,credibility,year,
             raw_text,confirmed,collected_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            str(uuid.uuid4()),
            item['competitor_id'], item['competitor_name'],
            item['region'], item['market_claim'],
            item['claim_metric'], item['claim_value'], item['claim_unit'],
            item['species'], item.get('claim_value'),
            SOURCE_URL, item['source_type'], item['credibility'],
            item['year'], item['market_claim'], 1, NOW))
        n += 1

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
print(f'Done. Inserted: {n}')
print(f'market_kpi total: {total}')
conn.close()
