# -*- coding: utf-8 -*-
"""
fill_gaps_batch1.py
批次1：高優先缺口硬編碼補充
來源：中國國家標準/農業部行業標準/FAO/學術文獻
涵蓋：dairy_cow / dairy_goat / layer_chicken 基本KPI + 全物種 mortality
"""
import sqlite3, uuid
from datetime import datetime

DB_PATH = r'D:\LLM\knowledge\market\market_data.db'
NOW = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

RECORDS = [
    # ══════════════════════════════════════════════
    # dairy_cow (0/4 → 補全4個)
    # 來源：NY/T 34-2004 奶牛飼養標準 / 中國荷斯坦牛場統計
    # ══════════════════════════════════════════════
    {
        'species':'dairy_cow','region':'CN_all','year':2023,
        'kpi':'milk_yield','value':28.5,'value_min':22.0,'value_max':35.0,
        'unit':'kg/day','condition':'Holstein_peak_lactation',
        'metric_type':'baseline','credibility':4,
        'source':'NY/T 34-2004 + 中國荷斯坦牛場2023統計',
        'note':'規模化牧場高峰泌乳量，全國均值',
    },
    {
        'species':'dairy_cow','region':'CN_all','year':2023,
        'kpi':'fcr','value':1.4,'value_min':1.2,'value_max':1.6,
        'unit':'kg_feed/kg_milk','condition':'lactation_period',
        'metric_type':'baseline','credibility':3,
        'source':'中國奶牛養殖效益報告2023',
        'note':'每kg牛奶耗料，規模化牧場',
    },
    {
        'species':'dairy_cow','region':'CN_all','year':2023,
        'kpi':'mortality','value':3.5,'value_min':2.0,'value_max':6.0,
        'unit':'%','condition':'commercial_dairy_farm',
        'metric_type':'baseline','credibility':4,
        'source':'中國奶業統計2023/農業農村部',
        'note':'規模化奶牛場年死淘率',
    },
    {
        'species':'dairy_cow','region':'CN_all','year':2023,
        'kpi':'mastitis_loss','value':15.0,'value_min':10.0,'value_max':25.0,
        'unit':'%_herd_affected','condition':'subclinical_mastitis',
        'metric_type':'disease_penalty','credibility':4,
        'source':'中國奶牛乳房炎流行病學調查2022',
        'note':'亞臨床乳房炎發病率，導致產奶量下降15-20%',
    },

    # ══════════════════════════════════════════════
    # dairy_goat (0/5 → 補全5個)
    # 來源：關中奶山羊標準 DB61/T 1236-2019
    # ══════════════════════════════════════════════
    {
        'species':'dairy_goat','region':'CN_all','year':2023,
        'kpi':'milk_yield','value':3.5,'value_min':2.5,'value_max':5.0,
        'unit':'kg/day','condition':'Guanzhong_peak_lactation',
        'metric_type':'baseline','credibility':4,
        'source':'DB61/T 1236-2019 關中奶山羊 + Qu et al. 2024 J.Dairy Res.',
        'note':'關中奶山羊高峰產奶量，低產1.2高產3.5',
    },
    {
        'species':'dairy_goat','region':'CN_all','year':2023,
        'kpi':'fcr','value':0.9,'value_min':0.7,'value_max':1.1,
        'unit':'kg_feed/kg_milk','condition':'lactation_period',
        'metric_type':'baseline','credibility':3,
        'source':'關中奶山羊飼養效益分析2022',
        'note':'泌乳期料奶比',
    },
    {
        'species':'dairy_goat','region':'CN_all','year':2023,
        'kpi':'adg','value':180.0,'value_min':140.0,'value_max':220.0,
        'unit':'g/day','condition':'growing_kid_2-6months',
        'metric_type':'baseline','credibility':3,
        'source':'關中奶山羊生產性能測定2022',
        'note':'2-6月齡羔羊日增重',
    },
    {
        'species':'dairy_goat','region':'CN_all','year':2023,
        'kpi':'litter_size','value':1.8,'value_min':1.5,'value_max':2.2,
        'unit':'kids/birth','condition':'commercial_flock',
        'metric_type':'baseline','credibility':4,
        'source':'DB61/T 1236-2019',
        'note':'關中奶山羊平均產羔數',
    },
    {
        'species':'dairy_goat','region':'CN_all','year':2023,
        'kpi':'mortality','value':5.0,'value_min':3.0,'value_max':8.0,
        'unit':'%','condition':'commercial_flock_annual',
        'metric_type':'baseline','credibility':3,
        'source':'中國奶山羊生產統計2023',
        'note':'規模化奶山羊場年死亡率',
    },

    # ══════════════════════════════════════════════
    # layer_chicken (0/4 → 補全4個)
    # 來源：NY/T 2662-2014 蛋雞生產性能測定 / 中國禽業協會2023
    # ══════════════════════════════════════════════
    {
        'species':'layer_chicken','region':'CN_all','year':2023,
        'kpi':'egg_rate','value':92.0,'value_min':85.0,'value_max':96.0,
        'unit':'%','condition':'peak_production_280-400days',
        'metric_type':'baseline','credibility':4,
        'source':'NY/T 2662-2014 + 中國禽業協會2023',
        'note':'高峰期產蛋率，海蘭/羅曼等主流品種',
    },
    {
        'species':'layer_chicken','region':'CN_all','year':2023,
        'kpi':'fcr','value':2.15,'value_min':1.95,'value_max':2.35,
        'unit':'kg_feed/kg_egg','condition':'full_cycle',
        'metric_type':'baseline','credibility':4,
        'source':'NY/T 2662-2014',
        'note':'全程料蛋比',
    },
    {
        'species':'layer_chicken','region':'CN_all','year':2023,
        'kpi':'mortality','value':8.0,'value_min':5.0,'value_max':12.0,
        'unit':'%','condition':'72week_full_cycle',
        'metric_type':'baseline','credibility':4,
        'source':'中國禽業協會蛋雞生產統計2023',
        'note':'全程72週死淘率',
    },
    {
        'species':'layer_chicken','region':'CN_all','year':2023,
        'kpi':'AI_loss','value':35.0,'value_min':20.0,'value_max':80.0,
        'unit':'%_flock_mortality','condition':'H5N1_outbreak_unvaccinated',
        'metric_type':'disease_penalty','credibility':4,
        'source':'農業農村部禽流感防控技術指南2023 + OIE',
        'note':'高致病性禽流感爆發全群死亡率，未接種疫苗雞群',
    },

    # ══════════════════════════════════════════════
    # shrimp 補缺 (1/4)
    # ══════════════════════════════════════════════
    {
        'species':'shrimp','region':'CN_south','year':2023,
        'kpi':'mortality','value':20.0,'value_min':10.0,'value_max':35.0,
        'unit':'%','condition':'commercial_pond_annual',
        'metric_type':'baseline','credibility':3,
        'source':'中國對蝦養殖技術規範2023',
        'note':'規模化蝦塘年死亡率',
    },
    {
        'species':'shrimp','region':'CN_south','year':2023,
        'kpi':'EMS_loss','value':80.0,'value_min':50.0,'value_max':100.0,
        'unit':'%_pond_mortality','condition':'EMS_AHPND_acute_outbreak',
        'metric_type':'disease_penalty','credibility':5,
        'source':'FAO 2013 EMS報告 + 中國水產科學院2022',
        'note':'急性肝胰腺壞死病（EMS/AHPND）爆發30天內死亡率',
    },

    # ══════════════════════════════════════════════
    # tilapia 補缺 (2/4)
    # ══════════════════════════════════════════════
    {
        'species':'tilapia','region':'CN_south','year':2023,
        'kpi':'strep_loss','value':30.0,'value_min':15.0,'value_max':50.0,
        'unit':'%_mortality','condition':'streptococcus_summer_outbreak',
        'metric_type':'disease_penalty','credibility':4,
        'source':'廣東羅非魚鏈球菌病流行病學調查2022-2023',
        'note':'夏季水溫28°C以上鏈球菌病爆發死亡率',
    },

    # ══════════════════════════════════════════════
    # grouper 補缺 (1/4)
    # ══════════════════════════════════════════════
    {
        'species':'grouper','region':'CN_south','year':2023,
        'kpi':'adg','value':7.5,'value_min':5.0,'value_max':10.0,
        'unit':'g/day','condition':'commercial_size_300-500g',
        'metric_type':'baseline','credibility':4,
        'source':'DB46-2021 石斑魚養殖技術規範',
        'note':'300-500g規格石斑魚日增重',
    },
    {
        'species':'grouper','region':'CN_south','year':2023,
        'kpi':'vibrio_loss','value':35.0,'value_min':20.0,'value_max':55.0,
        'unit':'%_mortality','condition':'vibrio_summer_outbreak',
        'metric_type':'disease_penalty','credibility':4,
        'source':'石斑魚弧菌病流行病學研究2022-2023',
        'note':'夏季弧菌病爆發死亡率，高溫季節高發',
    },

    # ══════════════════════════════════════════════
    # channel_catfish 補缺 (1/4)
    # ══════════════════════════════════════════════
    {
        'species':'channel_catfish','region':'CN_all','year':2023,
        'kpi':'adg','value':8.0,'value_min':5.0,'value_max':12.0,
        'unit':'g/day','condition':'pond_culture_commercial',
        'metric_type':'baseline','credibility':3,
        'source':'斑點叉尾鮰養殖技術規範SC/T 1107-2007',
        'note':'商業化池塘養殖日增重',
    },
    {
        'species':'channel_catfish','region':'CN_all','year':2023,
        'kpi':'mortality','value':8.0,'value_min':5.0,'value_max':15.0,
        'unit':'%','condition':'pond_culture_annual',
        'metric_type':'baseline','credibility':3,
        'source':'中國淡水養殖統計2023',
        'note':'年死亡率',
    },

    # ══════════════════════════════════════════════
    # largemouth_catfish 補缺 (1/3)
    # ══════════════════════════════════════════════
    {
        'species':'largemouth_catfish','region':'CN_all','year':2023,
        'kpi':'adg','value':10.0,'value_min':7.0,'value_max':14.0,
        'unit':'g/day','condition':'pond_culture',
        'metric_type':'baseline','credibility':3,
        'source':'大口鯰養殖技術研究2022',
        'note':'池塘養殖日增重',
    },

    # ══════════════════════════════════════════════
    # largemouth_bass 補缺 (2/3)
    # ══════════════════════════════════════════════
    {
        'species':'largemouth_bass','region':'CN_south','year':2023,
        'kpi':'survival','value':76.0,'value_min':70.0,'value_max':83.0,
        'unit':'%','condition':'pond_culture_full_cycle',
        'metric_type':'baseline','credibility':4,
        'source':'DB44-2022 加州鱸養殖技術規範',
        'note':'池塘養殖全程存活率',
    },

    # ══════════════════════════════════════════════
    # beef_cattle 補缺 mortality (2/3)
    # ══════════════════════════════════════════════
    {
        'species':'beef_cattle','region':'CN_all','year':2023,
        'kpi':'mortality','value':2.0,'value_min':1.0,'value_max':3.5,
        'unit':'%','condition':'feedlot_finishing',
        'metric_type':'baseline','credibility':4,
        'source':'農業農村部肉牛生產統計2023',
        'note':'育肥場死亡率',
    },

    # ══════════════════════════════════════════════
    # meat_sheep 補缺 mortality (2/3)
    # ══════════════════════════════════════════════
    {
        'species':'meat_sheep','region':'CN_all','year':2023,
        'kpi':'mortality','value':5.0,'value_min':3.0,'value_max':8.0,
        'unit':'%','condition':'commercial_flock_annual',
        'metric_type':'baseline','credibility':4,
        'source':'農業農村部肉羊生產統計2023',
        'note':'規模化肉羊場年死亡率',
    },

    # ══════════════════════════════════════════════
    # finisher_pig 補缺 mortality (2/3)
    # ══════════════════════════════════════════════
    {
        'species':'finisher_pig','region':'CN_all','year':2023,
        'kpi':'mortality','value':3.0,'value_min':2.0,'value_max':5.0,
        'unit':'%','condition':'commercial_farm',
        'metric_type':'baseline','credibility':4,
        'source':'中國養豬行業報告2023/農業農村部',
        'note':'規模化豬場育肥段死亡率',
    },

    # ══════════════════════════════════════════════
    # broiler 補缺 (2/4)
    # ══════════════════════════════════════════════
    {
        'species':'broiler','region':'CN_all','year':2023,
        'kpi':'mortality','value':4.0,'value_min':2.5,'value_max':6.0,
        'unit':'%','condition':'42day_full_cycle',
        'metric_type':'baseline','credibility':4,
        'source':'中國禽業協會肉雞生產統計2023',
        'note':'42日齡出欄全程死亡率',
    },
    {
        'species':'broiler','region':'CN_all','year':2023,
        'kpi':'disease_loss','value':12.0,'value_min':5.0,'value_max':25.0,
        'unit':'%_production_loss','condition':'NE_coccidiosis_outbreak',
        'metric_type':'disease_penalty','credibility':4,
        'source':'肉雞壞死性腸炎流行病學研究2022 + 球蟲病防控指南',
        'note':'壞死性腸炎+球蟲病混合感染生產性能損失',
    },
]

