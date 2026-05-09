# -*- coding: utf-8 -*-
"""
auto_collect_v5.py
智慧型搜尋資料引擎 — 全球頂尖30%性能目標
架構：多源搜尋 → AI價值判讀 → 智慧深爬 → 雙軌儲存
v5 改進：
  - 多源搜尋並行（Tavily + Semantic Scholar + Firecrawl Search）
  - Qwen頁面價值預判（避免無效深爬）
  - 爬蟲三層降級（Crawl4AI→Scrapling→Firecrawl）
  - URL hash + 內容指紋雙重去重
  - 動態查詢擴展（根據抽取結果調整下一輪查詢）
  - R2自動同步 + RAGFlow雙軌入庫
  - 每輪結束Telegram推送詳情
"""

import sqlite3, uuid, json, time, logging, requests, hashlib, re, asyncio, math
import sys, os, threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from scrapling import Fetcher

# ── ChromaDB 初始化（延遲載入）───────────────────────────
_chroma_collection = None

def get_chroma_collection():
    global _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        client = chromadb.PersistentClient(path=r'D:\LLM\knowledge\biotech\db')
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name='BAAI/bge-m3')
        _chroma_collection = client.get_or_create_collection(
            name='biotech_papers',
            embedding_function=ef,
            metadata={'hnsw:space': 'cosine'})
        logging.info(f'ChromaDB connected: {_chroma_collection.count()} docs')
        return _chroma_collection
    except Exception as e:
        logging.warning(f'ChromaDB init fail: {e}')
        return None

# ── 常數設定 ─────────────────────────────────────────────
DB_PATH        = r'D:\LLM\knowledge\market\market_data.db'
LOG_PATH       = r'D:\LLM\workflows\research-pipeline-v2\logs\auto_collect_v5.log'
EXPORT_DIR     = r'D:\LLM\knowledge\market'
QWEN_URL       = 'http://localhost:1234/v1/chat/completions'
QWEN_MODEL     = 'qwen3.6-35b'
TELEGRAM_TOKEN = '8703702788:AAFKEiGmLYTAuFVG9GX-gRtVTUUyi-f_5mM'
TELEGRAM_CHAT  = 897274134
WEBHOOK_PORT   = 8766
SLEEP_QUERY    = 6
SLEEP_SPECIES  = 12
SLEEP_ROUND    = 1800
MAX_HOURS      = 14.5
MAX_RETRIES    = 3
RETRY_DELAY    = 12

# API Keys
TAVILY_KEY        = None
FIRECRAWL_KEY     = 'fc-f1b23a25854a4c96aa56acb89c65e930'
SEMANTIC_SCHOLAR_KEY = 's2k-8Zr1tg8DeqJiJKwD7U5ip0QK9pijy04E7lHXIKfc'
RAGFLOW_API_KEY   = 'ragflow-fcCq8K0sVcefhVHboEmBOOzt5S2cQ7jCcHT5cCwhWRM'
RAGFLOW_DATASET   = '5a68aa6e49ba11f190c657ee8852d812'
RAGFLOW_URL       = 'http://localhost/api/v1'

# R2
R2_ENDPOINT   = 'https://adb1040c847f4ae4a7d6bfedcccd7b77.r2.cloudflarestorage.com'
R2_ACCESS_KEY = 'f443b2e5acc77dd1af6a83a5d548b35b'
R2_SECRET_KEY = 'da1c377ffbc03b865504e292480e0e2806ddb84a61bf87b7e6a2066632a4a357'
R2_BUCKET     = 'richtrong-collect'

# FAO
FAO_API_BASE = 'https://fenixservices.fao.org/faostat/api/v1'
FAO_AREA_CN  = '351'
FAO_SPECIES_MAP = {
    'dairy_cow':     [('QL', 'Milk, whole fresh cow'),   ('QA', 'Cattle')],
    'beef_cattle':   [('QA', 'Cattle'),                  ('QL', 'Meat, cattle')],
    'finisher_pig':  [('QA', 'Pigs'),                    ('QL', 'Meat, pig')],
    'layer_chicken': [('QA', 'Chickens'),                ('QL', 'Eggs, hen, in shell')],
    'broiler':       [('QA', 'Chickens'),                ('QL', 'Meat, chicken')],
    'meat_sheep':    [('QA', 'Sheep'),                   ('QL', 'Meat, sheep')],
    'meat_goat':     [('QA', 'Goats'),                   ('QL', 'Meat, goat')],
    'dairy_goat':    [('QA', 'Goats'),                   ('QL', 'Milk, whole fresh goat')],
    'shrimp':        [('QA', 'Shrimps, prawns'),         ('QL', 'Shrimps, prawns')],
    'tilapia':       [('QA', 'Tilapias nei'),            ('QL', 'Tilapias nei')],
}

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

# ── 核心原料論文搜尋配置（機密）─────────────────────────
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

SKIP_DOMAINS = [
    'researchgate.net', 'jstor.org', 'sci-hub',
    'facebook.com', 'twitter.com', 'instagram.com',
    'youtube.com', 'tiktok.com',
]

# ── 地區細化標準化 ────────────────────────────────────────
REGION_NORMALIZE = {
    'northeast':     'CN_northeast', 'cn_northeast': 'CN_northeast', '東北': 'CN_northeast',
    'north':         'CN_north',     'cn_north':     'CN_north',     '華北': 'CN_north',
    'east':          'CN_east',      'cn_east':      'CN_east',      '華東': 'CN_east',
    'south':         'CN_south',     'cn_south':     'CN_south',     '華南': 'CN_south',
    'central':       'CN_central',   'cn_central':   'CN_central',   '華中': 'CN_central',
    'southwest':     'CN_southwest', 'cn_southwest': 'CN_southwest', '西南': 'CN_southwest',
    'northwest':     'CN_northwest', 'cn_northwest': 'CN_northwest', '西北': 'CN_northwest',
    'sea_malaysia':  'SEA_malaysia',  'sea_thailand':  'SEA_thailand',
    'sea_vietnam':   'SEA_vietnam',   'sea_indonesia': 'SEA_indonesia',
    'tw':            'TW_all',        'taiwan':        'TW_all',
    'global':        'GLOBAL',        'cn_all':        'CN_all',
}

def normalize_region(region):
    return REGION_NORMALIZE.get(region.lower(), region)

# ── 核心原料標籤偵測（機密，對外屏蔽）───────────────────

