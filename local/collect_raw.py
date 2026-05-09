# -*- coding: utf-8 -*-
"""
collect_raw.py
GitHub Actions 專用：搜尋 + 爬蟲 + 存 R2
不依賴本地模型，純 API + Crawl4AI
結果存 R2 raw/YYYY-MM-DD/ 供 EVO-X2 Qwen3.6 處理
"""
import json, time, logging, requests, hashlib, re, asyncio, os, sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ── Keys（GitHub Secrets）────────────────────────────────
TAVILY_KEY           = os.environ.get('TAVILY_API_KEY', '')
FIRECRAWL_KEY        = os.environ.get('FIRECRAWL_API_KEY', 'fc-f1b23a25854a4c96aa56acb89c65e930')
SEMANTIC_SCHOLAR_KEY = os.environ.get('SEMANTIC_SCHOLAR_KEY', 's2k-8Zr1tg8DeqJiJKwD7U5ip0QK9pijy04E7lHXIKfc')
TELEGRAM_TOKEN       = os.environ.get('TELEGRAM_TOKEN', '8703702788:AAFKEiGmLYTAuFVG9GX-gRtVTUUyi-f_5mM')
TELEGRAM_CHAT        = int(os.environ.get('TELEGRAM_CHAT_ID', '897274134'))
R2_ENDPOINT          = 'https://adb1040c847f4ae4a7d6bfedcccd7b77.r2.cloudflarestorage.com'
R2_ACCESS_KEY        = os.environ.get('R2_ACCESS_KEY_ID', 'f443b2e5acc77dd1af6a83a5d548b35b')
R2_SECRET_KEY        = os.environ.get('R2_SECRET_ACCESS_KEY', 'da1c377ffbc03b865504e292480e0e2806ddb84a61bf87b7e6a2066632a4a357')
R2_BUCKET            = 'richtrong-collect'

SLEEP_QUERY = 4
MAX_RESULTS_PER_QUERY = 5

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s')