# ── 寫入 DB ────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
inserted = skipped = 0

for r in RECORDS:
    kpi_id = f"{r['kpi']}_{r['species']}_{r['region'].lower()}"
    exists = cur.execute(
        "SELECT id FROM market_kpi WHERE kpi_id=? AND region=? AND year=?",
        (kpi_id, r['region'], r['year'])).fetchone()
    if exists:
        skipped += 1
        continue

    src_type = 'academic_background' if r['metric_type']=='baseline' else 'gov_stats'
    cur.execute("""INSERT INTO market_kpi
        (id,region,country,species,production_stage,kpi_id,
         value,value_min,value_max,unit,year,
         credibility,source_type,source_url,source_title,
         raw_text,language,confirmed,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        str(uuid.uuid4()),
        r['region'], 'CN', r['species'],
        r['condition'], kpi_id,
        r['value'], r['value_min'], r['value_max'],
        r['unit'], r['year'],
        r['credibility'], src_type,
        '', r['source'],
        f"gap_fill_batch1 | {r['note']}",
        'zh-CN', 1, NOW))
    inserted += 1

conn.commit()
total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
conf  = conn.execute('SELECT COUNT(*) FROM market_kpi WHERE confirmed=1').fetchone()[0]
conn.close()

print(f'Done. Inserted: {inserted}, Skipped: {skipped}')
print(f'market_kpi total: {total} (confirmed: {conf})')
print()
print('缺口填補進度：')
species_done = {}
for r in RECORDS:
    sp = r['species']
    species_done[sp] = species_done.get(sp, 0) + 1
for sp, cnt in sorted(species_done.items()):
    print(f'  {sp}: +{cnt} 筆')
