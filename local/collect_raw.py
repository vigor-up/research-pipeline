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
    # 豬
    ('finisher_pig', 'CN_northeast', ['FCR','ADG','mortality']),
    ('finisher_pig', 'CN_north',     ['FCR','ADG','mortality']),
    ('finisher_pig', 'CN_south',     ['FCR','ADG','mortality']),
    ('finisher_pig', 'CN_central',   ['FCR','ADG','mortality']),
    ('finisher_pig', 'SEA_malaysia', ['FCR','ADG','mortality']),
    ('finisher_pig', 'SEA_vietnam',  ['FCR','ADG','mortality']),
    ('breeding_sow', 'CN_northeast', ['litter_size','mortality']),
    ('breeding_sow', 'CN_north',     ['litter_size','mortality']),
    # 牛
    ('beef_cattle',  'CN_northeast', ['FCR','ADG','mortality']),
    ('beef_cattle',  'CN_north',     ['FCR','ADG','mortality']),
    ('beef_cattle',  'CN_southwest', ['FCR','ADG','mortality']),
    ('beef_cattle',  'SEA_malaysia', ['FCR','ADG','mortality']),
    ('dairy_cow',    'CN_northeast', ['milk_yield','FCR','mortality']),
    ('dairy_cow',    'CN_north',     ['milk_yield','FCR','mortality']),
    # 羊
    ('meat_sheep',   'CN_northeast', ['FCR','ADG','mortality']),
    ('meat_sheep',   'CN_northwest', ['FCR','ADG','mortality']),
    ('meat_goat',    'CN_south',     ['FCR','ADG','mortality']),
    ('dairy_goat',   'CN_all',       ['milk_yield','FCR','mortality']),
    # 雞
    ('broiler',      'CN_northeast', ['FCR','ADG','mortality']),
    ('broiler',      'CN_south',     ['FCR','ADG','mortality']),
    ('broiler',      'SEA_malaysia', ['FCR','ADG','mortality']),
    ('broiler',      'SEA_vietnam',  ['FCR','ADG','mortality']),
    ('layer_chicken','CN_northeast', ['FCR','egg_rate','mortality']),
    ('layer_chicken','CN_north',     ['FCR','egg_rate','mortality']),
    ('layer_chicken','CN_south',     ['FCR','egg_rate','mortality']),
    ('layer_chicken','SEA_malaysia', ['FCR','egg_rate','mortality']),
    ('duck',         'CN_south',     ['FCR','ADG','mortality']),
    ('duck',         'CN_east',      ['FCR','ADG','mortality']),
    # 水產
    ('shrimp',       'CN_south',     ['FCR','survival','mortality']),
    ('shrimp',       'SEA_thailand', ['FCR','survival','mortality']),
    ('shrimp',       'SEA_vietnam',  ['FCR','survival','mortality']),
    ('shrimp',       'SEA_malaysia', ['FCR','survival','mortality']),
    ('tilapia',      'CN_south',     ['FCR','ADG','survival']),
    ('tilapia',      'SEA_thailand', ['FCR','ADG','survival']),
    ('grouper',      'CN_south',     ['FCR','ADG','survival']),
    ('largemouth_bass','CN_south',   ['FCR','ADG','survival']),
    ('channel_catfish','CN_all',     ['FCR','ADG','survival']),
    ('grass_carp',   'CN_south',     ['FCR','ADG','survival']),
    # 羊
    ('meat_sheep',   'CN_northeast', ['FCR','ADG','mortality']),
]

# 核心原料論文查詢（機密，對外屏蔽）
INGREDIENT_QUERIES = [
    'policosanol poultry FCR growth performance trial 2023 2024',
    'octacosanol swine feed conversion ratio experiment',
    'astaxanthin shrimp FCR survival growth trial 2024',
    'astaxanthin broiler antioxidant performance study',
    'choline orthosilicic acid poultry bone strength trial',
    'ch-OSA laying hen egg shell quality 2023 2024',
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