# ── 搜尋目標 ──────────────────────────────────────────────
SEARCH_TARGETS = [
    # ── 豬 ──────────────────────────────────────────
    ('finisher_pig',  'CN_northeast', ['饲料转化率', '料肉比', '日增重', '死亡率']),
    ('finisher_pig',  'CN_north',     ['饲料转化率', '料肉比', '日增重', '死亡率']),
    ('finisher_pig',  'CN_south',     ['饲料转化率', '料肉比', '日增重', '死亡率']),
    ('finisher_pig',  'CN_central',   ['饲料转化率', '料肉比', '日增重', '死亡率']),
    ('finisher_pig',  'CN_east',      ['饲料转化率', '料肉比', '日增重']),
    ('finisher_pig',  'SEA_vietnam',  ['饲料转化率', '料肉比', '日增重']),
    ('finisher_pig',  'SEA_malaysia', ['饲料转化率', '料肉比', '日增重']),
    ('breeding_sow',  'CN_northeast', ['窝产仔数', '分娩率', '断奶成活率', '死亡率']),
    ('breeding_sow',  'CN_north',     ['窝产仔数', '分娩率', '断奶成活率']),
    ('breeding_sow',  'CN_south',     ['窝产仔数', '分娩率']),
    ('piglet',        'CN_northeast', ['日增重', '死亡率', '断奶成活率']),
    ('piglet',        'CN_north',     ['日增重', '死亡率', '断奶成活率']),
    ('boar',          'CN_all',       ['受胎率', '配种妊娠率']),
    # ── 雞 ──────────────────────────────────────────
    ('broiler',       'CN_northeast', ['饲料转化率', '料肉比', '日增重', '出栏体重', '死亡率']),
    ('broiler',       'CN_north',     ['饲料转化率', '料肉比', '日增重']),
    ('broiler',       'CN_south',     ['饲料转化率', '料肉比', '日增重', '死亡率']),
    ('broiler',       'SEA_vietnam',  ['饲料转化率', '料肉比', '日增重']),
    ('broiler',       'SEA_malaysia', ['饲料转化率', '料肉比', '日增重']),
    ('broiler',       'SEA_thailand', ['饲料转化率', '日增重']),
    ('broiler',       'SEA_indonesia',['饲料转化率', '日增重']),
    ('layer_chicken', 'CN_northeast', ['产蛋率', '饲料转化率', '蛋重', '死亡率', '高峰产蛋率']),
    ('layer_chicken', 'CN_north',     ['产蛋率', '饲料转化率', '蛋重', '死亡率']),
    ('layer_chicken', 'CN_south',     ['产蛋率', '饲料转化率', '蛋重']),
    ('layer_chicken', 'CN_east',      ['产蛋率', '饲料转化率']),
    ('layer_chicken', 'SEA_malaysia', ['产蛋率', '饲料转化率']),
    # ── 鴨 ──────────────────────────────────────────
    ('duck',          'CN_south',     ['饲料转化率', '日增重', '死亡率']),
    ('duck',          'CN_east',      ['饲料转化率', '日增重', '死亡率']),
    # ── 鵝 ──────────────────────────────────────────
    ('goose',         'CN_south',     ['饲料转化率', '日增重', '死亡率']),
    ('goose',         'CN_east',      ['饲料转化率', '日增重']),
    # ── 牛 ──────────────────────────────────────────
    ('beef_cattle',   'CN_northeast', ['饲料转化率', '日增重', '屠宰率', '死亡率']),
    ('beef_cattle',   'CN_north',     ['饲料转化率', '日增重', '屠宰率']),
    ('beef_cattle',   'CN_southwest', ['饲料转化率', '日增重']),
    ('beef_cattle',   'SEA_malaysia', ['饲料转化率', '日增重']),
    ('beef_cattle',   'SEA_vietnam',  ['饲料转化率', '日增重']),
    ('dairy_cow',     'CN_northeast', ['产奶量', '乳脂率', '乳蛋白率', '体细胞数']),
    ('dairy_cow',     'CN_north',     ['产奶量', '乳脂率', '乳蛋白率']),
    # ── 羊 ──────────────────────────────────────────
    ('meat_sheep',    'CN_northeast', ['饲料转化率', '日增重', '屠宰率', '死亡率']),
    ('meat_sheep',    'CN_northwest', ['饲料转化率', '日增重', '屠宰率']),
    ('meat_sheep',    'CN_north',     ['饲料转化率', '日增重']),
    ('meat_goat',     'CN_south',     ['饲料转化率', '日增重', '死亡率']),
    ('dairy_goat',    'CN_all',       ['产奶量', '饲料转化率']),
    # ── 水產 ────────────────────────────────────────
    ('shrimp',        'CN_south',     ['存活率', '饲料转化率', '特定生长率', '死亡率']),
    ('shrimp',        'SEA_thailand', ['存活率', '饲料转化率', '特定生长率']),
    ('shrimp',        'SEA_vietnam',  ['存活率', '饲料转化率']),
    ('shrimp',        'SEA_malaysia', ['存活率', '饲料转化率']),
    ('shrimp',        'SEA_indonesia',['存活率', '饲料转化率']),
    ('tilapia',       'CN_south',     ['饲料转化率', '日增重', '存活率']),
    ('tilapia',       'SEA_thailand', ['饲料转化率', '日增重', '存活率']),
    ('grass_carp',    'CN_south',     ['饲料转化率', '日增重', '存活率']),
    ('grouper',       'CN_south',     ['饲料转化率', '日增重', '存活率']),
    ('largemouth_bass','CN_south',    ['饲料转化率', '日增重', '存活率']),
    ('channel_catfish','CN_all',      ['饲料转化率', '日增重', '存活率']),
    # ── 兔 ──────────────────────────────────────────
    ('rabbit',        'CN_all',       ['饲料转化率', '日增重', '死亡率']),
]

