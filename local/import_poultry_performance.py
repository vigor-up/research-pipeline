# -*- coding: utf-8 -*-
"""
import_poultry_performance.py
蛋雞/肉雞生產性能基準數據
來源：海蘭褐飼養手冊2021 + 行業技術文章
"""
import sqlite3, uuid
from datetime import datetime

DB_PATH = r'D:\LLM\knowledge\market\market_data.db'
NOW  = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
SRC1 = '海蘭褐飼養手冊2021 + 蛋雞飼料技術文章'
SRC2 = '家禽採食量計算公式 瑞華養殖在線2025'
SRC3 = '肉雞活動性與FCR研究 817養殖信息網'

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
n = 0

def ins(species, region, kpi_id, value, vmin, vmax, unit, year, cred, src, note):
    global n
    if cur.execute("SELECT id FROM market_kpi WHERE kpi_id=? AND year=?",
                   (kpi_id, year)).fetchone():
        return
    cur.execute("""INSERT INTO market_kpi
        (id,region,country,species,production_stage,kpi_id,
         value,value_min,value_max,unit,year,
         credibility,source_type,source_url,source_title,
         raw_text,language,confirmed,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        str(uuid.uuid4()), region, 'CN', species, 'production',
        kpi_id, value, vmin, vmax, unit, year,
        cred, 'academic_background', '', src,
        note, 'zh-CN', 1, NOW))
    n += 1

# ══════════════════════════════════════════════════════
# 1. 蛋雞72週全程料蛋比（品種別）
# ══════════════════════════════════════════════════════
layer_fcr = [
    ('layer_chicken','CN_all','fcr_layer_hyline_brown_72w',
     2.15,2.1,2.2,'kg_feed/kg_egg',2023,5,SRC1,
     '海蘭褐72週料蛋比2.1-2.2，日採食107-114g，產蛋325-340枚'),
    ('layer_chicken','CN_all','fcr_layer_hyline_grey_72w',
     1.93,1.88,1.97,'kg_feed/kg_egg',2023,5,SRC1,
     '海蘭灰72週料蛋比1.88-1.97，日採食101-105g，產蛋305-310枚'),
    ('layer_chicken','CN_all','fcr_layer_nongda3_72w',
     1.97,1.93,2.00,'kg_feed/kg_egg',2023,4,SRC1,
     '農大3號72週料蛋比1.93-2.00，日採食88g，產蛋306枚'),
    ('layer_chicken','CN_all','fcr_layer_jingfen1_72w',
     1.99,1.98,2.00,'kg_feed/kg_egg',2023,4,SRC1,
     '京粉1號72週料蛋比1.98-2.00，日採食110g，產蛋296-306枚'),
    ('layer_chicken','CN_all','fcr_layer_cn_good_farm',
     2.03,2.0,2.2,'kg_feed/kg_egg',2023,5,SRC1,
     '海蘭褐手冊標準：18-90週均採食110.7g，料蛋比2.03'),
    ('layer_chicken','CN_all','fcr_layer_cn_poor_farm',
     2.40,2.3,2.5,'kg_feed/kg_egg',2023,4,SRC1,
     '中國落後雞場料蛋比2.3-2.5，72週產蛋16-19kg'),
    ('layer_chicken','CN_all','fcr_layer_world_top',
     2.10,2.0,2.2,'kg_feed/kg_egg',2023,5,SRC1,
     '世界先進水平72週料蛋比2.0-2.2，產蛋20-21kg'),
]
for args in layer_fcr:
    ins(*args)

# ══════════════════════════════════════════════════════
# 2. 蛋雞日採食量基準
# ══════════════════════════════════════════════════════
layer_feed = [
    ('layer_chicken','CN_all','daily_feed_layer_peak',
     115.0,107.0,125.0,'g/day/bird',2023,5,SRC1,
     '產蛋高峰期日採食115g（120-125g為完全產蛋期標準）'),
    ('layer_chicken','CN_northeast','daily_feed_layer_ne_winter',
     118.0,115.0,122.0,'g/day/bird',2023,4,SRC1,
     '東北冬季採食量略高（保溫能量需求）'),
    ('layer_chicken','CN_all','daily_feed_layer_18to90w',
     110.7,107.0,114.0,'g/day/bird',2023,5,SRC1,
     '海蘭褐18-90週均採食110.7g（手冊標準）'),
]
for args in layer_feed:
    ins(*args)

# ══════════════════════════════════════════════════════
# 3. 蛋雞72週生產成績基準
# ══════════════════════════════════════════════════════
layer_perf = [
    ('layer_chicken','CN_all','egg_production_72w_cn_good',
     18.5,18.5,20.0,'kg/hen',2023,5,SRC1,
     '優質飼料雞場72週產蛋18.5-20kg，死淘率降低2%以上'),
    ('layer_chicken','CN_all','egg_production_72w_cn_poor',
     17.0,16.0,18.0,'kg/hen',2023,4,SRC1,
     '低檔飼料雞場72週產蛋16-18kg，死淘率10.8%'),
    ('layer_chicken','CN_all','egg_production_72w_world',
     20.5,20.0,21.0,'kg/hen',2023,5,SRC1,
     '世界先進水平72週產蛋20-21kg'),
    ('layer_chicken','CN_all','peak_production_rate_cn_good',
     92.0,90.0,95.0,'%',2023,5,SRC1,
     '優質飼料高峰產蛋率90%以上維持11個月以上'),
    ('layer_chicken','CN_all','peak_duration_cn_good',
     330.0,300.0,490.0,'days',2023,5,SRC1,
     '產蛋率90%高峰持續時間：目標490天（產500枚蛋基準）'),
    ('layer_chicken','CN_all','peak_duration_cn_avg',
     180.0,160.0,210.0,'days',2023,4,SRC1,
     '中國平均雞場高峰持續時間約160-210天'),
    ('layer_chicken','CN_all','mortality_72w_cn_good',
     4.0,2.0,6.0,'%',2023,5,SRC1,
     '優質飼料死淘率2-6%（世界先進水平）'),
    ('layer_chicken','CN_all','mortality_72w_cn_poor',
     10.8,10.0,15.0,'%',2023,4,SRC1,
     '低檔飼料死淘率10%以上，65-70週就淘汰'),
    ('layer_chicken','CN_all','egg_weight_72w_cn_good',
     65.3,62.0,66.0,'g/egg',2023,5,SRC1,
     '優質飼料72週均蛋重65.3g（海蘭褐標準）'),
    ('layer_chicken','CN_all','peak_rate_improve_good_feed',
     3.5,2.0,5.0,'days_earlier',2023,5,SRC1,
     '優質飼料上高峰縮短5天，蛋重提高0.5-1.2g，高峰延長2-5天'),
]
for args in layer_perf:
    ins(*args)

# ══════════════════════════════════════════════════════
# 4. 蛋雞飼料配方營養標準
# ══════════════════════════════════════════════════════
layer_nutrition = [
    ('layer_chicken','CN_all','metabolizable_energy_peak',
     2760.0,2720.0,2800.0,'kcal/kg',2023,5,SRC1,
     '產蛋高峰代謝能2760kcal/kg（不低於2680），每天310-320kcal需求'),
    ('layer_chicken','CN_all','crude_protein_peak',
     16.5,16.0,17.0,'%',2023,5,SRC1,
     '產蛋高峰粗蛋白16-17%，可消化賴氨酸不低於0.7%'),
    ('layer_chicken','CN_all','limestone_ratio_peak',
     8.0,7.5,8.5,'%',2023,5,SRC1,
     '產蛋期石粉8%，鈣含量36%以上，補殼關鍵'),
    ('layer_chicken','CN_all','corn_ratio_peak',
     58.0,57.4,58.4,'%',2023,5,SRC1,
     '產蛋期玉米佔比57.4-58.4%'),
    ('layer_chicken','CN_all','soybean_meal_ratio_peak',
     24.0,20.0,28.0,'%',2023,5,SRC1,
     '產蛋期豆粕20-28%（含魚粉配方可用20%）'),
]
for args in layer_nutrition:
    ins(*args)

# ══════════════════════════════════════════════════════
# 5. 肉雞採食量與FCR基準
# ══════════════════════════════════════════════════════
broiler_perf = [
    ('broiler','CN_all','daily_feed_broiler_formula',
     5.0,None,None,'g_per_day_age_based',2023,5,SRC2,
     '白羽肉雞採食量公式：日齡×只數×5g，最大200g/只'),
    ('broiler','CN_all','fcr_broiler_active_flock',
     1.85,1.75,1.91,'kg_feed/kg_gain',2023,5,SRC3,
     '商業雞場平均FCR 1.91，活躍鸡群FCR 1.75-1.85（光流研究）'),
    ('broiler','CN_all','mortality_broiler_active_flock',
     9.56,5.64,17.37,'%',2023,5,SRC3,
     '商業雞場死亡率均值9.56%，FCR與死亡率強相關r=0.698'),
    ('broiler','CN_all','fcr_broiler_activity_correlation',
     -0.326,None,None,'r_value',2023,4,SRC3,
     '鸡群活動性與FCR負相關r=-0.326，更活躍=FCR更低'),
    # 817肉雜雞
    ('broiler','CN_all','daily_feed_817_formula',
     4.5,None,None,'g_per_day_age_based',2023,4,SRC2,
     '817肉雜雞採食量：日齡×只數×0.005，最大100g/只'),
]
for args in broiler_perf:
    ins(*args)

# ══════════════════════════════════════════════════════
# 6. 肉種雞FCR與飼料成本
# ══════════════════════════════════════════════════════
breeder_perf = [
    ('broiler','CN_all','feed_consumption_broiler_breeder_total',
     55.5,None,None,'kg/hen_lifetime',2023,5,SRC1,
     '肉種雞全程耗料55.5kg（育成8.5kg+產蛋47kg），入舍產雛140只'),
    ('broiler','CN_all','feed_cost_per_chick_ratio',
     39.8,None,None,'%_of_chick_price',2023,5,SRC1,
     '種雞飼料成本佔日齡雛雞售價39.8%'),
    ('broiler','CN_all','fcr_improvement_1kg_feed_saving',
     0.725,None,None,'%_chick_cost_reduction',2023,5,SRC1,
     '種雞每減少1kg飼料可節省雛雞成本0.725%'),
]
for args in breeder_perf:
    ins(*args)

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
layer = conn.execute(
    "SELECT COUNT(*) FROM market_kpi WHERE species='layer_chicken'"
).fetchone()[0]
print(f'Done. Inserted: {n}')
print(f'DB total: {total} | layer_chicken: {layer}')
print()
print('=== 蛋雞ROI計算關鍵基準（確認版）===')
print('料蛋比基準：')
print('  海蘭褐優質飼料：2.03（手冊標準）')
print('  中國好雞場：2.1-2.2')
print('  中國差雞場：2.3-2.5')
print('  世界先進：2.0-2.2')
print()
print('日採食量：115g/只（高峰期），東北冬季118g')
print('高峰持續：優質飼料延長2-5天，死淘率降低2%')
print()
print('=== 對肉雞願付計算的修正建議 ===')
print('肉雞FCR=1.85→1.57（改善15%），改善0.28')
print('0.28/0.1 = 2.8個單位')
print('若每降0.1肉雞客戶願付CNY25-35：')
print(f'  WTP = 2.8 × 30 = CNY 84/kg（中間值）')
print('現在設8-12/單位太低，建議改為25-35')
