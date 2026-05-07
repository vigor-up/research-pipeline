# -*- coding: utf-8 -*-
"""
auto_collect_v3.py
智慧追蹤版：Qwen3.6分析DB缺口 → 動態生成查詢 → Scrapling全文 → 抽取 → DB
Telegram：只在輪次結束/錯誤/完成推送
"""

import sqlite3, uuid, json, time, logging, requests, hashlib
from datetime import datetime
from pathlib import Path
from scrapling import Fetcher

DB_PATH        = r'D:\LLM\knowledge\market\market_data.db'
LOG_PATH       = r'D:\LLM\workflows\research-pipeline-v2\logs\auto_collect_v3.log'
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

# 所有目標物種
ALL_SPECIES = [
    ('dairy_goat',       'CN_all',   ['FCR','ADG','milk_yield','mortality']),
    ('channel_catfish',  'CN_all',   ['FCR','ADG','survival','mortality']),
    ('largemouth_catfish','CN_all',  ['FCR','ADG','survival']),
    ('dairy_cow',        'CN_all',   ['milk_yield','FCR','mortality','mastitis_loss']),
    ('layer_chicken',    'CN_all',   ['FCR','egg_rate','mortality','AI_loss']),
    ('broiler',          'CN_all',   ['FCR','ADG','mortality','disease_loss']),
    ('shrimp',           'CN_south', ['FCR','survival','mortality','EMS_loss']),
    ('beef_cattle',      'CN_north', ['FCR','ADG','mortality']),
    ('beef_cattle',      'CN_south', ['FCR','ADG','mortality']),
    ('finisher_pig',     'CN_north', ['FCR','ADG','mortality']),
    ('meat_sheep',       'CN_north', ['FCR','ADG','mortality']),
    ('tilapia',          'CN_south', ['FCR','ADG','survival','strep_loss']),
    ('grouper',          'CN_south', ['FCR','ADG','survival','vibrio_loss']),
    ('largemouth_bass',  'CN_south', ['FCR','ADG','survival']),
]

# ── 缺口分析 Prompt ────────────────────────────────────
GAP_PROMPT = """你是動物營養市場研究員。
以下是資料庫現有數據摘要：
{db_summary}

請為以下物種生成 3-4 條最有可能找到具體數字的英文/中文搜索查詢：
物種：{species}（{region}）
缺少的KPI：{missing_kpis}

要求：
1. 查詢要具體，包含物種名稱、KPI指標、地區、年份
2. 英文和中文各2條
3. 優先針對「缺少的KPI」
4. 輸出純JSON數組：["查詢1","查詢2","查詢3","查詢4"]
不要任何說明。"""

# ── KPI 抽取 Prompt ────────────────────────────────────
EXTRACT_PROMPT = """從以下文字抽取{species}的生產KPI數據。
只抽取文中明確出現的數字，不推測不編造。
輸出純JSON數組：
[{{"kpi":"fcr|adg|mortality|milk_yield|egg_rate|survival|litter_size|slaughter_wt|other","value_min":數字或null,"value_mid":數字,"value_max":數字或null,"unit":"單位","condition":"條件","metric_type":"baseline或disease_penalty","year":年份或null,"confidence":"high或medium或low"}}]
無數字回覆: []
文字：
{text}"""

# ── 初始化 ─────────────────────────────────────────────
def setup_logging():
    Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.FileHandler(LOG_PATH, encoding='utf-8'), logging.StreamHandler()])

def load_tavily_key():
    global TAVILY_KEY
    for enc in ('utf-8-sig','utf-8','cp950'):
        try:
            with open(r'D:\LLM\API key.txt', encoding=enc) as f:
                for line in f:
                    if 'TAVILY' in line.upper():
                        TAVILY_KEY = line.split('=')[-1].strip().strip('"').strip("'")
                        logging.info(f'Tavily key ({enc}): {TAVILY_KEY[:8]}...')
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

