# -*- coding: utf-8 -*-
"""
import_market_prices_20260506.py
2026-05-06 全物種現貨價格批量導入
來源：10張截圖 OCR 提取
物種：生豬/仔豬/牛/羊/雞蛋/肉雞/蛋雞/豬肉批發
"""
import sqlite3, uuid
from datetime import datetime

DB_PATH = r'D:\LLM\knowledge\market\market_data.db'
NOW  = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
DATE = '2026-05-06'
YEAR = 2026

def ins(cur, region, country, species, stage, kpi_id,
        value, unit, cred, src_url, src_title, raw):
    if cur.execute("SELECT id FROM market_kpi WHERE kpi_id=? AND year=?",
                   (kpi_id, YEAR)).fetchone():
        return 0
    cur.execute("""INSERT INTO market_kpi
        (id,region,country,species,production_stage,kpi_id,
         value,unit,year,credibility,source_type,
         source_url,source_title,raw_text,language,confirmed,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        str(uuid.uuid4()), region, country, species, stage, kpi_id,
        value, unit, YEAR, cred, 'industry_media',
        src_url, src_title, raw, 'zh-CN', 1, NOW))
    return 1

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
n = 0

# ══════════════════════════════════════════════════════
# 1. 生豬出欄價 2026-05-06（圖1：海大農牧嘉牧版）
#    單位：元/公斤，含土雜/散戶/均價
# ══════════════════════════════════════════════════════
SRC1 = ('https://mp.weixin.qq.com', '海大農牧嘉牧版 2026-05-06 生豬出欄價')
pig_slaughter = [
    # (province, region,    tuzai, sanhu, avg)
    ('河南',  'CN_central',  10.23, 9.70, 10.07),
    ('湖南',  'CN_central',   9.42, 9.30,  9.38),
    ('安徽',  'CN_east',     10.18,10.10, 10.16),
    ('山西',  'CN_north',     9.76, 9.60,  9.71),
    ('山東',  'CN_east',     10.25,10.00, 10.18),
    ('廣東',  'CN_south',    10.12,10.00, 10.08),
    ('遼寧',  'CN_northeast', 9.80, 9.40,  9.68),
    ('吉林',  'CN_northeast', 9.65, 9.20,  9.52),
    ('黑龍江','CN_northeast', 9.45, 9.20,  9.38),
    ('四川',  'CN_southwest', 9.60, 9.40,  9.54),
    ('福建',  'CN_east',      9.70, 9.60,  9.67),
    ('浙江',  'CN_east',     10.30,10.30, 10.30),
    ('江蘇',  'CN_east',     10.30,10.25, 10.29),
    ('雲南',  'CN_southwest', 9.35, 9.20,  9.31),
    ('內蒙古','CN_north',     9.60, 9.40,  9.68),
    ('陝西',  'CN_north',     8.88, 9.80,  9.86),
    ('重慶',  'CN_southwest', 9.40, 9.20,  9.34),
]
for prov, reg, tz, sh, avg in pig_slaughter:
    for grade, val in [('tuzai', tz), ('sanhu', sh), ('avg', avg)]:
        kpi_id = f'slaughter_price_pig_{grade}_{prov}'
        n += ins(cur, reg, 'CN', 'finisher_pig', 'slaughter', kpi_id,
                 val, 'CNY/kg', 4, SRC1[0], SRC1[1],
                 f'{prov} {grade} {val}元/kg {DATE}')

# 全國均價（今日/昨日）
n += ins(cur,'CN_all','CN','finisher_pig','slaughter',
         'slaughter_price_pig_national_today',
         9.55, 'CNY/kg', 4, SRC1[0], SRC1[1], f'全國均價今日 {DATE}')
n += ins(cur,'CN_all','CN','finisher_pig','slaughter',
         'slaughter_price_pig_national_yesterday',
         9.69, 'CNY/kg', 4, SRC1[0], SRC1[1], f'全國均價昨日 {DATE}')

# ══════════════════════════════════════════════════════
# 2. 仔豬價格 2026-05-06（圖1下半）
#    集團6.5kg豬 / 散戶15kg豬，單位：元/頭
# ══════════════════════════════════════════════════════
SRC2 = ('https://mp.weixin.qq.com', '海大農牧嘉牧版 2026-05-06 仔豬價格')
piglet_prices = [
    # (province, region, group_6.5kg, farm_15kg)
    ('河南',  'CN_central',  245, 340),
    ('湖南',  'CN_central',  250, 350),
    ('湖北',  'CN_central',  245, 350),
    ('安徽',  'CN_east',     250, 355),
    ('江西',  'CN_east',     250, 355),
    ('河北',  'CN_north',    250, 355),
    ('黑龍江','CN_northeast',225, 320),
    ('四川',  'CN_southwest',245, 345),
    ('貴州',  'CN_southwest',250, 345),
    ('廣東',  'CN_south',    250, 360),
    ('廣西',  'CN_south',    250, 355),
    ('江蘇',  'CN_east',     250, 350),
    ('重慶',  'CN_southwest',250, 350),
]
for prov, reg, g65, f15 in piglet_prices:
    n += ins(cur, reg, 'CN', 'nursery_pig', 'piglet_sale',
             f'piglet_price_group65kg_{prov}',
             g65, 'CNY/head', 4, SRC2[0], SRC2[1],
             f'{prov} 集團6.5kg仔豬 {g65}元/頭 {DATE}')
    n += ins(cur, reg, 'CN', 'nursery_pig', 'piglet_sale',
             f'piglet_price_farm15kg_{prov}',
             f15, 'CNY/head', 4, SRC2[0], SRC2[1],
             f'{prov} 散戶15kg仔豬 {f15}元/頭 {DATE}')
# 全國均價
n += ins(cur,'CN_all','CN','nursery_pig','piglet_sale',
         'piglet_price_national_group_avg', 246, 'CNY/head', 4,
         SRC2[0], SRC2[1], f'全國均價集團6.5kg {DATE}')
n += ins(cur,'CN_all','CN','nursery_pig','piglet_sale',
         'piglet_price_national_farm_avg', 349, 'CNY/head', 4,
         SRC2[0], SRC2[1], f'全國均價散戶15kg {DATE}')

# ══════════════════════════════════════════════════════
# 3. 生牛價格 2026-05-06（圖5：一鴻生物）
#    單位：元/斤，換算元/kg
# ══════════════════════════════════════════════════════
SRC3 = ('https://mp.weixin.qq.com', '一鴻生物 2026-05-06 今日牛價')
cattle_prices = [
    # (province, region, low_jin, high_jin)
    ('黑龍江', 'CN_northeast', 14.5, 15.0),
    ('吉林',   'CN_northeast', 14.8, 15.4),
    ('遼寧',   'CN_northeast', 14.8, 15.3),
    ('內蒙古', 'CN_north',     14.7, 15.2),
    ('河北/山西','CN_north',   14.5, 15.2),
    ('山東',   'CN_east',      14.7, 15.1),
    ('江蘇',   'CN_east',      14.5, 15.0),
    ('安徽',   'CN_east',      14.5, 15.0),
    ('湖北',   'CN_central',   14.4, 15.0),
    ('湖南',   'CN_central',   14.4, 15.0),
    ('河南',   'CN_central',   14.5, 15.3),
    ('廣東',   'CN_south',     15.0, 16.1),
    ('廣西',   'CN_south',     14.8, 15.5),
    ('四川/重慶','CN_southwest',14.6,15.2),
    ('甘肅/新疆','CN_north',   13.5,15.0),
]
for prov, reg, lo, hi in cattle_prices:
    mid = round((lo+hi)/2*2, 2)  # 元/kg
    lo_kg = round(lo*2, 2)
    hi_kg = round(hi*2, 2)
    safe  = prov.replace('/','_')
    n += ins(cur, reg, 'CN', 'beef_cattle', 'slaughter',
             f'slaughter_price_cattle_{safe}',
             mid, 'CNY/kg', 4, SRC3[0], SRC3[1],
             f'{prov} 生牛 {lo}-{hi}元/斤={lo_kg}-{hi_kg}元/kg {DATE}')

# ══════════════════════════════════════════════════════
# 4. 羊價格 2026-05-06（圖9：西默農）
#    肉羊均價/山羊均價，單位：元/斤
# ══════════════════════════════════════════════════════
SRC4 = ('https://mp.weixin.qq.com', '西默農 2026-05-06 最新羊價格')
sheep_prices = [
    # (province, region, low_jin, high_jin, species_type)
    ('北京',  'CN_north',     14.0, 15.0, 'meat_sheep'),
    ('天津',  'CN_north',     14.0, 15.0, 'meat_sheep'),
    ('河北',  'CN_north',     14.0, 15.0, 'meat_sheep'),
    ('山西',  'CN_north',     14.0, 15.0, 'meat_sheep'),
    ('內蒙古','CN_north',     14.0, 15.0, 'meat_sheep'),
    ('山東',  'CN_east',      14.0, 15.5, 'meat_sheep'),
    ('江蘇',  'CN_east',      14.0, 15.0, 'meat_sheep'),
    ('安徽',  'CN_east',      14.0, 15.0, 'meat_sheep'),
    ('河南',  'CN_central',   14.0, 15.0, 'meat_sheep'),
    ('湖北',  'CN_central',   14.0, 15.0, 'meat_sheep'),
    ('湖南',  'CN_central',   14.0, 15.0, 'meat_sheep'),
    ('廣東',  'CN_south',     14.5, 16.0, 'meat_sheep'),
    ('廣西',  'CN_south',     14.5, 15.5, 'meat_sheep'),
    ('四川',  'CN_southwest', 14.0, 15.0, 'meat_sheep'),
    ('雲南',  'CN_southwest', 14.0, 15.0, 'meat_sheep'),
    ('重慶',  'CN_southwest', 14.0, 15.0, 'meat_sheep'),
    ('陝西',  'CN_north',     14.0, 15.0, 'meat_sheep'),
    ('甘肅',  'CN_north',     13.5, 15.0, 'meat_sheep'),
    ('新疆',  'CN_north',     13.5, 15.0, 'meat_sheep'),
    # 山羊
    ('全國南方','CN_south',   15.5, 16.5, 'meat_goat'),
    ('全國北方','CN_north',   14.0, 15.0, 'meat_goat'),
]
for prov, reg, lo, hi, sp in sheep_prices:
    mid   = round((lo+hi)/2*2, 2)
    safe  = prov.replace('/','_')
    n += ins(cur, reg, 'CN', sp, 'slaughter',
             f'slaughter_price_{sp}_{safe}',
             mid, 'CNY/kg', 4, SRC4[0], SRC4[1],
             f'{prov} {sp} {lo}-{hi}元/斤={mid}元/kg {DATE}')

# 全國均價
n += ins(cur,'CN_all','CN','meat_sheep','slaughter',
         'slaughter_price_sheep_national_avg',
         14.8*2, 'CNY/kg', 4, SRC4[0], SRC4[1],
         f'全國肉羊均價14.8元/斤 {DATE}')
n += ins(cur,'CN_all','CN','meat_goat','slaughter',
         'slaughter_price_goat_national_avg',
         13.2*2, 'CNY/kg', 4, SRC4[0], SRC4[1],
         f'全國山羊均價13.2元/斤 {DATE}')

# ══════════════════════════════════════════════════════
# 5. 豬肉批發價（圖10：長沙DVN，華東）
#    單位：元/斤，出欄體重110kg
# ══════════════════════════════════════════════════════
SRC5 = ('https://mp.weixin.qq.com', 'DVN 2026-05-06 豬出欄價格華東')
pig_east = [
    ('上海',  'CN_east',  5.0, 5.3, 110),
    ('山東',  'CN_east',  4.9, 5.2, 110),
    ('安徽',  'CN_east',  5.0, 5.2, 110),
    ('浙江',  'CN_east',  5.0, 5.3, 110),
    ('江蘇',  'CN_east',  5.1, 5.2, 110),
    ('福建',  'CN_east',  4.9, 5.1, 110),
    ('江西',  'CN_east',  4.6, 4.7, 110),
]
for prov, reg, lo, hi, wt in pig_east:
    mid = round((lo+hi)/2*2, 2)
    n += ins(cur, reg, 'CN', 'finisher_pig', 'slaughter',
             f'slaughter_price_pig_dvn_{prov}',
             mid, 'CNY/kg', 4, SRC5[0], SRC5[1],
             f'{prov} {lo}-{hi}元/斤={mid}元/kg 出欄{wt}kg {DATE}')

# ══════════════════════════════════════════════════════
# 6. 雞蛋/蛋雞價格（圖2/7：今日雞蛋價格）
# ══════════════════════════════════════════════════════
SRC6 = ('https://mp.weixin.qq.com', '今日雞蛋行情 2026-05-06')
# 全國雞蛋均價：約4.2元/斤=8.4元/kg（從圖2讀取）
n += ins(cur,'CN_all','CN','layer_chicken','egg_market',
         'egg_spot_price_national_avg',
         4.20*2, 'CNY/kg', 4, SRC6[0], SRC6[1],
         f'全國雞蛋均價4.20元/斤 {DATE}')

# 各省雞蛋價（圖2解析，元/斤）
egg_prices = [
    ('河南',   'CN_central',  4.10, 4.25),
    ('河北',   'CN_north',    4.15, 4.30),
    ('山東',   'CN_east',     4.10, 4.25),
    ('江蘇',   'CN_east',     4.20, 4.35),
    ('安徽',   'CN_east',     4.10, 4.30),
    ('湖北',   'CN_central',  4.15, 4.30),
    ('湖南',   'CN_central',  4.20, 4.35),
    ('廣東',   'CN_south',    4.40, 4.60),
    ('四川',   'CN_southwest',4.25, 4.40),
    ('遼寧',   'CN_northeast',4.05, 4.20),
    ('黑龍江', 'CN_northeast',3.90, 4.10),
]
for prov, reg, lo, hi in egg_prices:
    mid = round((lo+hi)/2*2, 2)
    n += ins(cur, reg, 'CN', 'layer_chicken', 'egg_market',
             f'egg_spot_price_{prov}',
             mid, 'CNY/kg', 4, SRC6[0], SRC6[1],
             f'{prov} 雞蛋 {lo}-{hi}元/斤={mid}元/kg {DATE}')

# ══════════════════════════════════════════════════════
# 7. 肉雞/白羽雞價格（圖6/4）
# ══════════════════════════════════════════════════════
SRC7 = ('https://mp.weixin.qq.com', '今日肉雞行情 2026-05-06')
broiler_prices = [
    ('山東',   'CN_east',      5.8, 6.2),
    ('廣東',   'CN_south',     6.0, 6.5),
    ('河南',   'CN_central',   5.6, 6.0),
    ('江蘇',   'CN_east',      5.8, 6.2),
    ('遼寧',   'CN_northeast', 5.5, 5.9),
    ('四川',   'CN_southwest', 5.8, 6.3),
    ('全國',   'CN_all',       5.9, 6.2),
]
for prov, reg, lo, hi in broiler_prices:
    mid = round((lo+hi)/2*2, 2)
    n += ins(cur, reg, 'CN', 'broiler', 'slaughter',
             f'slaughter_price_broiler_{prov}',
             mid, 'CNY/kg', 4, SRC7[0], SRC7[1],
             f'{prov} 肉雞 {lo}-{hi}元/斤={mid}元/kg {DATE}')

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
price_count = conn.execute(
    "SELECT COUNT(*) FROM market_kpi WHERE kpi_id LIKE '%price%' AND year=2026"
).fetchone()[0]
conn.close()

print(f'Done. Inserted: {n} new records')
print(f'2026 price records total: {price_count}')
print(f'market_kpi total: {total}')
print()
print('價格數據摘要 2026-05-06:')
print(f'  生豬出欄: {len(pig_slaughter)}省 + 全國均價')
print(f'  仔豬: {len(piglet_prices)}省 × 2規格')
print(f'  生牛: {len(cattle_prices)}區')
print(f'  羊: {len(sheep_prices)}區')
print(f'  雞蛋: {len(egg_prices)}省 + 全國')
print(f'  肉雞: {len(broiler_prices)}省')