# 核心原料論文查詢（機密，對外屏蔽）
INGREDIENT_QUERIES = [
    # ══════════════════════════════════════════════════
    # 多二十烷醇（Policosanol）C24-C32 長鏈烷醇系列
    # ══════════════════════════════════════════════════

    # 多二十烷醇（Policosanol）三語
    '多二十烷醇 肉鸡 饲料转化率 生长性能 试验',          # 簡體
    '多二十烷醇 蛋鸡 产蛋率 蛋品质 饲养试验',
    '多二十烷醇 育肥猪 料肉比 日增重 试验',
    '多二十烷醇 肉牛 饲料转化率 日增重 试验',
    '多二十烷醇 对虾 存活率 生长性能',
    '多二十烷醇 肉羊 饲料转化率 日增重',
    '蜂蜡醇 家禽 生长性能 饲料报酬 试验',
    '混合长链醇 畜禽 生产性能 饲养试验',
    '多廿烷醇 肉雞 飼料轉化率 生長性能 試驗',           # 繁體
    '多廿烷醇 蛋雞 產蛋率 蛋品質 飼養試驗',
    '多廿烷醇 育肥豬 料肉比 日增重 試驗',
    '多廿烷醇 肉牛 飼料轉化率 日增重',
    '多廿烷醇 對蝦 存活率 生長',
    'policosanol poultry FCR growth performance trial 2023 2024',  # 英文
    'policosanol broiler feed conversion ratio body weight gain',
    'policosanol laying hen egg production rate performance',
    'policosanol swine pig growth performance feed conversion',
    'policosanol cattle beef ADG feed efficiency trial',
    'policosanol shrimp aquaculture survival FCR growth',
    'policosanol sheep lamb growth performance experiment',
    'policosanol Vietnam Malaysia Thailand Indonesia livestock trial',
    'policosanol long chain alcohol poultry swine review 2024',

    # 二十四烷醇（Tetracosanol, C24）三語
    '二十四烷醇 畜禽 生产性能 饲料转化率 试验',          # 簡體
    '24烷醇 家禽 生长 饲料报酬',
    '二十四烷醇 畜禽 生產性能 飼料轉化率',               # 繁體
    'tetracosanol poultry livestock growth performance trial',     # 英文
    'tetracosanol C24 alcohol feed efficiency experiment',

    # 二十五烷醇（Pentacosanol, C25）三語
    '二十五烷醇 畜禽 生产性能 饲养试验',                 # 簡體
    '25烷醇 家禽 生长 饲料转化率 试验',
    '二十五烷醇 畜禽 生產性能 飼養試驗',                 # 繁體
    '二十五烷醇 家禽 生長 飼料轉化率',
    'pentacosanol poultry livestock performance trial',            # 英文
    'pentacosanol C25 alcohol feed conversion growth experiment',

    # 二十六烷醇（Hexacosanol, C26）三語
    '二十六烷醇 家禽 饲料转化率 生长性能',               # 簡體
    '26烷醇 畜禽 生产性能 试验',
    '二十六烷醇 家禽 飼料轉化率 生長性能',               # 繁體
    'hexacosanol poultry feed conversion growth trial',            # 英文
    'hexacosanol C26 alcohol livestock performance',

    # 二十七烷醇（Heptacosanol, C27）三語
    '二十七烷醇 畜禽 生长性能 试验',                     # 簡體
    '27烷醇 家禽 饲料转化率',
    '二十七烷醇 畜禽 生長性能 試驗',                     # 繁體
    'heptacosanol poultry livestock growth performance',           # 英文
    'heptacosanol C27 alcohol feed efficiency trial',

    # 二十八烷醇（Octacosanol, C28）三語
    '二十八烷醇 育肥猪 料肉比 生长性能 饲养试验',        # 簡體
    '正二十八烷醇 肉鸡 饲料转化率 试验',
    '二十八烷醇 蛋鸡 产蛋率 蛋壳质量 试验',
    '28烷醇 畜禽 生产性能 饲料报酬',
    '二十八碳醇 育肥豬 料肉比 生長性能 飼養試驗',        # 繁體
    '二十八碳醇 肉雞 飼料轉化率 試驗',
    '二十八碳醇 蛋雞 產蛋率 蛋殼品質',
    'octacosanol swine pig feed conversion ratio experiment',      # 英文
    'octacosanol poultry broiler growth performance trial',
    'octacosanol laying hen egg production eggshell quality',
    'octacosanol C28 alcohol livestock feed efficiency',

    # 二十九烷醇（Nonacosanol, C29）三語
    '二十九烷醇 畜禽 饲养试验 生长性能',                 # 簡體
    '29烷醇 家禽 生产性能',
    '二十九烷醇 畜禽 飼養試驗 生長性能',                 # 繁體
    'nonacosanol poultry livestock performance trial',             # 英文
    'nonacosanol C29 alcohol feed conversion growth',

    # 三十烷醇（Triacontanol, C30）三語
    '三十烷醇 畜禽 生长性能 饲料转化率 试验',            # 簡體
    '蜂花醇 家禽 生产性能 饲养试验',
    '30烷醇 猪 肉鸡 日增重 料肉比',
    '三十烷醇 畜禽 生長性能 飼料轉化率 試驗',            # 繁體
    '蜂花醇 家禽 生產性能 飼養試驗',
    'triacontanol poultry broiler growth feed conversion trial',   # 英文
    'triacontanol swine pig performance experiment',
    'triacontanol C30 alcohol livestock FCR ADG',

    # 三十一烷醇（Hentriacontanol, C31）三語
    '三十一烷醇 畜禽 生产性能 试验',                     # 簡體
    '31烷醇 家禽 生长 饲料转化率',
    '三十一烷醇 畜禽 生產性能 試驗',                     # 繁體
    'hentriacontanol poultry livestock performance trial',         # 英文
    'hentriacontanol C31 alcohol feed efficiency growth',

    # 三十二烷醇（Dotriacontanol, C32）三語
    '三十二烷醇 畜禽 生长性能 蜂蜡醇 试验',              # 簡體
    '32烷醇 蜂蜡醇 家禽 生产性能',
    '三十二烷醇 畜禽 生長性能 試驗',                     # 繁體
    'dotriacontanol poultry livestock performance trial',          # 英文
    'dotriacontanol C32 alcohol feed conversion growth experiment',

    # 通用長鏈烷醇
    'long chain fatty alcohol C24 C32 poultry livestock performance',
    'long chain aliphatic alcohol swine FCR growth trial',
    'very long chain alcohol livestock feed efficiency review',
    '長鏈脂肪醇 畜禽 生產性能 飼料轉化率',               # 繁體
    '长链脂肪醇 畜禽 生产性能 饲料转化率',               # 簡體

    # ══════════════════════════════════════════════════
    # 虾青素（Astaxanthin）三語
    # ══════════════════════════════════════════════════
    '虾青素 南美白对虾 存活率 生长性能 饲养试验',        # 簡體
    '虾青素 肉鸡 抗氧化 生产性能 饲料转化率',
    '虾青素 蛋鸡 蛋黄颜色 产蛋率 蛋品质',
    '虾青素 罗非鱼 石斑鱼 鲈鱼 生长存活',
    '虾青素 草鱼 鲤鱼 生长性能 存活率',
    '雨生红球藻提取物 水产 存活率 生长性能',
    '天然虾青素 对虾 抗病力 存活率 东南亚',
    '蝦青素 南美白對蝦 存活率 生長性能 飼養試驗',       # 繁體
    '蝦青素 肉雞 抗氧化 生產性能 飼料轉化率',
    '蝦青素 蛋雞 蛋黃顏色 產蛋率 蛋品質',
    '蝦青素 水產 存活率 生長 抗病力',
    'astaxanthin shrimp FCR survival growth trial 2024 2025',     # 英文
    'astaxanthin broiler antioxidant growth performance FCR',
    'astaxanthin laying hen egg quality yolk color pigmentation',
    'astaxanthin aquaculture tilapia grouper bass survival',
    'astaxanthin grass carp carp growth performance trial',
    'astaxanthin Southeast Asia shrimp aquaculture trial Vietnam Thailand',
    'astaxanthin immune response disease resistance shrimp',
    'natural astaxanthin Haematococcus pluvialis poultry aquaculture',

    # ══════════════════════════════════════════════════
    # 胆碱稳定原硅酸（ch-OSA）三語
    # ══════════════════════════════════════════════════
    '胆碱稳定原硅酸 蛋鸡 蛋壳质量 蛋壳强度 哈氏单位',   # 簡體
    '胆碱稳定原硅酸 家禽 骨骼强度 胫骨灰分 生产性能',
    '有机硅 蛋鸡 蛋品质 蛋壳 产蛋率',
    '生物活性硅 畜禽 骨骼 生长性能 试验',
    '胆碱稳定原硅酸 奶牛 蹄健康 产奶量 体细胞数',
    '胆碱稳定原硅酸 肉鸡 胫骨强度 生长性能',
    '膽鹼矽酸 蛋雞 蛋殼品質 蛋殼強度 哈氏單位',        # 繁體
    '膽鹼矽酸 家禽 骨骼強度 脛骨灰分',
    '膽鹼矽酸 奶牛 蹄健康 產乳量',
    '有機矽 蛋雞 蛋品質 蛋殼 產蛋率',
    'choline stabilized orthosilicic acid laying hen eggshell quality strength', # 英文
    'ch-OSA poultry bone tibia ash strength performance trial',
    'orthosilicic acid broiler tibia strength growth FCR',
    'ch-OSA dairy cow hoof health milk yield SCC',
    'bioavailable silicon poultry livestock bone eggshell trial',
    'ch-OSA pig swine bone growth performance experiment',

    # ══════════════════════════════════════════════════
    # 主要疾病（豬）三語
    # ══════════════════════════════════════════════════
    '猪蓝耳病 PRRS 发病率 死亡率 生产性能 损失',         # 簡體
    '猪圆环病毒 PCV2 生长迟缓 死亡率 饲养损失',
    '猪流行性腹泻 PED 仔猪 死亡率 发病率 2024',
    '非洲猪瘟 ASF 复养 生产性能 恢复 中国',
    '猪气喘病 支原体肺炎 生长性能 饲料转化率 影响',
    '猪伪狂犬病 PRV 繁殖障碍 死亡率 损失',
    '仔猪断奶腹泻 大肠杆菌 死亡率 生长迟缓',
    '猪口蹄疫 FMD 死亡率 生长影响',
    '猪蓝耳病 PRRS 發病率 死亡率 生產性能 損失',        # 繁體
    '豬圓環病毒 PCV2 生長遲緩 死亡率',
    '豬流行性腹瀉 PED 仔豬 死亡率',
    '非洲豬瘟 ASF 復養 生產性能 中國',
    'PRRS porcine reproductive respiratory syndrome production loss mortality 2024', # 英文
    'PCV2 porcine circovirus growth performance mortality China',
    'PED porcine epidemic diarrhea piglet mortality 2024',
    'African swine fever ASF recovery restocking China production',
    'Mycoplasma pneumonia pig growth performance FCR impact',
    'swine influenza pig production loss mortality Southeast Asia',

    # ── 主要疾病（雞）三語 ────────────────────────────
    '鸡新城疫 ND 死亡率 产蛋率下降 生产损失',            # 簡體
    '禽流感 AI H5N1 H7N9 发病率 死亡率 中国 2024',
    '传染性支气管炎 IB 蛋鸡 产蛋率 蛋壳质量 影响',
    '马立克氏病 MD 肉鸡 死亡率 生长性能 淘汰率',
    '鸡球虫病 肉鸡 饲料转化率 日增重 死亡率 影响',
    '鸡白痢 沙门氏菌 雏鸡 死亡率 生长迟缓',
    '禽白血病 ALV 蛋鸡 产蛋率 淘汰率 损失',
    '传染性法氏囊病 IBD 肉鸡 免疫 死亡率',
    '鸡传染性喉气管炎 ILT 死亡率 生产性能',
    '雞新城疫 ND 死亡率 產蛋率下降 生產損失',           # 繁體
    '禽流感 AI 發病率 死亡率 台灣 東南亞 2024',
    '傳染性支氣管炎 IB 蛋雞 產蛋率 蛋殼品質',
    '馬立克氏病 MD 肉雞 死亡率 生長性能',
    '雞球蟲病 肉雞 飼料轉化率 日增重 影響',
    'Newcastle disease ND poultry mortality production loss Asia 2024',  # 英文
    'avian influenza AI H5N1 broiler layer mortality Southeast Asia 2024',
    'infectious bronchitis IB laying hen egg production eggshell',
    'Marek disease MD broiler mortality growth performance',
    'coccidiosis broiler FCR growth performance mortality impact',
    'Salmonella pullorum chick mortality growth depression',
    'infectious bursal disease IBD broiler immunity mortality',
    'avian leukosis ALV layer egg production mortality loss',

    # ── 主要疾病（水產）三語 ──────────────────────────
    '对虾白斑综合征 WSSV 死亡率 存活率 损失 东南亚',     # 簡體
    '对虾急性肝胰腺坏死病 AHPND EMS 死亡率 越南 泰国',
    '对虾桃拉综合征 TSV 存活率 发病率 越南 泰国',
    '对虾传染性皮下及造血组织坏死病 IHHNV 生长影响',
    '罗非鱼链球菌病 死亡率 生长性能 损失',
    '草鱼出血病 GCHV 死亡率 养殖损失',
    '石斑鱼神经坏死病毒 VNN 死亡率 存活率',
    '鲤鱼疱疹病毒病 KHV 死亡率 中国',
    '對蝦白斑綜合症 WSSV 死亡率 存活率 東南亞',         # 繁體
    '對蝦急性肝胰腺壞死病 AHPND EMS 死亡率',
    '對蝦桃拉綜合症 TSV 存活率 越南 泰國',
    '羅非魚鏈球菌病 死亡率 生長性能',
    'white spot syndrome WSSV shrimp mortality survival Vietnam Thailand Malaysia', # 英文
    'AHPND EMS acute hepatopancreatic necrosis shrimp mortality 2024',
    'Taura syndrome TSV shrimp survival Southeast Asia',
    'IHHNV shrimp growth retardation mortality aquaculture',
    'tilapia streptococcosis mortality production loss Asia',
    'grass carp hemorrhage GCHV mortality production loss China',
    'grouper viral nervous necrosis VNN mortality survival',
    'koi herpesvirus KHV carp mortality China aquaculture',
    'shrimp disease mortality production loss Malaysia Indonesia Thailand 2024',

    # ── 主要疾病（牛羊）三語 ──────────────────────────
    '肉牛口蹄疫 FMD 生长性能 死亡率 影响 中国',          # 簡體
    '奶牛乳房炎 产奶量损失 体细胞数 发病率',
    '奶牛蹄叶炎 蹄病 淘汰率 产奶量 损失',
    '牛病毒性腹泻 BVD 生长性能 死亡率',
    '肉羊小反刍兽疫 PPR 死亡率 中国 东南亚',
    '肉羊口蹄疫 FMD 生长性能 死亡率',
    '奶山羊乳房炎 产奶量 体细胞数',
    '肉牛口蹄疫 FMD 生長性能 死亡率 影響',              # 繁體
    '乳牛乳房炎 產乳量損失 體細胞數',
    '肉羊小反芻獸疫 PPR 死亡率 東南亞',
    'bovine respiratory disease BRD cattle mortality FCR growth', # 英文
    'foot and mouth disease FMD cattle growth performance loss',
    'mastitis dairy cow milk yield loss SCC incidence China',
    'laminitis hoof disease dairy cow culling milk yield',
    'bovine viral diarrhea BVD cattle growth mortality',
    'peste des petits ruminants PPR sheep goat mortality China',

    # ══════════════════════════════════════════════════
    # 東南亞市場報告（三語擴充）
    # ══════════════════════════════════════════════════
    'Vietnam livestock poultry swine production statistics 2024 2025',   # 英文
    'Vietnam shrimp aquaculture production mortality disease 2024',
    'Malaysia poultry broiler layer FCR production performance report',
    'Malaysia aquaculture shrimp tilapia production statistics 2024',
    'Thailand broiler shrimp livestock production statistics 2024 2025',
    'Thailand aquaculture white shrimp production disease loss',
    'Indonesia broiler layer livestock feed efficiency production 2024',
    'Indonesia aquaculture shrimp tilapia production report',
    'Southeast Asia ASEAN animal feed additive market report 2024',
    'ASEAN livestock poultry aquaculture production statistics 2024',
    'Southeast Asia swine disease PRRS ASF production impact 2024',
    'Southeast Asia broiler layer disease avian influenza production loss',
    'Southeast Asia shrimp disease WSSV AHPND production loss 2024',
    '越南 畜牧业 家禽 猪 生产统计 饲料转化率 2024',               # 簡體
    '越南 对虾养殖 产量 疾病损失 白斑病 2024',
    '马来西亚 家禽 肉鸡 蛋鸡 生产性能 统计报告',
    '泰国 对虾养殖 产量 存活率 统计 2024',
    '印尼 畜牧业 家禽 猪 生产数据 统计 2024',
    '东南亚 饲料添加剂 市场报告 长链醇 虾青素 2024',
    '越南 畜牧業 家禽 豬 生產統計 飼料轉化率 2024',              # 繁體
    '馬來西亞 家禽 肉雞 蛋雞 生產性能 統計報告',
    '泰國 對蝦養殖 產量 存活率 統計 2024',
    '印尼 畜牧業 家禽 生產數據 2024',

    # ══════════════════════════════════════════════════
    # 中國行業報告（三語）
    # ══════════════════════════════════════════════════
    '中国畜牧业统计年报 2024 生产性能 饲料转化率',               # 簡體
    '全国生猪生产形势 季报 月报 2024 2025',
    '肉鸡行业白皮书 生产性能 饲料转化率 死亡率 2024',
    '蛋鸡行业报告 产蛋性能 养殖效益 死亡率 2024',
    '中国水产养殖统计 对虾 罗非鱼 草鱼 2024',
    '中国饲料添加剂行业报告 长链醇 虾青素 硅酸 2024',
    '中国肉牛产业报告 生产性能 饲料转化率 2024',
    '中国奶牛养殖报告 产奶量 乳品质 2024',
    '中国肉羊产业发展报告 2024 生产性能',
    '中國畜牧業統計年報 2024 生產性能 飼料轉化率',              # 繁體
    '全國生豬生產形勢 季報 2024 2025',
    '肉雞行業白皮書 生產性能 飼料轉化率 2024',
    '蛋雞行業報告 產蛋性能 養殖效益 2024',
    'China livestock production annual report 2024 FCR ADG',        # 英文
    'China swine pig industry production statistics 2024 2025',
    'China broiler poultry industry white paper performance 2024',
    'China aquaculture shrimp tilapia production statistics 2024',
    'China feed additive industry report long chain alcohol astaxanthin',
]

