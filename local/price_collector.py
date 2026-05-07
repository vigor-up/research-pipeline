# -*- coding: utf-8 -*-
"""
price_collector.py
定向價格爬蟲模組 - 整合進 auto_collect_v4
每日自動抓取豬/雞/牛/羊/魚/蝦現貨價格 + 飼料原料期貨
"""

import sqlite3, uuid, json, time, logging, requests, re
from datetime import datetime
from scrapling import Fetcher

QWEN_URL  = 'http://localhost:1234/v1/chat/completions'
QWEN_MODEL = 'qwen3.6-35b'

PRICE_EXTRACT_PROMPT = """從以下網頁文字中抽取{species}的現貨價格數據。
只抽取今日/最新的具體價格數字。
輸出純JSON數組：
[{{
  "item": "品項名稱",
  "price": 數字,
  "unit": "元/kg或元/斤或元/噸",
  "region": "地區（如全國/廣東/山東，無則填CN_all）",
  "date": "日期字串（如2026-05-06，無則填null）",
  "confidence": "high或medium或low"
}}]
無價格數據回覆: []
文字（前4000字）：
{text}"""

PRICE_SOURCES = [
    # 生豬
    {
        'species': 'finisher_pig', 'kpi_prefix': 'spot_price_pig',
        'unit_std': 'CNY/kg', 'region': 'CN_all', 'credibility': 4,
        'urls': [
            ('新牧網生豬', 'https://www.xumuwang.com/pigprice/'),
            ('搜豬網行情', 'https://www.soozhu.com/market/price/'),
        ]
    },
    # 雞蛋
    {
        'species': 'layer_chicken', 'kpi_prefix': 'spot_price_egg',
        'unit_std': 'CNY/kg', 'region': 'CN_all', 'credibility': 4,
        'urls': [
            ('新牧網雞蛋', 'https://www.xumuwang.com/eggprice/'),
            ('中禽協雞蛋', 'https://www.caaa.cn/market/egg/'),
        ]
    },
    # 肉雞
    {
        'species': 'broiler', 'kpi_prefix': 'spot_price_broiler',
        'unit_std': 'CNY/kg', 'region': 'CN_all', 'credibility': 4,
        'urls': [
            ('新牧網肉雞', 'https://www.xumuwang.com/broilerprice/'),
        ]
    },
    # 牛
    {
        'species': 'beef_cattle', 'kpi_prefix': 'spot_price_cattle',
        'unit_std': 'CNY/kg', 'region': 'CN_all', 'credibility': 4,
        'urls': [
            ('新牧網牛價', 'https://www.xumuwang.com/cattleprice/'),
        ]
    },
    # 羊
    {
        'species': 'meat_sheep', 'kpi_prefix': 'spot_price_sheep',
        'unit_std': 'CNY/kg', 'region': 'CN_all', 'credibility': 4,
        'urls': [
            ('新牧網羊價', 'https://www.xumuwang.com/sheepprice/'),
        ]
    },
    # 蝦
    {
        'species': 'shrimp', 'kpi_prefix': 'spot_price_shrimp',
        'unit_std': 'CNY/kg', 'region': 'CN_south', 'credibility': 4,
        'urls': [
            ('水產門戶蝦', 'https://www.shuichan.cc/price_list-0-4.html'),
        ]
    },
    # 羅非魚
    {
        'species': 'tilapia', 'kpi_prefix': 'spot_price_tilapia',
        'unit_std': 'CNY/kg', 'region': 'CN_south', 'credibility': 4,
        'urls': [
            ('水產門戶羅非', 'https://www.shuichan.cc/price_list-0-2.html'),
        ]
    },
    # 加州鱸
    {
        'species': 'largemouth_bass', 'kpi_prefix': 'spot_price_bass',
        'unit_std': 'CNY/kg', 'region': 'CN_south', 'credibility': 4,
        'urls': [
            ('水產門戶鱸魚', 'https://www.shuichan.cc/price_list-0-1.html'),
        ]
    },
    # 石斑魚
    {
        'species': 'grouper', 'kpi_prefix': 'spot_price_grouper',
        'unit_std': 'CNY/kg', 'region': 'CN_south', 'credibility': 4,
        'urls': [
            ('水產門戶石斑', 'https://www.shuichan.cc/price_list-0-3.html'),
        ]
    },
    # 豆粕
    {
        'species': 'feed_ingredient', 'kpi_prefix': 'spot_price_soybean_meal',
        'unit_std': 'CNY/ton', 'region': 'CN_all', 'credibility': 4,
        'urls': [
            ('飼料網豆粕', 'http://www.feedtrade.com.cn/market/soybean_meal.html'),
            ('大北農豆粕', 'https://www.dbn.com.cn/price/soybean/'),
        ]
    },
    # 玉米
    {
        'species': 'feed_ingredient', 'kpi_prefix': 'spot_price_corn',
        'unit_std': 'CNY/ton', 'region': 'CN_all', 'credibility': 4,
        'urls': [
            ('飼料網玉米', 'http://www.feedtrade.com.cn/market/corn.html'),
            ('大北農玉米', 'https://www.dbn.com.cn/price/corn/'),
        ]
    },
]