# ── DB 缺口分析 ─────────────────────────────────────────
def get_db_summary(conn, species, region, target_kpis):
    """回傳該物種已有/缺少的KPI"""
    rows = conn.execute(
        "SELECT kpi_id, value, confirmed FROM market_kpi WHERE species=? AND region=?",
        (species, region)
    ).fetchall()
    have = {r[0].split('_')[0] for r in rows if r[1] is not None}
    missing = [k for k in target_kpis if k.lower() not in have]
    return {
        'have': list(have),
        'missing': missing,
        'total': len(rows)
    }

# ── Qwen: 動態生成查詢 ─────────────────────────────────
def qwen_gen_queries(species, region, missing_kpis, db_summary):
    if not missing_kpis:
        # 沒缺口，用預設查詢補充確認
        return [
            f'{species.replace("_"," ")} FCR ADG mortality China {region} 2023 2024',
            f'{species.replace("_"," ")} production performance benchmark China 2023',
        ]
    prompt = GAP_PROMPT.format(
        db_summary=json.dumps(db_summary, ensure_ascii=False),
        species=species, region=region,
        missing_kpis=', '.join(missing_kpis)
    )
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(QWEN_URL, json={
                'model': QWEN_MODEL,
                'messages': [{'role':'user','content':prompt}],
                'temperature': 0.3, 'max_tokens': 400}, timeout=60)
            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message']['content']
                s = content.find('['); e = content.rfind(']')+1
                if s >= 0 and e > s:
                    queries = json.loads(content[s:e])
                    logging.info(f'Qwen queries for {species}: {queries}')
                    return queries[:4]
        except Exception as ex:
            logging.warning(f'Qwen gen attempt {attempt+1}: {ex}')
        time.sleep(RETRY_DELAY)
    # fallback
    return [f'{species.replace("_"," ")} {" ".join(missing_kpis[:2])} China 2023']

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
SKIP_DOMAINS = ['researchgate.net','jstor.org','sci-hub','paywall']

def scrape_url(url):
    if any(d in url for d in SKIP_DOMAINS):
        return ''
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
    except Exception as e:
        logging.debug(f'Scrape fail {url[:50]}: {e}')
        return ''

# ── Qwen: 抽取 KPI ────────────────────────────────────
def qwen_extract(text, species):
    if not text or len(text) < 100:
        return []
    prompt = EXTRACT_PROMPT.format(species=species, text=text[:3000])
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(QWEN_URL, json={
                'model': QWEN_MODEL,
                'messages': [{'role':'user','content':prompt}],
                'temperature': 0.1, 'max_tokens': 1000}, timeout=90)
            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message']['content']
                s = content.find('['); e = content.rfind(']')+1
                if s >= 0 and e > s:
                    return json.loads(content[s:e])
                return []
        except Exception as ex:
            logging.warning(f'Qwen extract attempt {attempt+1}: {ex}')
        time.sleep(RETRY_DELAY)
    return []

