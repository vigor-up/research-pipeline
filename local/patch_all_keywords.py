# -*- coding: utf-8 -*-
"""
patch_all_keywords.py
同步更新 EVO-X2 三個主程式的關鍵字清單
執行：python patch_all_keywords.py
"""

import re, ast
from pathlib import Path

BASE = Path(r'D:\LLM\workflows\research-pipeline-v2\local')
F_INT   = BASE / 'auto_collect_v5_integrated.py'
F_V5    = BASE / 'auto_collect_v5.py'
F_RAW   = BASE / 'collect_raw.py'

# ══ ALL_SPECIES / SEARCH_TARGETS（53組）══
NEW_ALL_SPECIES = """
ALL_SPECIES = [
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
"""

NEW_SEARCH_TARGETS = """
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
"""

# ══ ACADEMIC_QUERIES / INGREDIENT_QUERIES（三語，235條）══
NEW_ACADEMIC_QUERIES = """
ACADEMIC_QUERIES = [
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
"""

NEW_INGREDIENT_QUERIES = """
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
"""

# ══ INGREDIENT_SEARCHES（三語重構版）══
NEW_INGREDIENT_SEARCHES = """
INGREDIENT_SEARCHES = [
    {
        'ingredient': 'long_chain_alcohols',
        'queries_zh_hans': [
            # C24-C32 簡體
            '多二十烷醇 肉鸡 饲料转化率 生长性能 试验',
            '多二十烷醇 蛋鸡 产蛋率 蛋品质 饲养试验',
            '多二十烷醇 育肥猪 料肉比 日增重 试验',
            '多二十烷醇 肉牛 饲料转化率 日增重',
            '多二十烷醇 对虾 存活率 生长',
            '二十八烷醇 育肥猪 料肉比 生长性能 饲养试验',
            '二十八烷醇 蛋鸡 产蛋率 蛋壳质量',
            '三十烷醇 畜禽 生长性能 饲料转化率 试验',
            '二十四烷醇 畜禽 生产性能 饲料转化率',
            '二十五烷醇 畜禽 生产性能 饲养试验',
            '二十六烷醇 家禽 饲料转化率 生长性能',
            '二十七烷醇 畜禽 生长性能 试验',
            '二十九烷醇 畜禽 饲养试验 生长性能',
            '三十一烷醇 畜禽 生产性能 试验',
            '三十二烷醇 蜂蜡醇 畜禽 生长',
            '长链脂肪醇 畜禽 生产性能 饲料转化率',
            '蜂蜡醇 家禽 生长性能 饲料报酬',
            '混合长链醇 畜禽 生产性能 试验',
        ],
        'queries_zh_hant': [
            # C24-C32 繁體
            '多廿烷醇 肉雞 飼料轉化率 生長性能 試驗',
            '多廿烷醇 蛋雞 產蛋率 蛋品質 飼養試驗',
            '多廿烷醇 育肥豬 料肉比 日增重 試驗',
            '多廿烷醇 肉牛 飼料轉化率 日增重',
            '多廿烷醇 對蝦 存活率 生長',
            '二十八碳醇 育肥豬 料肉比 生長性能',
            '二十八碳醇 蛋雞 產蛋率 蛋殼品質',
            '三十烷醇 畜禽 生長性能 飼料轉化率',
            '長鏈脂肪醇 畜禽 生產性能 飼料轉化率',
        ],
        'queries_en': [
            # C24-C32 英文
            'policosanol poultry FCR growth performance trial 2023 2024',
            'policosanol broiler feed conversion ratio body weight gain',
            'policosanol laying hen egg production performance',
            'policosanol swine pig growth performance feed conversion',
            'policosanol cattle sheep ADG feed efficiency trial',
            'policosanol shrimp aquaculture survival FCR growth',
            'policosanol Vietnam Malaysia Thailand Indonesia livestock',
            'octacosanol swine feed conversion ratio experiment',
            'octacosanol poultry broiler growth performance trial',
            'octacosanol laying hen egg production eggshell quality',
            'triacontanol poultry broiler growth feed conversion trial',
            'triacontanol swine pig performance experiment',
            'tetracosanol poultry livestock growth performance trial',
            'pentacosanol poultry livestock performance trial',
            'hexacosanol poultry feed conversion growth trial',
            'heptacosanol poultry livestock growth performance',
            'nonacosanol poultry livestock performance trial',
            'hentriacontanol poultry livestock performance trial',
            'dotriacontanol poultry livestock performance trial',
            'long chain fatty alcohol C24 C32 poultry livestock performance',
            'long chain aliphatic alcohol swine FCR growth trial',
        ],
        'queries': [],  # 執行時自動合併三語
        'species_targets': ['broiler','finisher_pig','layer_chicken','shrimp',
                             'beef_cattle','dairy_cow','meat_sheep','duck',
                             'goose','rabbit','tilapia','grouper'],
    },
    {
        'ingredient': 'astaxanthin',
        'queries_zh_hans': [
            '虾青素 南美白对虾 存活率 生长性能 饲养试验',
            '虾青素 肉鸡 抗氧化 生产性能 饲料转化率',
            '虾青素 蛋鸡 蛋黄颜色 产蛋率 蛋品质',
            '虾青素 罗非鱼 石斑鱼 鲈鱼 生长存活',
            '虾青素 草鱼 鲤鱼 生长性能 存活率',
            '雨生红球藻提取物 水产 存活率 生长性能',
            '天然虾青素 对虾 抗病力 存活率 东南亚',
        ],
        'queries_zh_hant': [
            '蝦青素 南美白對蝦 存活率 生長性能 飼養試驗',
            '蝦青素 肉雞 抗氧化 生產性能 飼料轉化率',
            '蝦青素 蛋雞 蛋黃顏色 產蛋率 蛋品質',
            '蝦青素 水產 存活率 生長 抗病力',
        ],
        'queries_en': [
            'astaxanthin shrimp FCR survival growth trial 2024 2025',
            'astaxanthin broiler antioxidant growth performance FCR',
            'astaxanthin laying hen egg quality yolk color pigmentation',
            'astaxanthin aquaculture tilapia grouper bass survival',
            'astaxanthin Southeast Asia shrimp aquaculture trial',
            'astaxanthin immune response disease resistance shrimp',
            'natural astaxanthin Haematococcus pluvialis poultry aquaculture',
        ],
        'queries': [],
        'species_targets': ['shrimp','broiler','layer_chicken','tilapia',
                             'grouper','grass_carp','carp'],
    },
    {
        'ingredient': 'ch_osa',
        'queries_zh_hans': [
            '胆碱稳定原硅酸 蛋鸡 蛋壳质量 蛋壳强度 哈氏单位',
            '胆碱稳定原硅酸 家禽 骨骼强度 胫骨灰分 生产性能',
            '有机硅 蛋鸡 蛋品质 蛋壳 产蛋率',
            '生物活性硅 畜禽 骨骼 生长性能 试验',
            '胆碱稳定原硅酸 奶牛 蹄健康 产奶量 体细胞数',
            '胆碱稳定原硅酸 肉鸡 胫骨强度 生长性能',
        ],
        'queries_zh_hant': [
            '膽鹼矽酸 蛋雞 蛋殼品質 蛋殼強度 哈氏單位',
            '膽鹼矽酸 家禽 骨骼強度 脛骨灰分',
            '膽鹼矽酸 奶牛 蹄健康 產乳量',
            '有機矽 蛋雞 蛋品質 蛋殼 產蛋率',
        ],
        'queries_en': [
            'choline stabilized orthosilicic acid laying hen eggshell quality strength',
            'ch-OSA poultry bone tibia ash strength performance trial',
            'orthosilicic acid broiler tibia strength growth FCR',
            'ch-OSA dairy cow hoof health milk yield SCC',
            'bioavailable silicon poultry livestock bone eggshell trial',
            'ch-OSA pig swine bone growth performance experiment',
        ],
        'queries': [],
        'species_targets': ['layer_chicken','broiler','dairy_cow','finisher_pig'],
    },
]
"""

