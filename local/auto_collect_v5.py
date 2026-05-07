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
    # 豬 — 各地區分開，價格/FCR差異顯著
    ('finisher_pig',   'CN_northeast', ['FCR','ADG','mortality','slaughter_wt']),
    ('finisher_pig',   'CN_north',     ['FCR','ADG','mortality','slaughter_wt']),
    ('finisher_pig',   'CN_east',      ['FCR','ADG','mortality','slaughter_wt']),
    ('finisher_pig',   'CN_south',     ['FCR','ADG','mortality','slaughter_wt']),
    ('finisher_pig',   'CN_central',   ['FCR','ADG','mortality','slaughter_wt']),
    ('finisher_pig',   'SEA_malaysia', ['FCR','ADG','mortality']),
    ('finisher_pig',   'SEA_vietnam',  ['FCR','ADG','mortality']),
    ('breeding_sow',   'CN_northeast', ['litter_size','mortality','FCR']),
    ('breeding_sow',   'CN_north',     ['litter_size','mortality','FCR']),
    # 牛
    ('beef_cattle',    'CN_northeast', ['FCR','ADG','mortality']),
    ('beef_cattle',    'CN_north',     ['FCR','ADG','mortality']),
    ('beef_cattle',    'CN_southwest', ['FCR','ADG','mortality']),
    ('beef_cattle',    'SEA_malaysia', ['FCR','ADG','mortality']),
    ('dairy_cow',      'CN_northeast', ['milk_yield','FCR','mortality','mastitis_loss']),
    ('dairy_cow',      'CN_north',     ['milk_yield','FCR','mortality']),
    ('dairy_cow',      'CN_all',       ['milk_yield','FCR','mortality']),
    # 羊
    ('meat_sheep',     'CN_northeast', ['FCR','ADG','mortality']),
    ('meat_sheep',     'CN_northwest', ['FCR','ADG','mortality']),
    ('meat_goat',      'CN_south',     ['FCR','ADG','mortality']),
    ('dairy_goat',     'CN_all',       ['milk_yield','FCR','mortality']),
    # 雞
    ('broiler',        'CN_northeast', ['FCR','ADG','mortality']),
    ('broiler',        'CN_south',     ['FCR','ADG','mortality']),
    ('broiler',        'SEA_malaysia', ['FCR','ADG','mortality']),
    ('broiler',        'SEA_vietnam',  ['FCR','ADG','mortality']),
    ('layer_chicken',  'CN_northeast', ['FCR','egg_rate','mortality']),
    ('layer_chicken',  'CN_north',     ['FCR','egg_rate','mortality']),
    ('layer_chicken',  'CN_south',     ['FCR','egg_rate','mortality']),
    ('layer_chicken',  'SEA_malaysia', ['FCR','egg_rate','mortality']),
    ('duck',           'CN_south',     ['FCR','ADG','mortality']),
    ('duck',           'CN_east',      ['FCR','ADG','mortality']),
    # 水產
    ('shrimp',         'CN_south',     ['FCR','survival','mortality']),
    ('shrimp',         'SEA_thailand', ['FCR','survival','mortality']),
    ('shrimp',         'SEA_vietnam',  ['FCR','survival','mortality']),
    ('shrimp',         'SEA_malaysia', ['FCR','survival','mortality']),
    ('tilapia',        'CN_south',     ['FCR','ADG','survival']),
    ('tilapia',        'SEA_thailand', ['FCR','ADG','survival']),
    ('grouper',        'CN_south',     ['FCR','ADG','survival']),
    ('largemouth_bass','CN_south',     ['FCR','ADG','survival']),
    ('channel_catfish','CN_all',       ['FCR','ADG','survival','mortality']),
    ('largemouth_catfish','CN_all',    ['FCR','ADG','survival']),
    ('grass_carp',     'CN_south',     ['FCR','ADG','survival']),
    ('carp',           'CN_all',       ['FCR','ADG','mortality']),
]