def tg(msg):
    try:
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id': TELEGRAM_CHAT, 'text': msg, 'parse_mode': 'HTML'},
            timeout=10)
    except Exception as e:
        logging.warning(f'TG: {e}')

# ── 多源搜尋 ──────────────────────────────────────────────
def search_ddg(query):
    """DuckDuckGo 搜尋（免費，替代超額 Tavily）"""
    try:
        from ddgs import DDGS
        results = list(DDGS().text(query, max_results=MAX_RESULTS_PER_QUERY))
        return [{'url': r.get('href',''), 'title': r.get('title',''),
                 'snippet': r.get('body','')[:300],
                 'raw': r.get('body','') or '',
                 'source': 'ddg'} for r in results if r.get('href')]
    except Exception as e:
        logging.warning(f'DDG: {e}')
    return []

def search_semantic_scholar(query):
    try:
        resp = requests.get(
            'https://api.semanticscholar.org/graph/v1/paper/search',
            params={'query': query, 'limit': 3,
                    'fields': 'title,abstract,year,externalIds,openAccessPdf'},
            headers={'x-api-key': SEMANTIC_SCHOLAR_KEY}, timeout=20)
        if resp.status_code == 200:
            results = []
            for p in resp.json().get('data', []):
                pdf = p.get('openAccessPdf') or {}
                url = pdf.get('url','') or \
                      (f"https://doi.org/{p['externalIds']['DOI']}"
                       if p.get('externalIds',{}).get('DOI') else '')
                if url:
                    results.append({
                        'url': url, 'title': p.get('title',''),
                        'snippet': p.get('abstract','')[:300],
                        'raw': p.get('abstract',''),
                        'source': 'scholar'})
            return results
    except Exception as e:
        logging.warning(f'Scholar: {e}')
    return []