# KPI 中英文對照（讓簡體 missing 能 match 到 DB 已有的英文 kpi_id）
KPI_ZH_TO_EN = {
    '饲料转化率': 'fcr', '料肉比': 'fcr', '料重比': 'fcr',
    '日增重': 'adg', '平均日增重': 'adg',
    '死亡率': 'mortality', '死淘率': 'mortality',
    '产蛋率': 'egg_rate', '出栏体重': 'body_weight',
    '存活率': 'survival', '成活率': 'survival',
    '产奶量': 'milk_yield', '窝产仔数': 'litter_size',
}
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

def detect_ingredient_tag(text):
    if not text: return None
    tl = text.lower()
    for tag, kws in INGREDIENT_TAGS_MAP.items():
        if any(kw in tl for kw in kws):
            return tag
    return None

# ── Prompts ──────────────────────────────────────────────
PAGE_VALUE_PROMPT = """你是動物營養市場研究員。判斷以下頁面摘要是否含有可用的生產KPI數字。
物種：{species}，目標KPI：{target_kpis}
頁面摘要（前500字）：
{snippet}

只回覆JSON：{{"value": "high"|"medium"|"low"|"none", "reason": "一句話", "has_numbers": true|false}}
- high：有明確數字且符合目標KPI
- medium：有相關數字但不完全匹配
- low：有相關內容但無具體數字
- none：完全無關"""

GAP_PROMPT = """你是動物營養市場研究員。
DB現有：{db_summary}
為以下物種生成6條搜索查詢（英文3條+中文3條），避免重複已有資料：
物種：{species}（{region}）缺少：{missing_kpis}
已搜過的查詢：{searched_queries}
要求：
1. 英文查詢用通用名詞（如pig不用finisher_pig，chicken不用broiler）
2. 地區用省份名或國家名（如Heilongjiang, Northeast China）
3. 不要用底線或代碼格式
4. 優先2022-2025年數據
輸出純JSON數組：["q1","q2","q3","q4","q5","q6"]"""

EXTRACT_PROMPT = """從以下文字抽取{species}的生產KPI。
只抽取文中明確出現的數字，不推測。
輸出純JSON數組：
[{{"kpi":"fcr|adg|mortality|milk_yield|egg_rate|survival|litter_size|slaughter_wt|other",
  "value_min":數字或null,"value_mid":數字,"value_max":數字或null,
  "unit":"單位","condition":"條件","metric_type":"baseline或disease_penalty",
  "year":年份或null,"confidence":"high|medium|low",
  "source_sentence":"原文中包含此數字的句子（20字內）"}}]
無數字回覆: []
文字：{text}"""

VERIFY_PROMPT = """以下KPI數據聲稱來自這段文字，請驗證：
KPI: {kpi_id} = {value} {unit}
原文句子: "{source_sentence}"
文字片段:
{text}
問題：原文句子是否真實出現在文字中？數字是否正確？
回覆純JSON：{{"verified": true|false, "reason": "一句話說明"}}"""

INGREDIENT_EXTRACT_PROMPT = """從以下文字抽取{ingredient}在{species}上的試驗效果數據。
只抽取文中明確出現的數字，不推測。
輸出純JSON數組：
[{{"kpi":"fcr|adg|mortality|egg_rate|survival|milk_yield|other",
  "control_value":對照組數字或null,
  "treatment_value":試驗組數字,
  "unit":"單位",
  "improvement_pct":改善百分比或null,
  "year":年份或null,
  "study_type":"field_trial|lab|meta_analysis|review",
  "confidence":"high|medium|low",
  "raw_text":"原文關鍵句子（30字內）"}}]
無數字回覆: []
文字：{text}"""

QUERY_EXPAND_PROMPT = """根據以下抽取結果，判斷是否需要擴展搜尋：
已抽取KPI：{extracted_kpis}
仍缺少KPI：{missing_kpis}
物種：{species}（{region}）

如果缺少重要KPI，生成2條追加查詢；否則回覆空數組。
查詢規則：
1. 用自然語言，不用代碼（如"South China"不用"CN_south"，"pig"不用"finisher_pig"）
2. 具體含物種+KPI+地區
輸出純JSON數組：["q1","q2"] 或 []"""

# ── 初始化 ────────────────────────────────────────────────
def setup_logging():
    Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(LOG_PATH, encoding='utf-8'),
            logging.StreamHandler()
        ])

def load_api_keys():
    global TAVILY_KEY
    for enc in ('utf-8-sig', 'utf-8', 'cp950'):
        try:
            with open(r'D:\LLM\API key.txt', encoding=enc) as f:
                for line in f:
                    if 'TAVILY' in line.upper() and '=' in line:
                        TAVILY_KEY = line.split('=', 1)[-1].strip().strip('"\'')
                        logging.info(f'Tavily key loaded: {TAVILY_KEY[:8]}...')
                        return True
        except Exception:
            continue
    return False

def tg(msg):
    try:
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id': TELEGRAM_CHAT, 'text': msg, 'parse_mode': 'HTML'},
            timeout=10)
    except Exception as e:
        logging.warning(f'TG: {e}')

# ── Qwen 呼叫 ─────────────────────────────────────────────
def qwen_call(prompt, max_tokens=500, temperature=0.1):
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(QWEN_URL, json={
                'model': QWEN_MODEL,
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': temperature,
                'max_tokens': max_tokens,
                'stream': False,
            }, timeout=90)
            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message']['content']
                # 過濾 <think> 標籤（Qwen3 thinking mode）
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                return content
        except Exception as e:
            logging.warning(f'Qwen attempt {attempt+1}: {e}')
        time.sleep(RETRY_DELAY)
    return ''

def qwen_page_value(snippet, species, target_kpis):
    """AI判斷頁面價值，決定是否值得深爬"""
    if not snippet or len(snippet) < 50:
        return 'none'
    prompt = PAGE_VALUE_PROMPT.format(
        species=species,
        target_kpis=', '.join(target_kpis),
        snippet=snippet[:500])
    content = qwen_call(prompt, max_tokens=100)
    try:
        s = content.find('{'); e = content.rfind('}') + 1
        if s >= 0 and e > s:
            result = json.loads(content[s:e])
            val = result.get('value', 'none')
            logging.debug(f'PageValue={val} | {result.get("reason","")}')
            return val
    except Exception:
        pass
    return 'medium'  # 判讀失敗預設medium，繼續處理

