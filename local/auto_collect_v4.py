# -*- coding: utf-8 -*-
"""
auto_collect_v4.py
升級：FAO STAT API直拉 + Qwen二次驗證 + 參考文獻遞迴追蹤
credibility: FAO=5, 學術confirmed=4, web未驗證=3
"""

import sqlite3, uuid, json, time, logging, requests, hashlib, re
import sys, os
from datetime import datetime
from pathlib import Path
from scrapling import Fetcher

DB_PATH        = r'D:\LLM\knowledge\market\market_data.db'
LOG_PATH       = r'D:\LLM\workflows\research-pipeline-v2\logs\auto_collect_v4.log'
QWEN_URL       = 'http://localhost:1234/v1/chat/completions'
QWEN_MODEL     = 'qwen3.6-35b'
TELEGRAM_TOKEN = '8703702788:AAFKEiGmLYTAuFVG9GX-gRtVTUUyi-f_5mM'
TELEGRAM_CHAT  = 897274134
TAVILY_KEY     = None
SLEEP_QUERY    = 8
SLEEP_SPECIES  = 15
SLEEP_ROUND    = 1800
MAX_HOURS      = 14.5
MAX_RETRIES    = 3
RETRY_DELAY    = 15

# FAO STAT API 設定
FAO_API_BASE = 'https://fenixservices.fao.org/faostat/api/v1'
FAO_AREA_CN  = '351'  # China mainland

# FAO 物種對應
FAO_SPECIES_MAP = {
    'dairy_cow':      [('QL', 'Milk, whole fresh cow'),    ('QA', 'Cattle')],
    'beef_cattle':    [('QA', 'Cattle'),                   ('QL', 'Meat, cattle')],
    'finisher_pig':   [('QA', 'Pigs'),                     ('QL', 'Meat, pig')],
    'layer_chicken':  [('QA', 'Chickens'),                 ('QL', 'Eggs, hen, in shell')],
    'broiler':        [('QA', 'Chickens'),                 ('QL', 'Meat, chicken')],
    'meat_sheep':     [('QA', 'Sheep'),                    ('QL', 'Meat, sheep')],
    'meat_goat':      [('QA', 'Goats'),                    ('QL', 'Meat, goat')],
    'dairy_goat':     [('QA', 'Goats'),                    ('QL', 'Milk, whole fresh goat')],
    'shrimp':         [('QA', 'Shrimps, prawns'),          ('QL', 'Shrimps, prawns')],
    'tilapia':        [('QA', 'Tilapias nei'),             ('QL', 'Tilapias nei')],
}

ALL_SPECIES = [
    ('dairy_goat',        'CN_all',   ['FCR','ADG','milk_yield','mortality']),
    ('channel_catfish',   'CN_all',   ['FCR','ADG','survival','mortality']),
    ('largemouth_catfish','CN_all',   ['FCR','ADG','survival']),
    ('dairy_cow',         'CN_all',   ['milk_yield','FCR','mortality','mastitis_loss']),
    ('layer_chicken',     'CN_all',   ['FCR','egg_rate','mortality']),
    ('broiler',           'CN_all',   ['FCR','ADG','mortality']),
    ('shrimp',            'CN_south', ['FCR','survival','mortality']),
    ('beef_cattle',       'CN_north', ['FCR','ADG','mortality']),
    ('beef_cattle',       'CN_south', ['FCR','ADG','mortality']),
    ('finisher_pig',      'CN_north', ['FCR','ADG','mortality']),
    ('meat_sheep',        'CN_north', ['FCR','ADG','mortality']),
    ('tilapia',           'CN_south', ['FCR','ADG','survival']),
    ('grouper',           'CN_south', ['FCR','ADG','survival']),
    ('largemouth_bass',   'CN_south', ['FCR','ADG','survival']),
]

# ── Prompts ────────────────────────────────────────────
GAP_PROMPT = """你是動物營養市場研究員。
DB現有：{db_summary}
為以下物種生成4條搜索查詢（英文2條+中文2條）：
物種：{species}（{region}）缺少：{missing_kpis}
要求：具體含物種+KPI+地區+年份。
輸出純JSON數組：["q1","q2","q3","q4"]"""