# ══ INGREDIENT_TAGS_MAP（擴充三語別稱）══
NEW_INGREDIENT_TAGS_MAP = """
INGREDIENT_TAGS_MAP = {
    'policosanol': [
        'policosanol','octacosanol','triacontanol','tetracosanol','pentacosanol',
        'hexacosanol','heptacosanol','nonacosanol','hentriacontanol','dotriacontanol',
        '多二十烷醇','二十八烷醇','正二十八烷醇','三十烷醇','蜂花醇',
        '二十四烷醇','二十五烷醇','二十六烷醇','二十七烷醇',
        '二十九烷醇','三十一烷醇','三十二烷醇','蜂蜡醇','混合长链醇',
        '多廿烷醇','二十八碳醇','長鏈脂肪醇','长链脂肪醇',
        '28烷醇','30烷醇','24烷醇','25烷醇','26烷醇','27烷醇',
        '29烷醇','31烷醇','32烷醇','long chain alcohol','fatty alcohol',
    ],
    'astaxanthin': [
        'astaxanthin','虾青素','蝦青素','雨生红球藻','雨生紅球藻',
        'haematococcus','天然虾青素','蝦紅素',
    ],
    'ch_osa': [
        'ch-osa','ch_osa','orthosilicic','silicon','胆碱稳定原硅酸',
        '膽鹼矽酸','有机硅','有機矽','生物活性硅','生物活性矽',
    ],
    'disease': [
        'PRRS','蓝耳','藍耳','PCV2','圆环','圓環','ASF','非洲猪瘟','非洲豬瘟',
        'Newcastle','新城疫','avian influenza','禽流感','coccidiosis','球虫','球蟲',
        'WSSV','白斑','AHPND','EMS','TSV','mastitis','乳房炎','FMD','口蹄疫',
    ],
}
"""