def search_firecrawl(query):
    try:
        resp = requests.post(
            'https://api.firecrawl.dev/v1/search',
            headers={'Authorization': f'Bearer {FIRECRAWL_KEY}'},
            json={'query': query, 'limit': 3}, timeout=30)
        if resp.status_code == 200:
            return [{'url': r.get('url',''), 'title': r.get('title',''),
                     'snippet': r.get('description','')[:300],
                     'raw': r.get('markdown','') or '',
                     'source': 'firecrawl'}
                    for r in resp.json().get('data', [])]
    except Exception as e:
        logging.warning(f'Firecrawl search: {e}')
    return []

def multi_search(query):
    all_results = []
    url_seen = set()
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = [
            ex.submit(search_ddg, query),
            ex.submit(search_semantic_scholar, query),
            ex.submit(search_firecrawl, query),
        ]
        for f in as_completed(futures, timeout=40):
            try:
                for r in f.result():
                    h = hashlib.md5(r.get('url','').encode()).hexdigest()
                    if h not in url_seen:
                        url_seen.add(h)
                        all_results.append(r)
            except Exception as e:
                logging.warning(f'Search future: {e}')
    return all_results

# ── 爬蟲（無本地依賴）────────────────────────────────────
SKIP_DOMAINS = ['researchgate.net','jstor.org','sci-hub',
                'facebook.com','twitter.com','youtube.com']