EXTRACT_PROMPT = """從以下文字抽取{species}的生產KPI。
只抽取文中明確出現的數字，不推測。
輸出純JSON數組：
[{{"kpi":"fcr|adg|mortality|milk_yield|egg_rate|survival|litter_size|slaughter_wt|other","value_min":數字或null,"value_mid":數字,"value_max":數字或null,"unit":"單位","condition":"條件","metric_type":"baseline或disease_penalty","year":年份或null,"confidence":"high|medium|low","source_sentence":"原文中包含此數字的句子（20字內）"}}]
無數字回覆: []
文字：{text}"""

VERIFY_PROMPT = """以下KPI數據聲稱來自這段文字，請驗證：
KPI: {kpi_id} = {value} {unit}
原文句子: "{source_sentence}"
文字片段:
{text}

問題：原文句子是否真實出現在文字中？數字是否正確？
回覆純JSON：{{"verified": true或false, "reason": "一句話說明"}}"""

# ── 初始化 ─────────────────────────────────────────────
def setup_logging():
    Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.FileHandler(LOG_PATH, encoding='utf-8'),
                  logging.StreamHandler()])

def load_tavily_key():
    global TAVILY_KEY
    for enc in ('utf-8-sig','utf-8','cp950'):
        try:
            with open(r'D:\LLM\API key.txt', encoding=enc) as f:
                for line in f:
                    if 'TAVILY' in line.upper():
                        TAVILY_KEY = line.split('=')[-1].strip().strip('"').strip("'")
                        logging.info(f'Tavily ({enc}): {TAVILY_KEY[:8]}...')
                        return True
        except Exception:
            continue
    return False

def tg(msg):
    try:
        requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id':TELEGRAM_CHAT,'text':msg,'parse_mode':'HTML'}, timeout=10)
    except Exception as e:
        logging.warning(f'TG: {e}')

# ── FAO STAT API ───────────────────────────────────────
def fao_fetch(dataset, item_name, area=FAO_AREA_CN, years='2020,2021,2022,2023'):
    """直接從 FAO STAT 拉數據"""
    try:
        url = f'{FAO_API_BASE}/data/{dataset}'
        params = {
            'area': area,
            'element': '5510,5610,5320,5422',  # production, yield, stocks, slaughtered
            'year': years,
            'output_type': 'json',
        }
        r = requests.get(url, params=params, timeout=20)
        if r.status_code == 200:
            data = r.json()
            items = data.get('data', [])
            # 過濾目標品項
            matched = [i for i in items if item_name.lower() in i.get('Item','').lower()]
            logging.info(f'FAO {dataset}/{item_name}: {len(matched)} records')
            return matched
    except Exception as e:
        logging.warning(f'FAO API error: {e}')
    return []

def fao_to_kpi(fao_records, species, region='CN_all'):
    """FAO 記錄轉換為 KPI 格式"""
    kpis = []
    element_map = {
        'Yield': ('milk_yield', 'hg/An'),
        'Production': ('market_output', '1000 tonnes'),
        'Stocks': ('market_population', '1000 Head'),
        'Slaughtered': ('market_slaughter', '1000 Head'),
    }
    for rec in fao_records:
        element = rec.get('Element','')
        value   = rec.get('Value')
        year    = rec.get('Year')
        unit    = rec.get('Unit','')
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

# ── Qwen 呼叫 ──────────────────────────────────────────
def qwen_call(prompt, max_tokens=500, temperature=0.1):
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(QWEN_URL, json={
                'model': QWEN_MODEL,
                'messages': [{'role':'user','content':prompt}],
                'temperature': temperature,
                'max_tokens': max_tokens}, timeout=90)
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
        except Exception as e:
            logging.warning(f'Qwen attempt {attempt+1}: {e}')
        time.sleep(RETRY_DELAY)
    return ''