# ── 寫入 DB ────────────────────────────────────────────
def write_to_db(conn, species, region, kpis, url, title):
    inserted = 0
    for kpi in kpis:
        if kpi.get('confidence') == 'low': continue
        vmid = kpi.get('value_mid')
        if vmid is None: continue
        metric = kpi.get('kpi', 'unknown')
        year   = kpi.get('year') or 2023
        kpi_id = f"{metric}_{species}_{region.lower()}"
        if conn.execute(
            "SELECT id FROM market_kpi WHERE kpi_id=? AND region=? AND year=?",
            (kpi_id, region, year)).fetchone():
            continue
        conn.execute("""INSERT INTO market_kpi
            (id,region,country,species,production_stage,kpi_id,value,value_min,value_max,
             unit,year,credibility,source_type,source_url,source_title,raw_text,language,confirmed,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            str(uuid.uuid4()), region,
            'CN' if region.startswith('CN') else 'GLOBAL',
            species, kpi.get('condition',''), kpi_id,
            vmid, kpi.get('value_min'), kpi.get('value_max'),
            kpi.get('unit',''), year, 3, 'academic_background',
            url, title, f"auto_v3|{kpi.get('condition','')}",
            'zh-CN', 0, datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')))
        inserted += 1
    if inserted > 0:
        conn.commit()
    return inserted

# ── 主循環 ─────────────────────────────────────────────
def main():
    setup_logging()
    logging.info('='*60)
    logging.info('auto_collect_v3 START (智慧追蹤版)')
    if not load_tavily_key():
        tg('❌ Tavily key 讀取失敗')
        return

    conn = sqlite3.connect(DB_PATH)
    visited_urls = set()  # 已抓過的URL跳過
    total_inserted = 0
    start_time = time.time()
    round_num = 0

    tg(f'🧠 <b>auto_collect_v3 智慧追蹤啟動</b>\n'
       f'物種: {len(ALL_SPECIES)} 個\n'
       f'預計運行 {MAX_HOURS}h\n'
       f'每輪結束才推送，安心睡覺 😴')

    while True:
        elapsed = (time.time() - start_time) / 3600
        if elapsed > MAX_HOURS:
            break

        round_num += 1
        logging.info(f'=== Round {round_num} | {elapsed:.1f}h | total: {total_inserted} ===')

        round_inserted = 0
        round_detail = []

        for species, region, target_kpis in ALL_SPECIES:
            # ① 缺口分析
            summary = get_db_summary(conn, species, region, target_kpis)
            missing = summary['missing']
            logging.info(f'{species}/{region}: have={summary["have"]}, missing={missing}')

            # 如果全部有了，跳過
            if not missing and summary['total'] >= len(target_kpis):
                logging.info(f'  → {species} 已足夠，跳過')
                continue

            # ② Qwen 動態生成查詢
            queries = qwen_gen_queries(species, region, missing, summary)
            sp_inserted = 0

            for query in queries:
                results = tavily_search(query)
                time.sleep(SLEEP_QUERY)

                for r in results:
                    url   = r.get('url', '')
                    title = r.get('title', '')

                    # 跳過已訪問
                    url_hash = hashlib.md5(url.encode()).hexdigest()
                    if url_hash in visited_urls:
                        continue
                    visited_urls.add(url_hash)

                    # ③ 全文抓取
                    raw = r.get('raw_content', '') or ''
                    if len(raw) < 300:
                        raw = scrape_url(url)

                    # ④ Qwen 抽取
                    kpis = qwen_extract(raw, species)
                    if kpis:
                        n = write_to_db(conn, species, region, kpis, url, title)
                        sp_inserted += n
                        total_inserted += n
                        round_inserted += n
                        if n > 0:
                            logging.info(f'  ✅ {species} +{n} | {url[:60]}')

            if sp_inserted > 0:
                round_detail.append(f'{species}: +{sp_inserted}')
            logging.info(f'{species} done: +{sp_inserted}')
            time.sleep(SLEEP_SPECIES)

        # 每輪結束推一次 Telegram
        total_rows = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
        confirmed  = conn.execute('SELECT COUNT(*) FROM market_kpi WHERE confirmed=1').fetchone()[0]
        pending    = conn.execute('SELECT COUNT(*) FROM market_kpi WHERE confirmed=0').fetchone()[0]
        detail_str = '\n'.join(round_detail) if round_detail else '本輪無新增'

        tg(f'📊 <b>Round {round_num} 完成</b>\n'
           f'已運行 {elapsed:.1f}h\n'
           f'本輪新增: {round_inserted} 筆\n'
           f'{detail_str}\n'
           f'DB: {total_rows} 筆（✅{confirmed} / ⏳{pending}）')

        logging.info(f'Round {round_num} done. DB={total_rows} +{round_inserted}')
        logging.info(f'Sleeping {SLEEP_ROUND}s...')
        time.sleep(SLEEP_ROUND)

    elapsed = (time.time() - start_time) / 3600
    total_rows = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
    conn.close()
    tg(f'🏁 <b>auto_collect_v3 完成</b>\n'
       f'運行 {elapsed:.1f}h | {round_num} 輪\n'
       f'累計新增: {total_inserted} 筆\n'
       f'DB總計: {total_rows} 筆')
    logging.info('DONE')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info('Interrupted.')
        tg('⚠️ auto_collect_v3 手動中止')
    except Exception as e:
        logging.error(f'Fatal: {e}')
        tg(f'❌ <b>v3 崩潰</b>\n{e}')
