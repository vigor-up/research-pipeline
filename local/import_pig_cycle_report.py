# -*- coding: utf-8 -*-
"""
import_pig_cycle_report.py
來源：猪周期四维重构深度研究 2026
微信公眾號：造价木兰投资经
關鍵數據提取寫入DB + RAGFlow知識庫準備
"""
import sqlite3, uuid
from datetime import datetime

DB_PATH = r'D:\LLM\knowledge\market\market_data.db'
NOW  = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
YEAR = 2026
SOURCE = '猪周期四维重构深度研究 造价木兰投资经 2026'
URL    = 'https://mp.weixin.qq.com/s/av3Y-HiYvlLBiV-MKueAqg'

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
        URL, SOURCE, raw, 'zh-CN', 1, NOW))
    return 1

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
n = 0

# ══════════════════════════════════════════════════════
# 1. 競品成本結構（對ROI銷售最關鍵）
# ══════════════════════════════════════════════════════
cost_data = [
    # 牧原成本
    ('finisher_pig','CN_all','competitor_cost_muyuan_full',
     11.6,'CNY/kg',5,'牧原2026Q1完全成本11.6元/kg，行業最低'),
    ('finisher_pig','CN_all','competitor_cost_muyuan_cash',
     10.06,'CNY/kg',5,'牧原現金成本10.06元/kg（含折舊13.2%）'),
    # 頭部企業均值
    ('finisher_pig','CN_all','competitor_cost_top_avg',
     12.65,'CNY/kg',5,'頭部企業溫氏/新希望完全成本12.4-12.9元/kg'),
    # 散戶成本
    ('finisher_pig','CN_all','farm_cost_small_holder',
     17.0,'CNY/kg',5,'散戶成本16-18元/kg，與頭部差4元/kg'),
    # 頭均虧損（2026Q2）
    ('finisher_pig','CN_all','loss_per_head_2026q2',
     375.0,'CNY/head',5,'自繁自養頭均虧損300-450元，超歷史底部'),
]
for sp, reg, kid, val, unit, cred, note in cost_data:
    n += ins(cur, reg, sp, 'cost_structure', kid, val, unit, cred, note)