def qwen_gen_queries(species, region, missing_kpis, db_summary):
    if not missing_kpis:
        return [f'{species.replace("_"," ")} FCR ADG China {region} 2023 2024']
    prompt = GAP_PROMPT.format(
        db_summary=json.dumps(db_summary, ensure_ascii=False),
        species=species, region=region,
        missing_kpis=', '.join(missing_kpis))
    content = qwen_call(prompt, max_tokens=300, temperature=0.3)
    try:
        s = content.find('['); e = content.rfind(']')+1
        if s >= 0 and e > s:
            queries = json.loads(content[s:e])
            logging.info(f'Qwen queries {species}: {queries}')
            return queries[:4]
    except Exception:
        pass
    return [f'{species.replace("_"," ")} {" ".join(missing_kpis[:2])} China 2023']

def qwen_extract(text, species):
    if not text or len(text) < 100:
        return []
    prompt = EXTRACT_PROMPT.format(species=species, text=text[:3000])
    content = qwen_call(prompt, max_tokens=1200)
    try:
        s = content.find('['); e = content.rfind(']')+1
        if s >= 0 and e > s:
            return json.loads(content[s:e])
    except Exception:
        pass
    return []

def qwen_verify(kpi_id, value, unit, source_sentence, text):
    """二次驗證：確認數字真實存在於原文"""
    if not source_sentence or len(source_sentence) < 5:
        return False
    prompt = VERIFY_PROMPT.format(
        kpi_id=kpi_id, value=value, unit=unit,
        source_sentence=source_sentence, text=text[:2000])
    content = qwen_call(prompt, max_tokens=200)
    try:
        s = content.find('{'); e = content.rfind('}')+1
        if s >= 0 and e > s:
            result = json.loads(content[s:e])
            verified = result.get('verified', False)
            reason   = result.get('reason', '')
            logging.debug(f'Verify {kpi_id}: {verified} | {reason}')
            return verified
    except Exception:
        pass
    return False

# ── Tavily ─────────────────────────────────────────────
def tavily_search(query, max_results=5):
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post('https://api.tavily.com/search', json={
                'api_key': TAVILY_KEY, 'query': query,
                'max_results': max_results, 'search_depth': 'advanced',
                'include_raw_content': True}, timeout=30)
            if resp.status_code == 200:
                results = resp.json().get('results', [])
                logging.info(f'Tavily [{len(results)}] "{query[:55]}"')
                return results
        except Exception as e:
            logging.warning(f'Tavily: {e}')
        time.sleep(RETRY_DELAY)
    return []

# ── Scrapling ──────────────────────────────────────────
SKIP_DOMAINS = ['researchgate.net','jstor.org','sci-hub']