async def _crawl4ai(url):
    try:
        from crawl4ai import AsyncWebCrawler
        async with AsyncWebCrawler(verbose=False) as crawler:
            r = await crawler.arun(url, word_count_threshold=50)
            if r.success and r.markdown and len(r.markdown) > 200:
                return r.markdown[:5000]
    except Exception as e:
        logging.debug(f'Crawl4AI: {e}')
    return ''

def crawl4ai_fetch(url):
    try:
        return asyncio.run(_crawl4ai(url))
    except Exception:
        return ''

def firecrawl_scrape(url):
    try:
        resp = requests.post(
            'https://api.firecrawl.dev/v1/scrape',
            headers={'Authorization': f'Bearer {FIRECRAWL_KEY}'},
            json={'url': url, 'formats': ['markdown']}, timeout=30)
        if resp.status_code == 200:
            md = resp.json().get('data',{}).get('markdown','')
            if md and len(md) > 200:
                return md[:5000]
    except Exception as e:
        logging.debug(f'Firecrawl scrape: {e}')
    return ''

def scrape_url(url):
    if any(d in url for d in SKIP_DOMAINS):
        return ''
    text = crawl4ai_fetch(url)
    if text: return text
    return firecrawl_scrape(url)

# ── R2 上傳 ───────────────────────────────────────────────
def upload_to_r2(records, date_str):
    try:
        import boto3
        s3 = boto3.client('s3',
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY,
            aws_secret_access_key=R2_SECRET_KEY,
            region_name='auto')
        key = f'raw/{date_str}/collected.json'
        body = json.dumps(records, ensure_ascii=False, indent=2)
        s3.put_object(Bucket=R2_BUCKET, Key=key,
                      Body=body.encode('utf-8'),
                      ContentType='application/json')
        logging.info(f'R2 upload: {key} ({len(records)} records)')
        return key
    except Exception as e:
        logging.error(f'R2 upload fail: {e}')
        return ''