# ── 核心原料論文搜尋配置（機密）─────────────────────────
INGREDIENT_SEARCHES = [
    {
        'ingredient': 'policosanol',
        'queries': [
            'policosanol poultry FCR growth performance trial',
            'octacosanol swine feed conversion ratio experiment',
            'triacontanol broiler weight gain study 2023 2024',
            '二十八烷醇 肉雞 飼料轉化率 試驗',
            'policosanol pig ADG mortality field trial China',
        ],
        'species_targets': ['broiler','finisher_pig','beef_cattle','layer_chicken'],
    },
    {
        'ingredient': 'astaxanthin',
        'queries': [
            'astaxanthin shrimp FCR survival growth trial',
            'astaxanthin broiler pigmentation antioxidant performance',
            'astaxanthin laying hen egg quality yolk color 2023',
            '蝦青素 對蝦 生長性能 試驗 2023 2024',
            'astaxanthin fish feed conversion immune response',
        ],
        'species_targets': ['shrimp','broiler','layer_chicken','tilapia','grouper'],
    },
    {
        'ingredient': 'ch_osa',
        'queries': [
            'choline stabilized orthosilicic acid poultry bone strength',
            'ch-OSA laying hen egg shell quality trial',
            'silicon bioavailable broiler tibia ash experiment',
            'ch-OSA dairy cow milk production hoof health',
            'orthosilicic acid pig growth performance experiment',
        ],
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
INGREDIENT_TAGS_MAP = {
    'policosanol': ['octacosanol','triacontanol','policosanol','二十八烷醇','三十烷醇','二十六烷醇'],
    'astaxanthin': ['astaxanthin','蝦青素','蝦紅素'],
    'ch_osa':      ['ch-osa','orthosilicic','silicon','矽酸膽鹼'],
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
要求：具體含物種+KPI+地區+年份，優先2023-2025年數據。
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

def qwen_gen_queries(species, region, missing_kpis, db_summary, searched_queries=None):
    if not missing_kpis:
        return [f'{species.replace("_"," ")} FCR ADG China {region} 2024']
    prompt = GAP_PROMPT.format(
        db_summary=json.dumps(db_summary, ensure_ascii=False),
        species=species, region=region,
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
    return [f'{species.replace("_"," ")} {" ".join(missing_kpis[:2])} China 2024']

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
        r = requests.get(url, params=params, timeout=20)
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
def search_tavily(query, max_results=5):
    if not TAVILY_KEY:
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
            timeout=20)
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
            ex.submit(search_tavily, query, 5): 'tavily',
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
        page = Fetcher(auto_match=False).get(url, timeout=20)
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
    missing = [k for k in target_kpis if k.lower() not in have]
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
                kpi.get('unit',''),year,credibility,
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
            effect,kpi.get('unit',''),ctrl,effect,impv,
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
                for species in cfg['species_targets']:
                    kpis = qwen_extract_ingredient(full_text, ingredient, species)
                    if kpis:
                        n = write_ingredient_evidence(
                            conn, ingredient, species, 'GLOBAL', kpis, url, title)
                        if n > 0:
                            total += n
                            logging.info(f'  Evidence {ingredient}/{species} +{n}')
    return total

def process_species(conn, species, region, target_kpis,
                    visited_urls, visited_fingerprints):
    """單一物種的完整搜尋→抓取→抽取→入庫流程"""
    summary    = get_db_summary(conn, species, region, target_kpis)
    missing    = summary['missing']
    searched_q = []
    sp_new = sp_upd = sp_conf = 0
    sp_detail  = []

    logging.info(f'{species}/{region}: have={summary["have"]}, missing={missing}')

    # ── A. FAO STAT 直拉（最高可信度）────────────────────
    if species in FAO_SPECIES_MAP:
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
        time.sleep(3)

    # 檢查樣本數：即使 KPI 齊全，樣本數不足3仍繼續累積
    min_samples = conn.execute(
        "SELECT MIN(COALESCE(sample_count,1)) FROM market_kpi "
        "WHERE species=? AND region=? AND confirmed=1",
        (species, region)).fetchone()[0] or 0

    if not missing and min_samples >= 3:
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
                n, u, c = write_to_db(conn, species, region, kpis, url, title, full_text)
                sp_new += n; sp_upd += u; sp_conf += c
                all_extracted_kpis.extend([k.get('kpi') for k in kpis])
                if n > 0:
                    logging.info(f'  ✅ {species} +{n}(✓{c}) | {url[:55]}')
                    sp_detail.append(f'{species}: +{n}(✓{c})')

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