def scrape_url(url):
    if any(d in url for d in SKIP_DOMAINS):
        return ''
    try:
        page = Fetcher(auto_match=False).get(url, timeout=20)
        text = page.get_all_text(ignore_tags=('script','style','nav','footer','header'))
        return text[:6000] if text else ''
    except Exception:
        pass
    try:
        r = requests.get(url, timeout=15,
            headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        return r.text[:6000] if r.status_code == 200 else ''
    except Exception as e:
        logging.debug(f'Scrape fail {url[:50]}: {e}')
        return ''

# ── 參考文獻追蹤 ───────────────────────────────────────
def extract_refs(text):
    """從頁面文字中提取 DOI 或學術 URL"""
    dois  = re.findall(r'10\.\d{4,}/\S+', text)
    urls  = re.findall(r'https?://(?:doi\.org|pubmed\.ncbi|scholar\.google|cnki\.net)\S+', text)
    refs  = [f'https://doi.org/{d.rstrip(".,)")}' for d in dois[:5]]
    refs += [u.rstrip('.,)') for u in urls[:3]]
    return list(set(refs))

# ── DB ─────────────────────────────────────────────────
def get_db_summary(conn, species, region, target_kpis):
    rows = conn.execute(
        "SELECT kpi_id, value, confirmed FROM market_kpi WHERE species=? AND region=?",
        (species, region)).fetchall()
    have    = {r[0].split('_')[0] for r in rows if r[1] is not None}
    missing = [k for k in target_kpis if k.lower() not in have]
    return {'have': list(have), 'missing': missing, 'total': len(rows)}

def write_to_db(conn, species, region, kpis, url, title, text_for_verify=''):
    inserted = confirmed_count = 0
    for kpi in kpis:
        if kpi.get('confidence') == 'low': continue
        vmid = kpi.get('value_mid')
        if vmid is None: continue

        metric  = kpi.get('kpi','unknown')
        year    = kpi.get('year') or 2023
        kpi_id  = f"{metric}_{species}_{region.lower()}"
        is_fao  = kpi.get('fao_source', False)

        if conn.execute(
            "SELECT id FROM market_kpi WHERE kpi_id=? AND region=? AND year=?",
            (kpi_id, region, year)).fetchone():
            continue

        # 二次驗證（非FAO來源才需要驗證）
        confirmed = 1
        credibility = 5
        if not is_fao:
            source_sent = kpi.get('source_sentence','')
            verified = qwen_verify(kpi_id, vmid, kpi.get('unit',''),
                                   source_sent, text_for_verify)
            confirmed   = 1 if verified else 0
            credibility = 4 if verified else 3
            if verified:
                confirmed_count += 1

        conn.execute("""INSERT INTO market_kpi
            (id,region,country,species,production_stage,kpi_id,value,value_min,value_max,
             unit,year,credibility,source_type,source_url,source_title,raw_text,language,confirmed,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            str(uuid.uuid4()), region,
            'CN' if region.startswith('CN') else 'GLOBAL',
            species, kpi.get('condition',''), kpi_id,
            vmid, kpi.get('value_min'), kpi.get('value_max'),
            kpi.get('unit',''), year, credibility,
            'gov_stats' if is_fao else 'academic_background',
            url, title,
            f"auto_v4|verified={'fao' if is_fao else confirmed}|{kpi.get('condition','')}",
            'zh-CN', confirmed,
            datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')))
        inserted += 1

    if inserted > 0:
        conn.commit()
    return inserted, confirmed_count

# ── 主循環 ─────────────────────────────────────────────
def main():
    setup_logging()
    logging.info('='*60)
    logging.info('auto_collect_v4 START (FAO+二次驗證+參考追蹤)')
    if not load_tavily_key():
        tg('❌ Tavily key 讀取失敗')
        return

    conn = sqlite3.connect(DB_PATH)
    visited_urls = set()
    total_inserted = total_confirmed = 0
    start_time = time.time()
    round_num = 0

    tg(f'🧠 <b>auto_collect_v4 啟動</b>\n'
       f'新增：FAO API + 價格爬蟲 + Qwen二次驗證 + 參考追蹤\n'
       f'物種: {len(ALL_SPECIES)} 個 | 預計 {MAX_HOURS}h\n'
       f'每輪結束才推送 😴')

    while True:
        elapsed = (time.time() - start_time) / 3600
        if elapsed > MAX_HOURS: break

        round_num += 1
        logging.info(f'=== Round {round_num} | {elapsed:.1f}h ===')
        round_inserted = round_confirmed = 0
        round_detail = []

        # ── 價格收集（每輪優先執行）────────────────
        try:
            from price_collector import run_price_collection
            price_n, price_detail = run_price_collection(conn)
            if price_n > 0:
                round_inserted += price_n
                total_inserted += price_n
                round_detail.extend(price_detail)
                logging.info(f'Price collection: +{price_n}')
        except Exception as pe:
            logging.warning(f'Price collector error: {pe}')

        for species, region, target_kpis in ALL_SPECIES:
            summary = get_db_summary(conn, species, region, target_kpis)
            missing = summary['missing']
            logging.info(f'{species}/{region}: have={summary["have"]}, missing={missing}')

            sp_inserted = sp_confirmed = 0

            # ── A. FAO STAT 直拉 ──────────────────────
            if species in FAO_SPECIES_MAP:
                for dataset, item_name in FAO_SPECIES_MAP[species]:
                    fao_recs = fao_fetch(dataset, item_name)
                    if fao_recs:
                        kpis = fao_to_kpi(fao_recs, species, region)
                        n, c = write_to_db(conn, species, region, kpis,
                                           f'{FAO_API_BASE}/data/{dataset}',
                                           f'FAOSTAT {item_name}')
                        sp_inserted += n; sp_confirmed += c
                        if n > 0:
                            logging.info(f'  🌐 FAO {species} +{n}')
                time.sleep(3)

            # 全部已有且有FAO數據，跳Tavily
            if not missing and summary['total'] >= len(target_kpis):
                logging.info(f'  → {species} 足夠，跳Tavily')
                time.sleep(SLEEP_SPECIES)
                continue

            # ── B. Qwen生成查詢 + Tavily + Scrapling ──
            queries = qwen_gen_queries(species, region, missing, summary)

            for query in queries:
                results = tavily_search(query)
                time.sleep(SLEEP_QUERY)

                for r in results:
                    url   = r.get('url','')
                    title = r.get('title','')
                    url_hash = hashlib.md5(url.encode()).hexdigest()
                    if url_hash in visited_urls: continue
                    visited_urls.add(url_hash)

                    raw = r.get('raw_content','') or ''
                    if len(raw) < 300:
                        raw = scrape_url(url)

                    kpis = qwen_extract(raw, species)
                    if kpis:
                        n, c = write_to_db(conn, species, region,
                                           kpis, url, title, raw)
                        sp_inserted += n; sp_confirmed += c
                        if n > 0:
                            logging.info(f'  ✅ {species} +{n}(✓{c}) | {url[:55]}')

                    # ── C. 參考文獻遞迴追蹤 ──────────
                    if raw and len(raw) > 500:
                        refs = extract_refs(raw)
                        for ref_url in refs[:2]:  # 最多追2個
                            ref_hash = hashlib.md5(ref_url.encode()).hexdigest()
                            if ref_hash in visited_urls: continue
                            visited_urls.add(ref_hash)
                            ref_text = scrape_url(ref_url)
                            if ref_text:
                                ref_kpis = qwen_extract(ref_text, species)
                                if ref_kpis:
                                    n2, c2 = write_to_db(conn, species, region,
                                                         ref_kpis, ref_url,
                                                         f'ref from {title}', ref_text)
                                    sp_inserted += n2; sp_confirmed += c2
                                    if n2 > 0:
                                        logging.info(f'  📎 ref +{n2}(✓{c2}) | {ref_url[:50]}')

            round_inserted += sp_inserted
            round_confirmed += sp_confirmed
            total_inserted += sp_inserted
            total_confirmed += sp_confirmed
            if sp_inserted > 0:
                round_detail.append(f'{species}: +{sp_inserted}(✓{sp_confirmed})')
            logging.info(f'{species} done: +{sp_inserted} confirmed={sp_confirmed}')
            time.sleep(SLEEP_SPECIES)

        # 輪次結束推 Telegram
        total_rows  = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
        confirmed_r = conn.execute('SELECT COUNT(*) FROM market_kpi WHERE confirmed=1').fetchone()[0]
        pending     = conn.execute('SELECT COUNT(*) FROM market_kpi WHERE confirmed=0').fetchone()[0]
        detail_str  = '\n'.join(round_detail) if round_detail else '本輪無新增'

        tg(f'📊 <b>Round {round_num} 完成</b>\n'
           f'已運行 {elapsed:.1f}h\n'
           f'本輪: +{round_inserted} 筆 (✓{round_confirmed} verified)\n'
           f'{detail_str}\n'
           f'DB: {total_rows} 筆 | ✅{confirmed_r} / ⏳{pending}')

        logging.info(f'Round {round_num} done. DB={total_rows} +{round_inserted} confirmed={round_confirmed}')
        logging.info(f'Sleeping {SLEEP_ROUND}s...')
        time.sleep(SLEEP_ROUND)

    elapsed = (time.time() - start_time) / 3600
    total_rows = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
    conn.close()
    tg(f'🏁 <b>v4 完成</b>\n'
       f'{elapsed:.1f}h | {round_num} 輪\n'
       f'新增: {total_inserted} | Verified: {total_confirmed}\n'
       f'DB: {total_rows} 筆')
    logging.info('DONE')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info('Interrupted.')
        tg('⚠️ v4 手動中止')
    except Exception as e:
        logging.error(f'Fatal: {e}')
        tg(f'❌ <b>v4 崩潰</b>\n{e}')