# ══════════════════════════════════════════════════════
# 2. 生豬價格歷史數據（週期分析用）
# ══════════════════════════════════════════════════════
price_history = [
    ('finisher_pig','CN_all','pig_price_2026jan',  12.1,'CNY/kg',5,'2026年1月均價'),
    ('finisher_pig','CN_all','pig_price_2026feb',   9.8,'CNY/kg',5,'2026年2月均價'),
    ('finisher_pig','CN_all','pig_price_2026mar',   9.1,'CNY/kg',5,'2026年3月均價，2018年以來同期最低'),
    ('finisher_pig','CN_all','pig_price_2026apr',   8.8,'CNY/kg',5,'2026年4月，歷史新低，部分地區3.5元/斤'),
    ('finisher_pig','CN_all','pig_price_2025avg',  14.0,'CNY/kg',5,'2025年全年均價，同比-17%'),
    ('finisher_pig','CN_all','pig_price_2024avg',  14.17,'CNY/kg',5,'2024年全年均價，同比+12%'),
    ('finisher_pig','CN_all','pig_price_2020peak', 52.0,'CNY/kg',5,'2020年7月峰值，非洲豬瘟後歷史最高'),
    ('finisher_pig','CN_all','pig_price_breakeven_top',  12.65,'CNY/kg',5,'頭部企業盈虧平衡點'),
    ('finisher_pig','CN_all','pig_price_breakeven_small', 17.0,'CNY/kg',5,'散戶盈虧平衡點'),
]
for sp, reg, kid, val, unit, cred, note in price_history:
    yr = int(kid.split('_')[-1][:4]) if kid.split('_')[-1][:4].isdigit() else YEAR
    if not cur.execute("SELECT id FROM market_kpi WHERE kpi_id=?", (kid,)).fetchone():
        cur.execute("""INSERT INTO market_kpi
            (id,region,country,species,production_stage,kpi_id,
             value,unit,year,credibility,source_type,
             source_url,source_title,raw_text,language,confirmed,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            str(uuid.uuid4()), reg, 'CN', sp, 'price_history', kid,
            val, unit, yr, cred, 'industry_media',
            URL, SOURCE, note, 'zh-CN', 1, NOW))
        n += 1

# ══════════════════════════════════════════════════════
# 3. 產業結構數據
# ══════════════════════════════════════════════════════
industry_data = [
    ('finisher_pig','CN_all','market_concentration_top20_2025',
     36.0,'%_market_share',5,'TOP20企業市占率36%，同比+5個百分點'),
    ('finisher_pig','CN_all','market_concentration_top10_2025',
     30.0,'%_market_share',5,'TOP10企業市占率30%'),
    ('finisher_pig','CN_all','scale_farm_ratio_2025',
     70.0,'%_of_total',5,'規模場佔比70%以上，散戶降至30%以下'),
    ('finisher_pig','CN_all','psy_industry_avg_2026',
     26.34,'piglets/sow/year',5,'行業PSY 2026年3月26.34頭，2019年前16.1頭'),
    ('finisher_pig','CN_all','psy_muyuan_2026',
     32.0,'piglets/sow/year',5,'牧原PSY 32頭以上，頂級水準'),
    ('finisher_pig','CN_all','breeding_sow_target_2026',
     3650.0,'万头',5,'2026年能繁母豬調控目標3650萬頭，較3961萬降7.8%'),
    ('finisher_pig','CN_all','annual_slaughter_2025',
     70000.0,'万头',5,'2025年全國生豬出欄7億頭以上'),
    ('finisher_pig','CN_all','pork_consumption_share_2025',
     57.9,'%_of_meat',5,'豬肉佔肉類消費57.9%，2018年62.1%下降'),
    ('finisher_pig','CN_all','per_capita_pork_2025',
     26.6,'kg/person/year',5,'2025年人均豬肉消費26.6kg，同比-5.4%，連續2年下跌'),
]
for sp, reg, kid, val, unit, cred, note in industry_data:
    n += ins(cur, reg, sp, 'industry_structure', kid, val, unit, cred, note)

# ══════════════════════════════════════════════════════
# 4. 飼料成本結構（配方師最關心）
# ══════════════════════════════════════════════════════
feed_data = [
    ('finisher_pig','CN_all','feed_cost_ratio_in_total',
     70.0,'%_of_total_cost',5,'飼料佔養殖總成本60-80%'),
    ('finisher_pig','CN_all','corn_ratio_in_feed',
     60.0,'%_of_feed',5,'玉米佔豬飼料60%'),
    ('finisher_pig','CN_all','soybean_meal_ratio_industry_avg',
     14.5,'%_of_feed',5,'行業豆粕均值14.5%，牧原僅7.3%'),
    ('finisher_pig','CN_all','soybean_meal_ratio_muyuan',
     7.3,'%_of_feed',5,'牧原低蛋白日糧豆粕僅7.3%，比行業少一半'),
    ('finisher_pig','CN_all','corn_price_impact_on_cost',
     0.45,'%_cost_increase_per_1pct_corn_rise',5,
     '玉米價格每漲1%，養殖總成本漲0.4-0.5%'),
    ('finisher_pig','CN_all','corn_soybean_price_yoy_2026',
     20.0,'%_increase_yoy',4,'2026年玉米豆粕同比漲約20%，推高成本線'),
    ('finisher_pig','CN_all','biosecurity_cost_per_head',
     200.0,'CNY/head',5,'非瘟後防疫成本每頭200元以上，非瘟前40元'),
    ('finisher_pig','CN_all','labor_cost_per_head_2025',
     120.0,'CNY/head',4,'頭部企業人工成本約100-120元/頭'),
]
for sp, reg, kid, val, unit, cred, note in feed_data:
    n += ins(cur, reg, sp, 'feed_cost', kid, val, unit, cred, note)

# ══════════════════════════════════════════════════════
# 5. ROI銷售話術支撐數據
# ══════════════════════════════════════════════════════
roi_support = [
    ('finisher_pig','CN_all','roi_context_smallholder_pain',
     375.0,'CNY/head',5,
     '2026Q2散戶頭均虧損375元，FCR改善可直接抵消部分虧損'),
    ('finisher_pig','CN_all','roi_context_cost_gap_vs_top',
     4.0,'CNY/kg',5,
     '散戶vs頭部成本差4元/kg，一頭豬差500元，添加劑是縮差工具'),
    ('finisher_pig','CN_all','roi_context_cycle_bottom_2026',
     1.0,'is_bottom_zone',5,
     '2026Q2豬價歷史新低，底部降本比任何時期ROI更高'),
    ('finisher_pig','CN_all','roi_context_feed_cost_share',
     70.0,'%_of_total',5,
     '飼料70%成本佔比：FCR改善=最直接降本路徑，配方師最有說服力的切入點'),
]
for sp, reg, kid, val, unit, cred, note in roi_support:
    n += ins(cur, reg, sp, 'roi_context', kid, val, unit, cred, note)

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
print(f'Done. Inserted: {n}')
print(f'DB total: {total}')
print()
print('=== ROI銷售話術關鍵數字 ===')
print('• 散戶頭均虧損 375元 → FCR改善115元/頭 = 直接補回30%虧損')
print('• 競品牧原成本 11.6元/kg → 你的客戶散戶成本 17元/kg')
print('• 成本差4元/kg × 80kg增重 = 320元/頭差距')
print('• 你的產品幫客戶縮差 → 這才是底部期最強銷售邏輯')
print()
print('=== 配方師話術框架 ===')
print('問：現在豬價這麼低，還要買添加劑？')
print('答：正因為虧損，FCR改善的ROI是漲價期的3倍')
print('    牧原11.6元/kg vs 你的客戶17元/kg')
print('    差距就是飼料效率，這是唯一不依賴豬價的確定性收益')