# ── Region code → 自然語言（搜尋查詢用）─────────────────────
REGION_LABEL = {
    'CN_northeast': 'Northeast China',
    'CN_north':     'North China',
    'CN_south':     'South China',
    'CN_central':   'Central China',
    'CN_east':      'East China',
    'CN_southwest': 'Southwest China',
    'CN_northwest': 'Northwest China',
    'CN_all':       'China',
    'SEA_vietnam':  'Vietnam',
    'SEA_malaysia': 'Malaysia',
    'SEA_thailand': 'Thailand',
    'SEA_indonesia':'Indonesia',
    'GLOBAL':       'Global',
}

def qwen_gen_queries(species, region, missing_kpis, db_summary, searched_queries=None):
    region_label = REGION_LABEL.get(region, region)
    species_label = species.replace('_', ' ')
    if not missing_kpis:
        return [f'{species_label} FCR ADG {region_label} 2024']
    prompt = GAP_PROMPT.format(
        db_summary=json.dumps(db_summary, ensure_ascii=False),
        species=species_label, region=region_label,
        missing_kpis=missing_kpis,
        searched_queries=json.dumps(searched_queries or [], ensure_ascii=False))
    content = qwen_call(prompt, max_tokens=400)
    try:
        s = content.find('['); e = content.rfind(']') + 1
        if s >= 0 and e > s:
            queries = json.loads(content[s:e])
            return [q for q in queries if isinstance(q, str)][:6]
    except Exception:
        pass
    return [f'{species_label} {" ".join(missing_kpis[:2])} {region_label} 2024']

def qwen_extract(text, species):
    if not text or len(text) < 100:
        return []
    prompt = EXTRACT_PROMPT.format(species=species, text=text[:4000])
    content = qwen_call(prompt, max_tokens=1500)
    try:
        s = content.find('['); e = content.rfind(']') + 1
        if s >= 0 and e > s:
            return json.loads(content[s:e])
    except Exception:
        pass
    return []

def qwen_extract_ingredient(text, ingredient, species):
    if not text or len(text) < 100:
        return []
    prompt = INGREDIENT_EXTRACT_PROMPT.format(
        ingredient=ingredient, species=species, text=text[:4000])
    content = qwen_call(prompt, max_tokens=1500)
    try:
        s = content.find('['); e = content.rfind(']') + 1
        if s >= 0 and e > s:
            return json.loads(content[s:e])
    except Exception:
        pass
    return []

def qwen_verify(kpi_id, value, unit, source_sentence, text):
    if not source_sentence or len(source_sentence) < 5:
        return False
    prompt = VERIFY_PROMPT.format(
        kpi_id=kpi_id, value=value, unit=unit,
        source_sentence=source_sentence, text=text[:2000])
    content = qwen_call(prompt, max_tokens=200)
    try:
        s = content.find('{'); e = content.rfind('}') + 1
        if s >= 0 and e > s:
            result = json.loads(content[s:e])
            return result.get('verified', False)
    except Exception:
        pass
    return False

def qwen_expand_queries(extracted_kpis, missing_kpis, species, region):
    """根據抽取結果動態擴展查詢"""
    if not missing_kpis:
        return []
    prompt = QUERY_EXPAND_PROMPT.format(
        extracted_kpis=extracted_kpis,
        missing_kpis=missing_kpis,
        species=species, region=region)
    content = qwen_call(prompt, max_tokens=200)
    try:
        s = content.find('['); e = content.rfind(']') + 1
        if s >= 0 and e > s:
            return json.loads(content[s:e])
    except Exception:
        pass
    return []

# ── FAO STAT API ──────────────────────────────────────────
def fao_fetch(dataset, item_name, area=FAO_AREA_CN, years='2020,2021,2022,2023'):
    try:
        url = f'{FAO_API_BASE}/data/{dataset}'
        params = {
            'area': area,
            'element': '5510,5610,5320,5422',
            'year': years,
            'output_type': 'json',
        }
        r = requests.get(url, params=params, timeout=3)
        if r.status_code == 200:
            data = r.json()
            items = data.get('data', [])
            matched = [i for i in items if item_name.lower() in i.get('Item', '').lower()]
            logging.info(f'FAO {dataset}/{item_name}: {len(matched)} records')
            return matched
    except Exception as e:
        logging.warning(f'FAO API error: {e}')
    return []

def fao_to_kpi(fao_records, species, region='CN_all'):
    kpis = []
    element_map = {
        'Yield':       ('milk_yield',        'hg/An'),
        'Production':  ('market_output',     '1000 tonnes'),
        'Stocks':      ('market_population', '1000 Head'),
        'Slaughtered': ('market_slaughter',  '1000 Head'),
    }
    for rec in fao_records:
        element = rec.get('Element', '')
        value   = rec.get('Value')
        year    = rec.get('Year')
        unit    = rec.get('Unit', '')
        if value is None:
            continue
        for key, (kpi_name, expected_unit) in element_map.items():
            if key.lower() in element.lower():
                kpis.append({
                    'kpi': kpi_name,
                    'value_mid': float(value),
                    'value_min': None,
                    'value_max': None,
                    'unit': unit or expected_unit,
                    'condition': 'fao_official',
                    'metric_type': 'baseline',
                    'year': int(year) if year else 2023,
                    'confidence': 'high',
                    'source_sentence': f'FAO STAT {element} {value} {unit} {year}',
                    'fao_source': True,
                })
    return kpis

# ── 多源搜尋引擎 ──────────────────────────────────────────
def search_ddg(query, max_results=5):
    """DuckDuckGo 搜尋（免費無限額，替代超額 Tavily）"""
    try:
        from ddgs import DDGS
        results = list(DDGS().text(query, max_results=max_results))
        logging.info(f'DDG [{len(results)}] "{query[:50]}"')
        return [{'url': r.get('href',''), 'title': r.get('title',''),
                 'snippet': r.get('body','')[:500],
                 'raw': r.get('body','') or '',
                 'source': 'ddg'} for r in results if r.get('href')]
    except Exception as e:
        logging.warning(f'DDG: {e}')
    return []
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post('https://api.tavily.com/search', json={
                'api_key': TAVILY_KEY,
                'query': query,
                'max_results': max_results,
                'search_depth': 'advanced',
                'include_raw_content': True,
            }, timeout=30)
            if resp.status_code == 200:
                results = resp.json().get('results', [])
                logging.info(f'Tavily [{len(results)}] "{query[:50]}"')
                return [{'url': r.get('url',''), 'title': r.get('title',''),
                         'snippet': r.get('content','')[:500],
                         'raw': r.get('raw_content','') or '',
                         'source': 'tavily'} for r in results]
        except Exception as e:
            logging.warning(f'Tavily: {e}')
        time.sleep(RETRY_DELAY)
    return []