SKIP_DOMAINS = ['researchgate.net', 'jstor.org']

def scrape(url):
    try:
        page = Fetcher(auto_match=False).get(url, timeout=20)
        text = page.get_all_text(ignore_tags=('script','style','nav','footer','header'))
        return text[:5000] if text else ''
    except Exception:
        pass
    try:
        r = requests.get(url, timeout=15,
            headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        return r.text[:5000] if r.status_code == 200 else ''
    except Exception:
        return ''

def qwen_extract_price(text, species):
    if not text or len(text) < 50:
        return []
    prompt = PRICE_EXTRACT_PROMPT.format(species=species, text=text[:4000])
    try:
        resp = requests.post(QWEN_URL, json={
            'model': QWEN_MODEL,
            'messages': [{'role':'user','content':prompt}],
            'temperature': 0.1, 'max_tokens': 800}, timeout=60)
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            s = content.find('['); e = content.rfind(']')+1
            if s >= 0 and e > s:
                return json.loads(content[s:e])
    except Exception as ex:
        logging.warning(f'Qwen price extract: {ex}')
    return []

def normalize_price(price, unit):
    """統一換算為 CNY/kg"""
    if not price:
        return None
    price = float(price)
    unit = (unit or '').lower()
    if '斤' in unit:
        return round(price * 2, 2)
    if '噸' in unit or 'ton' in unit:
        return round(price / 1000, 2)
    return price  # 已是 CNY/kg

def write_price(conn, species, kpi_prefix, region, credibility,
                item, price_kg, unit_orig, src_region, date_str, url, src_name):
    today_year = int(date_str[:4]) if date_str and len(date_str) >= 4 else 2026
    region_use = src_region if src_region and src_region != 'CN_all' else region
    safe_item  = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '', item)[:20]
    kpi_id     = f"{kpi_prefix}_{safe_item}_{region_use.lower()}"

    exists = conn.execute(
        "SELECT id FROM market_kpi WHERE kpi_id=? AND year=?",
        (kpi_id, today_year)).fetchone()
    if exists:
        return 0

    conn.execute("""INSERT INTO market_kpi
        (id,region,country,species,production_stage,kpi_id,
         value,unit,year,credibility,source_type,
         source_url,source_title,raw_text,language,confirmed,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        str(uuid.uuid4()), region_use, 'CN',
        species, 'market_price', kpi_id,
        price_kg, 'CNY/kg', today_year,
        credibility, 'industry_media',
        url, src_name,
        f'{item} {price_kg}CNY/kg ({unit_orig}) {date_str}',
        'zh-CN', 1,
        datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')))
    return 1

def run_price_collection(conn):
    """主入口：在 auto_collect_v4 的每輪開始時呼叫"""
    total = 0
    detail = []
    logging.info('=== Price Collection Start ===')

    for src in PRICE_SOURCES:
        species     = src['species']
        kpi_prefix  = src['kpi_prefix']
        region      = src['region']
        credibility = src['credibility']
        sp_count    = 0

        for src_name, url in src['urls']:
            text = scrape(url)
            if not text:
                logging.warning(f'  No content: {url[:60]}')
                continue

            prices = qwen_extract_price(text, species)
            if not prices:
                logging.info(f'  No prices extracted: {src_name}')
                continue

            for p in prices:
                if p.get('confidence') == 'low':
                    continue
                price_raw = p.get('price')
                unit_orig = p.get('unit', 'CNY/kg')
                price_kg  = normalize_price(price_raw, unit_orig)
                if not price_kg:
                    continue

                n = write_price(
                    conn, species, kpi_prefix, region, credibility,
                    p.get('item', species),
                    price_kg, unit_orig,
                    p.get('region', region),
                    p.get('date', ''),
                    url, src_name)
                sp_count += n

            time.sleep(5)

        if sp_count > 0:
            detail.append(f'{species}: +{sp_count}')
            total += sp_count
        logging.info(f'Price {species}: +{sp_count}')

    conn.commit()
    logging.info(f'=== Price Collection Done: +{total} ===')
    return total, detail


if __name__ == '__main__':
    # 獨立測試
    logging.basicConfig(level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s')
    DB_PATH = r'D:\LLM\knowledge\market\market_data.db'
    conn = sqlite3.connect(DB_PATH)
    total, detail = run_price_collection(conn)
    rows = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
    print(f'Done. +{total} price records. DB total: {rows}')
    conn.close()