# ── 主流程 ────────────────────────────────────────────────
def main():
    date_str = datetime.utcnow().strftime('%Y-%m-%d')
    logging.info(f'collect_raw START {date_str}')
    tg(f'🌐 <b>GitHub Actions 開始收集</b>\n{date_str}\n物種組: {len(SEARCH_TARGETS)} | 原料查詢: {len(INGREDIENT_QUERIES)}')

    all_records = []
    url_seen = set()
    total_urls = 0

    # 市場KPI搜尋
    for species, region, kpis in SEARCH_TARGETS:
        queries = [
            f'{species.replace("_"," ")} {" ".join(kpis[:2])} {region.replace("_"," ")} 2024 2025',
            f'{species.replace("_"," ")} feed conversion ratio {region} China statistics',
            f'{species.replace("_"," ")} 飼料轉化率 {region.replace("CN_","").replace("SEA_","")} 2024',
        ]
        for query in queries:
            results = multi_search(query)
            time.sleep(SLEEP_QUERY)
            for r in results:
                url = r.get('url','')
                if not url: continue
                h = hashlib.md5(url.encode()).hexdigest()
                if h in url_seen: continue
                url_seen.add(h)
                raw = r.get('raw','')
                if not raw or len(raw) < 300:
                    raw = scrape_url(url)
                if raw and len(raw) > 200:
                    all_records.append({
                        'type': 'market_kpi',
                        'species': species,
                        'region': region,
                        'target_kpis': kpis,
                        'url': url,
                        'title': r.get('title',''),
                        'text': raw[:5000],
                        'source': r.get('source',''),
                        'collected_at': datetime.utcnow().isoformat(),
                    })
                    total_urls += 1
        logging.info(f'{species}/{region}: {total_urls} total records so far')

    # 核心原料論文搜尋
    for query in INGREDIENT_QUERIES:
        results = multi_search(query)
        time.sleep(SLEEP_QUERY)
        for r in results:
            url = r.get('url','')
            if not url: continue
            h = hashlib.md5(url.encode()).hexdigest()
            if h in url_seen: continue
            url_seen.add(h)
            raw = r.get('raw','') or scrape_url(url)
            if raw and len(raw) > 200:
                all_records.append({
                    'type': 'ingredient_evidence',
                    'query': query,
                    'url': url,
                    'title': r.get('title',''),
                    'text': raw[:5000],
                    'source': r.get('source',''),
                    'collected_at': datetime.utcnow().isoformat(),
                })

    # 上傳 R2
    r2_key = upload_to_r2(all_records, date_str)

    tg(f'✅ <b>GitHub Actions 收集完成</b>\n'
       f'日期: {date_str}\n'
       f'原始文章: {len(all_records)} 筆\n'
       f'R2: {r2_key}\n'
       f'⚡ EVO-X2 請執行 /process 處理入庫')

    logging.info(f'Done. {len(all_records)} records -> {r2_key}')

if __name__ == '__main__':
    main()