def search_semantic_scholar(query, max_results=5):
    """Semantic Scholar — 學術論文直搜"""
    try:
        resp = requests.get(
            'https://api.semanticscholar.org/graph/v1/paper/search',
            params={
                'query': query,
                'limit': max_results,
                'fields': 'title,abstract,year,externalIds,openAccessPdf',
            },
            headers={'x-api-key': SEMANTIC_SCHOLAR_KEY},
            timeout=3)
        if resp.status_code == 200:
            papers = resp.json().get('data', [])
            results = []
            for p in papers:
                pdf = p.get('openAccessPdf', {})
                url = pdf.get('url', '') if pdf else ''
                if not url:
                    doi = p.get('externalIds', {}).get('DOI', '')
                    url = f'https://doi.org/{doi}' if doi else ''
                if url:
                    results.append({
                        'url': url,
                        'title': p.get('title', ''),
                        'snippet': p.get('abstract', '')[:500],
                        'raw': p.get('abstract', ''),
                        'source': 'semantic_scholar',
                        'year': p.get('year'),
                    })
            logging.info(f'SemanticScholar [{len(results)}] "{query[:50]}"')
            return results
    except Exception as e:
        logging.warning(f'SemanticScholar: {e}')
    return []

def search_firecrawl(query, max_results=5):
    """Firecrawl Search — JS密集頁面搜尋"""
    try:
        resp = requests.post(
            'https://api.firecrawl.dev/v1/search',
            headers={'Authorization': f'Bearer {FIRECRAWL_KEY}'},
            json={'query': query, 'limit': max_results, 'lang': 'zh'},
            timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('data', [])
            logging.info(f'Firecrawl Search [{len(results)}] "{query[:50]}"')
            return [{'url': r.get('url',''), 'title': r.get('title',''),
                     'snippet': r.get('description','')[:500],
                     'raw': r.get('markdown','') or '',
                     'source': 'firecrawl'} for r in results]
    except Exception as e:
        logging.warning(f'Firecrawl Search: {e}')
    return []

def multi_search(query, target_kpis=None):
    """多源並行搜尋 + AI去重排序"""
    all_results = []
    url_seen = set()

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {
            ex.submit(search_ddg, query, 5): 'ddg',
            ex.submit(search_semantic_scholar, query, 3): 'scholar',
            ex.submit(search_firecrawl, query, 3): 'firecrawl',
        }
        for future in as_completed(futures, timeout=40):
            try:
                results = future.result()
                for r in results:
                    url = r.get('url', '')
                    if not url:
                        continue
                    url_hash = hashlib.md5(url.encode()).hexdigest()
                    if url_hash not in url_seen:
                        url_seen.add(url_hash)
                        all_results.append(r)
            except Exception as e:
                logging.warning(f'Search future error: {e}')

    logging.info(f'MultiSearch total: {len(all_results)} unique results')
    return all_results

# ── 爬蟲三層降級 ──────────────────────────────────────────
async def _crawl4ai_fetch(url):
    try:
        from crawl4ai import AsyncWebCrawler
        async with AsyncWebCrawler(verbose=False) as crawler:
            r = await crawler.arun(url, word_count_threshold=50)
            if r.success and r.markdown and len(r.markdown) > 200:
                logging.info(f'Crawl4AI ✓ {url[:55]}')
                return r.markdown[:6000]
    except Exception as e:
        logging.debug(f'Crawl4AI fail: {e}')
    return ''

def crawl4ai_fetch(url):
    try:
        return asyncio.run(_crawl4ai_fetch(url))
    except Exception:
        return ''

def scrapling_fetch(url):
    try:
        page = Fetcher(auto_match=False).get(url, timeout=3)
        text = page.get_all_text(ignore_tags=('script', 'style', 'nav', 'footer', 'header'))
        if text and len(text) > 200:
            logging.info(f'Scrapling ✓ {url[:55]}')
            return text[:6000]
    except Exception as e:
        logging.debug(f'Scrapling fail: {e}')
    return ''

def firecrawl_scrape(url):
    try:
        r = requests.post(
            'https://api.firecrawl.dev/v1/scrape',
            headers={'Authorization': f'Bearer {FIRECRAWL_KEY}'},
            json={'url': url, 'formats': ['markdown']},
            timeout=30)
        if r.status_code == 200:
            md = r.json().get('data', {}).get('markdown', '')
            if md and len(md) > 200:
                logging.info(f'Firecrawl ✓ {url[:55]}')
                return md[:6000]
    except Exception as e:
        logging.debug(f'Firecrawl scrape fail: {e}')
    return ''

MCP_SCRAPER_URL = 'http://localhost:8765'
RAGFLOW_API_KEY    = 'ragflow-fcCq8K0sVcefhVHboEmBOOzt5S2cQ7jCcHT5cCwhWRM'
RAGFLOW_DATASET_ID = '5a68aa6e49ba11f190c657ee8852d812'
RAGFLOW_URL        = 'http://localhost/api/v1'

_ragflow_doc_seen = set()
_chroma_doc_seen  = set()

def push_to_ragflow(text, url, title):
    url_hash = hashlib.md5(url.encode()).hexdigest()
    if url_hash in _ragflow_doc_seen or len(text) < 300:
        return False
    _ragflow_doc_seen.add(url_hash)
    try:
        resp = requests.post(
            f'{RAGFLOW_URL}/datasets/{RAGFLOW_DATASET_ID}/documents',
            headers={'Authorization': f'Bearer {RAGFLOW_API_KEY}'},
            json={'name': f"{title[:80]}_{url_hash[:8]}.txt", 'text': text[:8000]},
            timeout=30)
        if resp.status_code in (200, 201):
            logging.debug(f'RAGFlow pushed: {title[:50]}')
            return True
    except Exception as e:
        logging.debug(f'RAGFlow push fail: {e}')
    return False

def push_to_chromadb(text, url, title, metadata=None):
    url_hash = hashlib.md5(url.encode()).hexdigest()
    if url_hash in _chroma_doc_seen:
        return False
    _chroma_doc_seen.add(url_hash)
    col = get_chroma_collection()
    if col is None:
        return False
    try:
        if col.get(ids=[url_hash])['ids']:
            return False
        meta = {'url': url[:500], 'title': title[:200],
                'source': 'auto_collect_v5',
                'collected_at': datetime.now().strftime('%Y-%m-%d')}
        if metadata:
            meta.update({k: str(v)[:200] for k, v in metadata.items()})
        col.add(ids=[url_hash], documents=[text[:8000]], metadatas=[meta])
        logging.info(f'ChromaDB added: {title[:50]}')
        return True
    except Exception as e:
        logging.debug(f'ChromaDB push fail: {e}')
    return False

def scrape_url(url, mode='auto'):
    """智能爬蟲：MCP Scrapling(Qwen3.6) → Crawl4AI → Firecrawl"""
    if any(d in url for d in SKIP_DOMAINS):
        return ''
    # 層1：scrapling MCP Server（port 8765，Qwen3.6智能路由）
    try:
        resp = requests.post(f'{MCP_SCRAPER_URL}/call',
            json={'tool': 'scrape_url',
                  'params': {'url': url, 'mode': mode,
                             'extract_type': 'text', 'max_tokens': 4000}},
            timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success'):
                text = data.get('content', '')
                if isinstance(text, list):
                    text = ' '.join(
                        b.get('text', '') if isinstance(b, dict) else str(b)
                        for b in text)
                if text and len(text) > 200:
                    logging.info(f'MCP OK {url[:55]}')
                    return text[:6000]
    except Exception as e:
        logging.debug(f'MCP fail: {e}')
    # 層2：Crawl4AI
    text = crawl4ai_fetch(url)
    if text:
        return text
    # 層3：Firecrawl
    text = firecrawl_scrape(url)
    if text:
        return text
    logging.debug(f'All scrapers failed: {url[:55]}')
    return ''

# ── 內容指紋去重 ──────────────────────────────────────────
def content_fingerprint(text):
    """取前200字生成指紋，避免相同內容重複處理"""
    if not text:
        return ''
    normalized = re.sub(r'\s+', ' ', text[:200]).strip().lower()
    return hashlib.md5(normalized.encode()).hexdigest()

# ── 參考文獻追蹤 ──────────────────────────────────────────
def extract_refs(text):
    dois  = re.findall(r'10\.\d{4,}/\S+', text)
    urls  = re.findall(
        r'https?://(?:doi\.org|pubmed\.ncbi|scholar\.google|cnki\.net)\S+', text)
    refs  = [f'https://doi.org/{d.rstrip(".,)")}' for d in dois[:5]]
    refs += [u.rstrip('.,)') for u in urls[:3]]
    return list(set(refs))

# ── DB 操作 ───────────────────────────────────────────────
def get_db_summary(conn, species, region, target_kpis):
    rows = conn.execute(
        "SELECT kpi_id, value, confirmed FROM market_kpi WHERE species=? AND region=?",
        (species, region)).fetchall()
    have    = {r[0].split('_')[0] for r in rows if r[1] is not None}
        # 簡體KPI轉英文後比對DB已有欄位，避免重複搜尋
    _kpi_map = {
        '饲料转化率':'fcr','料肉比':'fcr','料重比':'fcr',
        '日增重':'adg','平均日增重':'adg',
        '死亡率':'mortality','死淘率':'mortality',
        '产蛋率':'egg_rate','高峰产蛋率':'egg_rate_peak',
        '蛋重':'egg_weight','出栏体重':'body_weight',
        '存活率':'survival','成活率':'survival',
        '产奶量':'milk_yield','乳脂率':'milk_fat',
        '乳蛋白率':'milk_protein','体细胞数':'somatic_cell_count',
        '窝产仔数':'litter_size','分娩率':'farrowing_rate',
        '断奶成活率':'weaning_survival',
        '受胎率':'conception_rate','配种妊娠率':'conception_rate',
        '屠宰率':'dressing_rate','特定生长率':'sgr',
    }
    missing = [k for k in target_kpis
               if _kpi_map.get(k, k).lower() not in have and k.lower() not in have]
    return {'have': list(have), 'missing': missing, 'total': len(rows)}

def write_to_db(conn, species, region, kpis, url, title, text_for_verify=''):
    """累積均值寫入：Welford線上標準差"""
    inserted = updated = confirmed_count = 0
    region = normalize_region(region)
    ingredient_tag = detect_ingredient_tag(text_for_verify + title)

    for kpi in kpis:
        if kpi.get('confidence') == 'low': continue
        vmid = kpi.get('value_mid')
        if vmid is None: continue
        if kpi.get('unit') is None: kpi['unit'] = 'unknown'
        metric  = kpi.get('kpi', 'unknown')
        year    = kpi.get('year') or 2024
        kpi_id  = f"{metric}_{species}_{region.lower()}"
        is_fao  = kpi.get('fao_source', False)
        confirmed = credibility = 0
        confirmed = 1; credibility = 5
        if not is_fao:
            verified    = qwen_verify(kpi_id, vmid, kpi.get('unit',''),
                                      kpi.get('source_sentence',''), text_for_verify)
            confirmed   = 1 if verified else 0
            credibility = 4 if verified else 3
            if verified: confirmed_count += 1
        else:
            confirmed_count += 1

        existing = conn.execute(
            "SELECT id,value,value_min,value_max,sample_count,value_stddev "
            "FROM market_kpi WHERE kpi_id=? AND region=? AND year=?",
            (kpi_id, region, year)).fetchone()

        if existing:
            eid, old_val, old_min, old_max, n, old_std = existing
            n = n or 1; new_n = n + 1
            new_val = (old_val * n + vmid) / new_n
            delta = vmid - old_val; delta2 = vmid - new_val
            old_m2 = ((old_std or 0)**2)*(n-1)
            new_m2 = old_m2 + delta*delta2
            new_std = math.sqrt(new_m2/(new_n-1)) if new_n>1 else 0
            mins = [x for x in [old_min,kpi.get('value_min'),vmid] if x is not None]
            maxs = [x for x in [old_max,kpi.get('value_max'),vmid] if x is not None]
            conn.execute("""UPDATE market_kpi SET
                value=?,value_min=?,value_max=?,sample_count=?,value_stddev=?,
                credibility=MAX(credibility,?),confirmed=MAX(confirmed,?),
                ingredient_tag=COALESCE(ingredient_tag,?),updated_at=? WHERE id=?""",
                (new_val,min(mins) if mins else None,max(maxs) if maxs else None,
                 new_n,new_std,credibility,confirmed,ingredient_tag,
                 datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),eid))
            updated += 1
            logging.debug(f'UPDATE {kpi_id} n={new_n} val={new_val:.3f}±{new_std:.3f}')
        else:
            conn.execute("""INSERT INTO market_kpi
                (id,region,country,species,production_stage,kpi_id,value,value_min,value_max,
                 unit,year,credibility,source_type,source_url,source_title,raw_text,language,
                 confirmed,updated_at,sample_count,value_stddev,ingredient_tag)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                str(uuid.uuid4()),region,
                'CN' if region.startswith('CN') else
                'SEA' if region.startswith('SEA') else
                'TW' if region.startswith('TW') else 'GLOBAL',
                species,kpi.get('condition',''),kpi_id,
                vmid,kpi.get('value_min'),kpi.get('value_max'),
                kpi.get('unit','') or 'unknown',year,credibility,
                'gov_stats' if is_fao else 'academic_background',
                url,title,f"auto_v5|{kpi.get('condition','')}",
                'zh-CN',confirmed,
                datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                1,None,ingredient_tag))
            inserted += 1

    if inserted+updated > 0: conn.commit()
    return inserted, updated, confirmed_count

def write_ingredient_evidence(conn, ingredient, species, region, kpis, url, title):
    region = normalize_region(region)
    inserted = 0
    for kpi in kpis:
        effect = kpi.get('treatment_value')
        if effect is None: continue
        ctrl = kpi.get('control_value')
        impv = round((effect-ctrl)/ctrl*100,2) if ctrl and ctrl!=0 else None
        conn.execute("""INSERT OR IGNORE INTO ingredient_evidence
            (id,ingredient,species,region,kpi_id,
             effect_size,effect_unit,control_value,treatment_value,improvement_pct,
             year,study_type,credibility,source_url,source_title,raw_text,confirmed,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            str(uuid.uuid4()),ingredient,species,region,kpi.get('kpi','unknown'),
            effect,kpi.get('unit','') or 'unknown',ctrl,effect,impv,
            kpi.get('year',2024),kpi.get('study_type','field_trial'),
            kpi.get('credibility',3),url,title,kpi.get('raw_text',''),
            1,datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')))
        inserted += 1
    if inserted > 0: conn.commit()
    return inserted

def query_kpi_stats(conn, species, region, kpi_name):
    region = normalize_region(region)
    kpi_id = f"{kpi_name}_{species}_{region.lower()}"
    rows = conn.execute("""
        SELECT value,value_min,value_max,sample_count,value_stddev,year,unit,credibility
        FROM market_kpi WHERE kpi_id=? AND confirmed=1
        ORDER BY credibility DESC,year DESC""",(kpi_id,)).fetchall()
    if not rows: return None
    vals = [r[0] for r in rows]
    return {
        'kpi_id':kpi_id,'mean':round(sum(vals)/len(vals),4),
        'stddev':round(rows[0][4] or 0,4),
        'min':min(r[1] or r[0] for r in rows),
        'max':max(r[2] or r[0] for r in rows),
        'sample_count':sum(r[3] or 1 for r in rows),
        'unit':rows[0][6],'years':sorted(set(r[5] for r in rows)),
        'credibility':rows[0][7],
    }

def compare_regions(conn, species, kpi_name, regions):
    """Bot支援：華北vs東北vs馬來西亞 FCR比較"""
    result = {}
    for r in regions:
        s = query_kpi_stats(conn, species, r, kpi_name)
        if s: result[r] = s
    return result


# ── 匯出 TXT（供 R2 + RAGFlow）───────────────────────────
def export_species_txt(conn, species, region):
    rows = conn.execute(
        """SELECT kpi_id, value, unit, year, credibility, source_title
           FROM market_kpi WHERE species=? AND region=? AND confirmed=1
           ORDER BY credibility DESC, year DESC""",
        (species, region)).fetchall()
    if not rows:
        return None
    lines = [f"# {species} / {region} — {datetime.now():%Y-%m-%d}"]
    for r in rows:
        lines.append(f"{r[0]}: {r[1]} {r[2]} ({r[3]}) cred={r[4]} src={r[5] or 'N/A'}")
    fname = f"market_{datetime.now():%Y-%m-%d}_{species}_{region}.txt"
    fpath = os.path.join(EXPORT_DIR, fname)
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return fpath

# ── R2 同步 ───────────────────────────────────────────────
def sync_to_r2(export_paths):
    try:
        import boto3
        s3 = boto3.client('s3',
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY,
            aws_secret_access_key=R2_SECRET_KEY,
            region_name='auto')
        for fpath in export_paths:
            if fpath and os.path.exists(fpath):
                key = 'market/' + os.path.basename(fpath)
                s3.upload_file(fpath, R2_BUCKET, key)
                logging.info(f'R2 ↑ {key}')
    except Exception as e:
        logging.warning(f'R2 sync fail: {e}')

# ── 主循環 ────────────────────────────────────────────────
def run_ingredient_collection(conn, visited_urls, visited_fingerprints):
    """核心原料論文搜尋模組"""
    total = 0
    for cfg in INGREDIENT_SEARCHES:
        ingredient = cfg['ingredient']
        logging.info(f'=== Ingredient: {ingredient} ===')
        for query in cfg['queries']:
            results = multi_search(query)
            time.sleep(SLEEP_QUERY)
            for r in results:
                url   = r.get('url','')
                title = r.get('title','')
                raw   = r.get('raw','')
                if not url: continue
                h = hashlib.md5(url.encode()).hexdigest()
                if h in visited_urls: continue
                visited_urls.add(h)
                full_text = scrape_url(url) or raw
                if not full_text or len(full_text) < 100: continue
                fp = content_fingerprint(full_text)
                if fp in visited_fingerprints: continue
                visited_fingerprints.add(fp)
                # 原料論文推兩個向量庫
                push_to_chromadb(full_text, url, title,
                                  {'ingredient': ingredient, 'source': r.get('source','')})
                push_to_ragflow(full_text, url, title)
                for species in cfg['species_targets']:
                    kpis = qwen_extract_ingredient(full_text, ingredient, species)
                    if kpis:
                        n = write_ingredient_evidence(
                            conn, ingredient, species, 'GLOBAL', kpis, url, title)
                        if n > 0:
                            total += n
                            logging.info(f'  Evidence {ingredient}/{species} +{n}')
    return total

_fao_fetched = set()  # 每輪 reset，見 main()

def process_species(conn, species, region, target_kpis,
                    visited_urls, visited_fingerprints):
    """單一物種的完整搜尋→抓取→抽取→入庫流程"""
    summary    = get_db_summary(conn, species, region, target_kpis)
    missing    = summary['missing']
    searched_q = []
    sp_new = sp_upd = sp_conf = 0
    sp_detail  = []

    logging.info(f'{species}/{region}: have={summary["have"]}, missing={missing}')

    # ── A. FAO STAT 直拉（每個 species 全程只拉一次）────────
    if species in FAO_SPECIES_MAP and species not in _fao_fetched:
        _fao_fetched.add(species)
        for dataset, item_name in FAO_SPECIES_MAP[species]:
            fao_recs = fao_fetch(dataset, item_name)
            if fao_recs:
                kpis = fao_to_kpi(fao_recs, species, region)
                n, u, c = write_to_db(conn, species, region, kpis,
                                     f'{FAO_API_BASE}/data/{dataset}',
                                     f'FAOSTAT {item_name}')
                sp_new += n; sp_upd += u; sp_conf += c
                if n > 0:
                    logging.info(f'  🌐 FAO {species} +{n}')
        time.sleep(1)
    elif species in FAO_SPECIES_MAP:
        logging.debug(f'FAO skip {species} (already fetched this run)')

    # 檢查樣本數：即使 KPI 齊全，樣本數不足3仍繼續累積
    min_samples = conn.execute(
        "SELECT MIN(COALESCE(sample_count,1)) FROM market_kpi "
        "WHERE species=? AND region=? AND confirmed=1",
        (species, region)).fetchone()[0] or 0

    if not missing and min_samples >= 2:
        logging.info(f'  → {species}/{region} 足夠(min_samples={min_samples})，跳搜尋')
        return sp_new, sp_upd, sp_conf, sp_detail

    if not missing:
        logging.info(f'  → {species}/{region} KPI齊全但樣本數不足(min={min_samples})，繼續累積')

    # ── B. 多源搜尋 + AI判讀 + 智慧深爬 ─────────────────
    queries = qwen_gen_queries(species, region, missing, summary, searched_q)
    all_extracted_kpis = []

    for query in queries:
        searched_q.append(query)
        results = multi_search(query, target_kpis)
        time.sleep(SLEEP_QUERY)

        for r in results:
            url      = r.get('url', '')
            title    = r.get('title', '')
            snippet  = r.get('snippet', '')
            raw      = r.get('raw', '')

            if not url:
                continue

            url_hash = hashlib.md5(url.encode()).hexdigest()
            if url_hash in visited_urls:
                continue
            visited_urls.add(url_hash)

            # AI 頁面價值判讀
            value_score = qwen_page_value(snippet or raw[:500], species, target_kpis)
            if value_score == 'none':
                logging.debug(f'  ⛔ Skip (none value): {url[:55]}')
                continue

            # 取得完整內容
            full_text = raw if (raw and len(raw) > 500) else ''
            if not full_text or value_score == 'high':
                # high價值 或 raw不足 → 深爬
                full_text = scrape_url(url) or raw

            if not full_text or len(full_text) < 100:
                continue

            # 內容指紋去重
            fp = content_fingerprint(full_text)
            if fp in visited_fingerprints:
                logging.debug(f'  ⛔ Dup content: {url[:55]}')
                continue
            visited_fingerprints.add(fp)

            # Qwen 抽取
            kpis = qwen_extract(full_text, species)
            if kpis:
                try:
                    n, u, c = write_to_db(conn, species, region, kpis, url, title, full_text)
                    sp_new += n; sp_upd += u; sp_conf += c
                    all_extracted_kpis.extend([k.get('kpi') for k in kpis])
                except Exception as db_err:
                    logging.warning(f'DB write skip: {db_err} | {url[:50]}')
                if n > 0:
                    logging.info(f'  ✅ {species} +{n}(✓{c}) | {url[:55]}')
                    sp_detail.append(f'{species}: +{n}(✓{c})')
                    # 同步寫入 ChromaDB
                    push_to_chromadb(full_text, url, title, {
                        'species': species, 'region': region,
                        'topic': species, 'category': 'A',
                        'category_label': 'A=field_trial',
                        'strategic_value': 'self_validation',
                        'quality_score': 3,
                        'year': str(datetime.now().year),
                    })

            # ── C. 參考文獻遞迴追蹤 ──────────────────────
            if full_text and len(full_text) > 500:
                refs = extract_refs(full_text)
                for ref_url in refs[:2]:
                    ref_hash = hashlib.md5(ref_url.encode()).hexdigest()
                    if ref_hash in visited_urls:
                        continue
                    visited_urls.add(ref_hash)
                    ref_text = scrape_url(ref_url)
                    if ref_text:
                        ref_fp = content_fingerprint(ref_text)
                        if ref_fp not in visited_fingerprints:
                            visited_fingerprints.add(ref_fp)
                            ref_kpis = qwen_extract(ref_text, species)
                            if ref_kpis:
                                n2, u2, c2 = write_to_db(
                                    conn, species, region,
                                    ref_kpis, ref_url,
                                    f'ref from {title}', ref_text)
                                sp_new += n2; sp_upd += u2; sp_conf += c2
                                if n2 + u2 > 0:
                                    logging.info(f'  📎 ref +{n2} upd={u2} | {ref_url[:50]}')

    # ── D. 動態查詢擴展 ──────────────────────────────────
    summary2  = get_db_summary(conn, species, region, target_kpis)
    missing2  = summary2['missing']
    if missing2:
        extra_q = qwen_expand_queries(
            list(set(all_extracted_kpis)), missing2, species, region)
        for eq in extra_q:
            if eq in searched_q:
                continue
            searched_q.append(eq)
            logging.info(f'  🔄 Expand query: {eq}')
            results2 = multi_search(eq, target_kpis)
            time.sleep(SLEEP_QUERY)
            for r in results2:
                url   = r.get('url', '')
                title = r.get('title', '')
                raw   = r.get('raw', '')
                if not url:
                    continue
                url_hash = hashlib.md5(url.encode()).hexdigest()
                if url_hash in visited_urls:
                    continue
                visited_urls.add(url_hash)
                full_text = scrape_url(url) or raw
                if full_text and len(full_text) > 100:
                    fp = content_fingerprint(full_text)
                    if fp not in visited_fingerprints:
                        visited_fingerprints.add(fp)
                        kpis = qwen_extract(full_text, species)
                        if kpis:
                            n, u, c = write_to_db(conn, species, region,
                                               kpis, url, title, full_text)
                            sp_new += n; sp_upd += u; sp_conf += c
                            if n + u > 0:
                                logging.info(f'  🔄 Expanded +{n} upd={u} | {url[:55]}')

    return sp_new, sp_upd, sp_conf, sp_detail

def main():
    setup_logging()
    logging.info('=' * 60)
    logging.info('auto_collect_v5 START — 智慧型多源搜尋引擎')
    if not load_api_keys():
        tg('❌ API key 讀取失敗')
        return

    conn = sqlite3.connect(DB_PATH)
    visited_urls         = set()
    visited_fingerprints = set()
    total_new = total_upd = total_conf = 0
    start_time = time.time()
    round_num  = 0
    exported_paths = []

    tg(f'🚀 <b>auto_collect_v5 啟動</b>\n'
       f'引擎：Tavily + SemanticScholar + Firecrawl Search\n'
       f'爬蟲：Crawl4AI → Scrapling → Firecrawl\n'
       f'判讀：Qwen3.6 頁面價值預判 + 動態查詢擴展\n'
       f'物種：{len(ALL_SPECIES)} 個 | 預計 {MAX_HOURS}h')

    while True:
        elapsed = (time.time() - start_time) / 3600
        if elapsed > MAX_HOURS:
            break

        round_num += 1
        _fao_fetched.clear()  # 每輪重置，允許重新拉 FAO
        logging.info(f'=== Round {round_num} | {elapsed:.1f}h ===')
        round_new = round_upd = round_conf = 0
        round_detail   = []

        for species, region, target_kpis in ALL_SPECIES:
            n, u, c, detail = process_species(
                conn, species, region, target_kpis,
                visited_urls, visited_fingerprints)
            round_new += n; round_upd += u; round_conf += c
            round_detail.extend(detail)
            total_new += n; total_upd += u; total_conf += c

            # 匯出 TXT
            fpath = export_species_txt(conn, species, region)
            if fpath:
                exported_paths.append(fpath)

            logging.info(f'{species} done: +{n} confirmed={c}')
            time.sleep(SLEEP_SPECIES)

        # R2 同步
        if exported_paths:
            sync_to_r2(exported_paths)
            exported_paths.clear()

        # 輪次結束統計
        total_rows  = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
        confirmed_r = conn.execute('SELECT COUNT(*) FROM market_kpi WHERE confirmed=1').fetchone()[0]
        pending     = conn.execute('SELECT COUNT(*) FROM market_kpi WHERE confirmed=0').fetchone()[0]
        detail_str  = '\n'.join(round_detail[:10]) if round_detail else '本輪無新增'

        tg(f'📊 <b>Round {round_num} 完成</b>\n'
           f'已運行 {elapsed:.1f}h\n'
           f'本輪: +{round_inserted}筆 (✓{round_confirmed} verified)\n'
           f'{detail_str}\n'
           f'DB: {total_rows}筆 | ✅{confirmed_r} / ⏳{pending}\n'
           f'URL去重池: {len(visited_urls)} | 內容指紋: {len(visited_fingerprints)}')

        logging.info(f'Round {round_num} done. DB={total_rows} +{round_inserted}')
        logging.info(f'Sleeping {SLEEP_ROUND}s...')
        time.sleep(SLEEP_ROUND)

    elapsed    = (time.time() - start_time) / 3600
    total_rows = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
    conn.close()
    tg(f'🏁 <b>v5 完成</b>\n'
       f'{elapsed:.1f}h | {round_num} 輪\n'
       f'新增: {total_inserted} | Verified: {total_confirmed}\n'
       f'DB: {total_rows}筆')
    logging.info('DONE')

if __name__ == '__main__':
    # ChangeDetection.io 觸發模式
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', default='full',
                        choices=['full', 'single', 'triggered'],
                        help='full=全量, single=單物種, triggered=ChangeDetection觸發')
    parser.add_argument('--species', default='', help='single模式指定物種')
    parser.add_argument('--region',  default='CN_all', help='single模式指定地區')
    args = parser.parse_args()

    try:
        if args.mode == 'triggered':
            # ChangeDetection → Webhook → 觸發單輪收集
            setup_logging()
            load_api_keys()
            conn = sqlite3.connect(DB_PATH)
            visited_urls = set()
            visited_fingerprints = set()
            tg('🔔 <b>ChangeDetection 觸發收集</b>')
            for species, region, target_kpis in ALL_SPECIES:
                n, u, c, _ = process_species(
                    conn, species, region, target_kpis,
                    visited_urls, visited_fingerprints)
                if n + u > 0:
                    fpath = export_species_txt(conn, species, region)
                    if fpath:
                        sync_to_r2([fpath])
            conn.close()
        elif args.mode == 'single' and args.species:
            setup_logging()
            load_api_keys()
            conn = sqlite3.connect(DB_PATH)
            target = next(
                ((s, r, k) for s, r, k in ALL_SPECIES
                 if s == args.species and r == args.region), None)
            if not target:
                DEFAULT_KPIS = {
                    'broiler': ['FCR','ADG','mortality'],
                    'finisher_pig': ['FCR','ADG','mortality'],
                    'beef_cattle': ['FCR','ADG','mortality'],
                    'layer_chicken': ['FCR','egg_rate','mortality'],
                    'meat_sheep': ['FCR','ADG','mortality'],
                    'shrimp': ['FCR','survival','mortality'],
                }
                kpis = DEFAULT_KPIS.get(args.species, ['FCR','ADG','mortality'])
                target = (args.species, args.region, kpis)
                logging.info(f'Dynamic target: {target}')
            if target:
                n, u, c, _ = process_species(conn, *target, set(), set())
                tg(f'✅ single {args.species}/{args.region}: new={n} upd={u} conf={c}')
            conn.close()
        else:
            main()
    except KeyboardInterrupt:
        logging.info('Interrupted.')
        tg('⚠️ v5 手動中止')
    except Exception as e:
        logging.error(f'Fatal: {e}', exc_info=True)
        tg(f'❌ <b>v5 崩潰</b>\n{e}')
