# -*- coding: utf-8 -*-
"""
import_livestock_prices_20260507.py
2026-05-07 全物種現貨價格批量導入
牛/羊/肉雞/蝦/魚 + 蛋雞飼料配方
"""
import sqlite3, uuid
from datetime import datetime

DB_PATH = r'D:\LLM\knowledge\market\market_data.db'
NOW  = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
YEAR = 2026
SRC  = '市場行情匯總 2026-05-07'

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
n = 0

def ins(species, region, kpi_id, value, vmin, vmax, unit, cred, note):
    global n
    if cur.execute("SELECT id FROM market_kpi WHERE kpi_id=? AND year=?",
                   (kpi_id, YEAR)).fetchone():
        return
    cur.execute("""INSERT INTO market_kpi
        (id,region,country,species,production_stage,kpi_id,
         value,value_min,value_max,unit,year,
         credibility,source_type,source_url,source_title,
         raw_text,language,confirmed,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        str(uuid.uuid4()), region, 'CN', species,
        'market_price', kpi_id,
        value, vmin, vmax, unit, YEAR,
        cred, 'industry_media', '', SRC,
        note, 'zh-CN', 1, NOW))
    n += 1

def mid(lo, hi): return round((lo+hi)/2, 1)

# ══════════════════════════════════════════════════════
# 1. 生牛價格（元/斤 → 元/kg ×2）
# ══════════════════════════════════════════════════════
cattle = [
    ('beef_cattle','CN_northeast','spot_price_cattle_heilongjiang', mid(14.5,15.0)*2, 14.5*2,15.0*2,'黑龍江 14.5-15.0元/斤'),
    ('beef_cattle','CN_northeast','spot_price_cattle_jilin',        mid(14.8,15.4)*2, 14.8*2,15.4*2,'吉林 14.8-15.4元/斤'),
    ('beef_cattle','CN_northeast','spot_price_cattle_liaoning',     mid(14.8,15.3)*2, 14.8*2,15.3*2,'遼寧 14.8-15.3元/斤'),
    ('beef_cattle','CN_north',    'spot_price_cattle_inner_mongolia',mid(14.7,15.2)*2,14.7*2,15.2*2,'內蒙古 14.7-15.2元/斤'),
    ('beef_cattle','CN_north',    'spot_price_cattle_hebei_shanxi', mid(14.5,15.2)*2, 14.5*2,15.2*2,'河北/山西 14.5-15.2元/斤'),
    ('beef_cattle','CN_north',    'spot_price_cattle_shandong',     mid(14.7,15.1)*2, 14.7*2,15.1*2,'山東 14.7-15.1元/斤'),
    ('beef_cattle','CN_east',     'spot_price_cattle_jiangsu',      mid(14.5,15.0)*2, 14.5*2,15.0*2,'江蘇 14.5-15.0元/斤'),
    ('beef_cattle','CN_east',     'spot_price_cattle_anhui',        mid(14.5,15.0)*2, 14.5*2,15.0*2,'安徽 14.5-15.0元/斤'),
    ('beef_cattle','CN_central',  'spot_price_cattle_hubei',        mid(14.4,15.0)*2, 14.4*2,15.0*2,'湖北 14.4-15.0元/斤'),
    ('beef_cattle','CN_central',  'spot_price_cattle_hunan',        mid(14.4,15.0)*2, 14.4*2,15.0*2,'湖南 14.4-15.0元/斤'),
    ('beef_cattle','CN_central',  'spot_price_cattle_henan',        mid(14.5,15.3)*2, 14.5*2,15.3*2,'河南 14.5-15.3元/斤'),
    ('beef_cattle','CN_south',    'spot_price_cattle_guangdong',    mid(15.0,16.1)*2, 15.0*2,16.1*2,'廣東 15.0-16.1元/斤'),
    ('beef_cattle','CN_south',    'spot_price_cattle_guangxi',      mid(14.8,15.5)*2, 14.8*2,15.5*2,'廣西 14.8-15.5元/斤'),
    ('beef_cattle','CN_southwest','spot_price_cattle_sichuan',      mid(14.6,15.2)*2, 14.6*2,15.2*2,'四川/重慶 14.6-15.2元/斤'),
    ('beef_cattle','CN_north',    'spot_price_cattle_gansu_xinjiang',mid(13.5,15.0)*2,13.5*2,15.0*2,'甘肅/新疆 13.5-15.0元/斤'),
    # 東北均價
    ('beef_cattle','CN_northeast','spot_price_cattle_ne_avg_20260507',
     mid(14.7,15.2)*2, 14.5*2, 15.4*2, '東北生牛均價 2026-05-07'),
]
for sp,reg,kid,val,vmin,vmax,note in cattle:
    ins(sp,reg,kid,round(val,1),round(vmin,1),round(vmax,1),'CNY/kg',4,note)

# ══════════════════════════════════════════════════════
# 2. 活羊價格（元/斤 → 元/kg ×2）
# ══════════════════════════════════════════════════════
sheep = [
    ('meat_sheep','CN_all',       'spot_price_sheep_national_avg',   30.67,None,None,'全國活羊均價 30.67元/kg 同比+5.4%'),
    ('meat_sheep','CN_all',       'spot_price_mutton_national_avg',  72.56,None,None,'全國羊肉（整羊）均價 72.56元/kg 同比+4.6%'),
    ('meat_sheep','CN_north',     'spot_price_sheep_hebei_shandong', mid(13,14.1)*2,13*2,14.1*2,'河北/山東 13-14.1元/斤'),
    ('meat_sheep','CN_north',     'spot_price_sheep_shanxi',         mid(11.5,12.5)*2,11.5*2,12.5*2,'山西 11.5-12.5元/斤'),
    ('meat_sheep','CN_north',     'spot_price_sheep_inner_mongolia', mid(13.1,13.8)*2,13.1*2,13.8*2,'內蒙古 13.1-13.8元/斤'),
    ('meat_sheep','CN_northeast', 'spot_price_sheep_heilongjiang',   mid(13.5,14.1)*2,13.5*2,14.1*2,'黑龍江/遼寧 13.5-14.1元/斤'),
    ('meat_sheep','CN_northeast', 'spot_price_sheep_jilin',          mid(13.8,14.2)*2,13.8*2,14.2*2,'吉林 13.8-14.2元/斤'),
    ('meat_sheep','CN_east',      'spot_price_sheep_jiangsu_anhui',  mid(13.5,14.0)*2,13.5*2,14.0*2,'江蘇/安徽 13.5-14.0元/斤'),
    ('meat_sheep','CN_east',      'spot_price_sheep_shanghai',       mid(14.0,14.8)*2,14.0*2,14.8*2,'上海/浙江 14.0-14.8元/斤'),
    ('meat_sheep','CN_central',   'spot_price_sheep_henan_hubei',    mid(13.5,14.1)*2,13.5*2,14.1*2,'河南/湖北 13.5-14.1元/斤'),
    ('meat_sheep','CN_south',     'spot_price_sheep_guangdong',      mid(13.9,14.5)*2,13.9*2,14.5*2,'廣東/廣西 13.9-14.5元/斤'),
    ('meat_sheep','CN_southwest', 'spot_price_sheep_sichuan',        mid(12.6,13.7)*2,12.6*2,13.7*2,'四川/重慶 12.6-13.7元/斤'),
    ('meat_sheep','CN_north',     'spot_price_sheep_shaanxi_ningxia',mid(13.4,14.1)*2,13.4*2,14.1*2,'陝西/寧夏 13.4-14.1元/斤'),
    ('meat_sheep','CN_north',     'spot_price_sheep_gansu_xinjiang', mid(13.1,13.8)*2,13.1*2,13.8*2,'甘肅/新疆 13.1-13.8元/斤'),
    # 東北均價
    ('meat_sheep','CN_northeast', 'spot_price_sheep_ne_avg_20260507',
     mid(13.7,14.2)*2,13.5*2,14.2*2,'東北活羊均價 2026-05-07'),
]
for sp,reg,kid,val,vmin,vmax,note in sheep:
    ins(sp,reg,kid,round(val,1),
        round(vmin,1) if vmin else None,
        round(vmax,1) if vmax else None,
        'CNY/kg',4,note)

# ══════════════════════════════════════════════════════
# 3. 肉雞出欄價（元/斤 → 元/kg ×2）
# ══════════════════════════════════════════════════════
broiler = [
    ('broiler','CN_north',    'spot_price_broiler_shandong',    mid(3.70,3.85)*2,3.70*2,3.85*2,'山東白羽 棚前3.70-3.85元/斤'),
    ('broiler','CN_northeast','spot_price_broiler_liaoning',    mid(3.95,4.00)*2,3.95*2,4.00*2,'遼寧 棚前3.95-4.00元/斤'),
    ('broiler','CN_north',    'spot_price_broiler_jingjinji',   mid(3.65,3.80)*2,3.65*2,3.80*2,'京津冀 3.65-3.80元/斤'),
    ('broiler','CN_central',  'spot_price_broiler_henan',       mid(3.70,3.70)*2,3.70*2,3.70*2,'河南白羽 3.70元/斤'),
    ('broiler','CN_southwest','spot_price_broiler_sichuan_maji',mid(5.10,5.30)*2,5.10*2,5.30*2,'川渝麻鸡≥2kg 5.10-5.30元/斤'),
    ('broiler','CN_east',     'spot_price_broiler_anhui_maji',  mid(4.40,4.50)*2,4.40*2,4.50*2,'安徽麻雞 4.40-4.50元/斤'),
    # 東北均價
    ('broiler','CN_northeast','spot_price_broiler_ne_avg_20260507',
     mid(3.95,4.00)*2,3.95*2,4.00*2,'東北白羽肉雞均價 2026-05-07'),
]
for sp,reg,kid,val,vmin,vmax,note in broiler:
    ins(sp,reg,kid,round(val,2),round(vmin,2),round(vmax,2),'CNY/kg',4,note)

# ══════════════════════════════════════════════════════
# 4. 蝦類價格（元/斤 → 元/kg ×2）
# ══════════════════════════════════════════════════════
shrimp_prices = [
    # 南美白蝦
    ('shrimp','CN_south','spot_price_shrimp_guangdong_30head', 15*2,None,None,'廣東珠三角30頭 15元/斤'),
    ('shrimp','CN_south','spot_price_shrimp_guangdong_20head', 18*2,None,None,'廣東珠三角20頭 18元/斤'),
    ('shrimp','CN_south','spot_price_shrimp_zhanjiang_30head', 16*2,None,None,'廣東湛江30頭 16元/斤'),
    ('shrimp','CN_south','spot_price_shrimp_guangxi_30head',   15*2,None,None,'廣西北海30頭 15元/斤'),
    ('shrimp','CN_east', 'spot_price_shrimp_jiangsu_30head',   18*2,None,None,'江蘇30頭 18元/斤'),
    ('shrimp','CN_north','spot_price_shrimp_shandong_20head',  20*2,None,None,'山東20頭 20元/斤'),
    ('shrimp','CN_south','spot_price_shrimp_cn_south_avg',     mid(14,16)*2,14*2,18*2,'華南白蝦均價 30頭規格'),
    # 羅氏沼蝦
    ('shrimp','CN_south','spot_price_shrimp_macrobrachium_10head',mid(55,60)*2,55*2,60*2,'廣東肇庆罗氏沼虾10頭 55-60元/斤'),
    ('shrimp','CN_south','spot_price_shrimp_macrobrachium_15head',mid(45,50)*2,45*2,50*2,'廣東肇庆罗氏沼虾15頭 45-50元/斤'),
]
for sp,reg,kid,val,vmin,vmax,note in shrimp_prices:
    ins(sp,reg,kid,round(val,1),
        round(vmin,1) if vmin else None,
        round(vmax,1) if vmax else None,
        'CNY/kg',4,note)

# ══════════════════════════════════════════════════════
# 5. 魚類價格（元/斤 → 元/kg ×2）
# ══════════════════════════════════════════════════════
fish_prices = [
    ('tilapia',         'CN_all',  'spot_price_tilapia_national',    3.5*2,None,None,'羅非魚全國均價 3.5元/斤'),
    ('tilapia',         'CN_south','spot_price_tilapia_guangdong',   3.4*2,None,None,'廣東羅非魚 3.4元/斤'),
    ('grass_carp',      'CN_all',  'spot_price_grass_carp_national', 7.4*2,None,None,'草魚全國均價 7.4元/斤'),
    ('grass_carp',      'CN_south','spot_price_grass_carp_guangdong',mid(7.9,8.3)*2,7.9*2,8.3*2,'廣東草魚 7.9-8.3元/斤'),
    ('crucian_carp',    'CN_all',  'spot_price_crucian_national',    9.9*2,None,None,'鯽魚全國均價 9.9元/斤'),
    ('carp',            'CN_all',  'spot_price_carp_national',       5.7*2,None,None,'鯉魚全國均價 5.7元/斤'),
    ('silver_carp',     'CN_all',  'spot_price_silver_carp_national',mid(7.3,8.5)*2,7.3*2,8.5*2,'花鰱全國均價 7.3-8.5元/斤'),
]
for sp,reg,kid,val,vmin,vmax,note in fish_prices:
    ins(sp,reg,kid,round(val,1),
        round(vmin,1) if vmin else None,
        round(vmax,1) if vmax else None,
        'CNY/kg',3,note)

# ══════════════════════════════════════════════════════
# 6. 蛋雞飼料配方（配方師核心數據）
# ══════════════════════════════════════════════════════
layer_formula = [
    # 產蛋期主流配方（3個配方的均值）
    ('layer_chicken','CN_all','feed_formula_corn_ratio_layer',
     58.2,57.4,58.4,'%','產蛋雞玉米比例均值 57.4-58.4%'),
    ('layer_chicken','CN_all','feed_formula_soybean_ratio_layer',
     23.2,20.0,28.0,'%','產蛋雞豆粕比例 20-28%（含魚粉菜粕配方低）'),
    ('layer_chicken','CN_all','feed_formula_limestone_ratio_layer',
     8.0,8.0,8.0,'%','產蛋雞石粉8%（補鈣關鍵）'),
    ('layer_chicken','CN_all','feed_formula_premix_ratio_layer',
     1.0,1.0,1.0,'%','預混料1%（含維生素礦物質）'),
    # 雛雞配方
    ('layer_chicken','CN_all','feed_formula_corn_ratio_chick',
     62.1,61.7,62.7,'%','雛雞玉米比例 61.7-62.7%'),
    ('layer_chicken','CN_all','feed_formula_soybean_ratio_chick',
     27.0,24.0,31.0,'%','雛雞豆粕比例 24-31%'),
    # 育成期配方
    ('layer_chicken','CN_all','feed_formula_corn_ratio_pullet',
     61.2,60.4,61.9,'%','育成雞玉米比例 60.4-61.9%'),
    ('layer_chicken','CN_all','feed_formula_soybean_ratio_pullet',
     18.0,15.5,21.0,'%','育成雞豆粕比例 15.5-21%'),
]
for sp,reg,kid,val,vmin,vmax,unit,note in layer_formula:
    ins(sp,reg,kid,val,vmin,vmax,unit,4,note)

# ══════════════════════════════════════════════════════
# 7. 蝦市場趨勢（ROI銷售背景）
# ══════════════════════════════════════════════════════
ins('shrimp','CN_south','shrimp_price_trend_may2026',
    1.0,None,None,'bullish_signal',3,
    '白蝦5月進入復甦上漲通道，華南存塘下降，價格筑底完成')
ins('shrimp','CN_south','shrimp_macrobrachium_risk_jul2026',
    -1.0,None,None,'bearish_signal',3,
    '罗氏沼虾7月江浙大量上市，預計跌至20元，現在高位應出貨')

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
ne    = conn.execute("SELECT COUNT(*) FROM market_kpi WHERE region='CN_northeast'").fetchone()[0]
price = conn.execute("SELECT COUNT(*) FROM market_kpi WHERE kpi_id LIKE '%spot_price%' AND year=2026").fetchone()[0]

print(f'Done. Inserted: {n}')
print(f'DB total: {total} | CN_northeast: {ne} | 2026價格: {price}')
print()
print('=== 東北核心價格更新 ===')
print(f'生牛: ~{mid(14.7,15.2)*2:.1f}元/kg（東北均值）')
print(f'活羊: ~{mid(13.7,14.2)*2:.1f}元/kg（東北均值）')
print(f'肉雞: ~{mid(3.95,4.00)*2:.2f}元/kg（遼寧）')
print(f'玉米: 2.22元/kg | 豆粕: 2.98元/kg')
print(f'配合飼料: {(2220*0.60+2980*0.20+2800*0.20)/1000:.3f}元/kg')