def update_block(path, old_pat, new_content, label):
    if not path.exists():
        print(f"SKIP: {label} ({path.name} not found)"); return False
    content = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(old_pat, content, re.DOTALL)
    if not match:
        print(f"WARN: {label} block not found in {path.name}"); return False
    bak = path.with_suffix(".py.bak")
    bak.write_text(content, encoding="utf-8")
    path.write_text(content[:match.start()] + new_content + content[match.end():], encoding="utf-8")
    print(f"OK: {label}")
    return True

def merge_queries_in_file(path):
    """將 queries_zh_hans + queries_zh_hant + queries_en 合併到 queries"""
    if not path.exists(): return
    content = path.read_text(encoding="utf-8", errors="replace")
    # 找到每個 ingredient block，把三個 queries_* 合併成 queries
    def merge(m):
        block = m.group(0)
        zh_hans = re.findall(r"'queries_zh_hans':\s*\[(.*?)\]", block, re.DOTALL)
        zh_hant = re.findall(r"'queries_zh_hant':\s*\[(.*?)\]", block, re.DOTALL)
        en = re.findall(r"'queries_en':\s*\[(.*?)\]", block, re.DOTALL)
        all_q = []
        for grp in (zh_hans + zh_hant + en):
            for q in re.findall(r"'(.*?)'", grp):
                if q not in all_q:
                    all_q.append(q)
        q_str = ",\n            ".join(f"\'{q}\'" for q in all_q)
        block = re.sub(r"'queries':\s*\[\]",
                       f"'queries': [\n            {q_str}\n        ]", block)
        return block
    new_content = re.sub(r"\{[^{}]*?'ingredient'[^{}]*?\}", merge, content, flags=re.DOTALL)
    if new_content != content:
        path.write_text(new_content, encoding="utf-8")
        print(f"OK: {path.name} queries merged")

def verify(path):
    if not path.exists(): return
    try:
        ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        print(f"OK syntax: {path.name}")
    except SyntaxError as e:
        print(f"ERROR: {path.name}: {e}")
        bak = path.with_suffix(".py.bak")
        if bak.exists():
            path.write_text(bak.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"  restored from backup")

def main():
    print("=== patch_all_keywords.py ===")
    print()

    # 1. collect_raw.py（GitHub Actions）
    update_block(F_RAW, r"SEARCH_TARGETS\s*=\s*\[.*?\n\]",
        NEW_SEARCH_TARGETS.strip(), "collect_raw → SEARCH_TARGETS")
    update_block(F_RAW, r"INGREDIENT_QUERIES\s*=\s*\[.*?\n\]",
        NEW_INGREDIENT_QUERIES.strip(), "collect_raw → INGREDIENT_QUERIES")

    # 2. auto_collect_v5.py（本機原料論文）
    update_block(F_V5, r"INGREDIENT_SEARCHES\s*=\s*\[.*?^\]",
        NEW_INGREDIENT_SEARCHES.strip(), "auto_collect_v5 → INGREDIENT_SEARCHES")
    update_block(F_V5, r"INGREDIENT_TAGS_MAP\s*=\s*\{.*?^\}",
        NEW_INGREDIENT_TAGS_MAP.strip(), "auto_collect_v5 → INGREDIENT_TAGS_MAP")

    # 3. auto_collect_v5_integrated.py（本機市場KPI）
    update_block(F_INT, r"ALL_SPECIES\s*=\s*\[.*?\n\]",
        NEW_ALL_SPECIES.strip(), "auto_collect_v5_integrated → ALL_SPECIES")
    update_block(F_INT, r"INGREDIENT_SEARCHES\s*=\s*\[.*?^\]",
        NEW_INGREDIENT_SEARCHES.strip(), "auto_collect_v5_integrated → INGREDIENT_SEARCHES")
    update_block(F_INT, r"INGREDIENT_TAGS_MAP\s*=\s*\{.*?^\}",
        NEW_INGREDIENT_TAGS_MAP.strip(), "auto_collect_v5_integrated → INGREDIENT_TAGS_MAP")

    # 4. 語法驗證
    print()
    for f in [F_RAW, F_V5, F_INT]:
        verify(f)

    print()
    print("Done:")
    print("  collect_raw.py        → SEARCH_TARGETS(53) + INGREDIENT_QUERIES(235)")
    print("  auto_collect_v5.py    → INGREDIENT_SEARCHES(三語) + INGREDIENT_TAGS_MAP")
    print("  auto_collect_v5_integrated.py → ALL_SPECIES(53) + INGREDIENT_SEARCHES + TAGS")

if __name__ == "__main__":
    main()
