# -*- coding: utf-8 -*-
"""
auto_collect_v2.py
架構：Tavily → Scrapling全文 → Qwen3.6抽取 → DB
Telegram：只在輪次結束/錯誤/完成推送，不打擾睡眠
"""

import sqlite3, uuid, json, time, logging, requests
from datetime import datetime
from pathlib import Path
from scrapling import Fetcher

DB_PATH        = r'D:\LLM\knowledge\market\market_data.db'
LOG_PATH       = r'D:\LLM\workflows\research-pipeline-v2\logs\auto_collect_v2.log'
QWEN_URL       = 'http://localhost:1234/v1/chat/completions'
QWEN_MODEL     = 'qwen3.6-35b'
TELEGRAM_TOKEN = '8703702788:AAFKEiGmLYTAuFVG9GX-gRtVTUUyi-f_5mM'
TELEGRAM_CHAT  = 897274134
TAVILY_KEY     = None
SLEEP_QUERY    = 8
SLEEP_SPECIES  = 20
SLEEP_ROUND    = 1800
MAX_HOURS      = 14.5
MAX_RETRIES    = 3
RETRY_DELAY    = 15

SPECIES_QUERIES = [
    {'species':'dairy_goat','region':'CN_all','queries':[
        'dairy goat FCR feed conversion ratio ADG daily weight gain China farm benchmark 2022 2023',
        'dairy goat milk yield lactation performance Guanzhong Saanen China 2023 kg per day',
        'dairy goat mortality disease loss China commercial farm statistics 2023',
        '奶山羊 饲料转化率 日增重 产奶量 规模化 基准值 2023',
    ]},
    {'species':'channel_catfish','region':'CN_all','queries':[
        'channel catfish Ictalurus punctatus FCR ADG survival rate China pond 2022 2023',
        'channel catfish production performance benchmark China aquaculture 2022 2023',
        '斑点叉尾鮰 饲料系数 日增重 成活率 中国 池塘 2022 2023',
    ]},
    {'species':'dairy_cow','region':'CN_all','queries':[
        'Holstein dairy cow milk yield per day FCR China commercial farm 2023',
        'dairy cow mastitis lameness mortality China farm disease loss 2023',
        '奶牛 产奶量 饲料转化效率 死亡率 中国规模化牧场 2023',
    ]},
    {'species':'layer_chicken','region':'CN_all','queries':[
        'layer chicken feed conversion ratio egg production rate mortality China 2023',
        'layer hen Newcastle disease avian influenza mortality China 2023',
        '蛋鸡 料蛋比 产蛋率 死亡率 中国商业化 2023',
    ]},
    {'species':'broiler','region':'CN_all','queries':[
        'broiler FCR ADG mortality China commercial farm 2023 benchmark',
        'broiler necrotic enteritis coccidiosis performance loss China 2023',
        '肉鸡 料肉比 日增重 死亡率 中国规模化 2023',
    ]},
    {'species':'shrimp','region':'CN_south','queries':[
        'whiteleg shrimp Litopenaeus vannamei FCR survival rate China pond 2022 2023',
        'shrimp EMS AHPND mortality production loss China Guangdong 2023',
        '对虾 饲料系数 成活率 中国南方 2022 2023',
    ]},
    {'species':'largemouth_catfish','region':'CN_all','queries':[
        'largemouth catfish Silurus meridionalis FCR ADG China pond benchmark',
        '大口鲶 饲料系数 日增重 养殖性能 中国 2022 2023',
    ]},
    {'species':'beef_cattle','region':'CN_north','queries':[
        'beef cattle FCR ADG feedlot China northern region benchmark 2023',
        '肉牛 料肉比 日增重 中国北方 育肥 2023 基准值',
    ]},
    {'species':'finisher_pig','region':'CN_north','queries':[
        'finisher pig FCR ADG China northern farm benchmark 2023 regional',
        '育肥猪 料肉比 日增重 中国北方 2023 区域数据',
    ]},
]

EXTRACT_PROMPT = """你是動物生產性能數據抽取專家。從以下文字抽取{species}的KPI數據。
只抽取文中明確出現的數字，不要推測或編造。
輸出純JSON數組（不加任何說明文字）：
[{{"kpi":"fcr|adg|mortality|milk_yield|egg_rate|survival|litter_size|slaughter_wt|other","value_min":數字或null,"value_mid":數字,"value_max":數字或null,"unit":"單位","condition":"條件","metric_type":"baseline或disease_penalty","year":年份或null,"confidence":"high或medium或low"}}]
如無具體數字回覆: []
文字：
{text}"""

def setup_logging():
    Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.FileHandler(LOG_PATH,encoding='utf-8'), logging.StreamHandler()])

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
        logging.warning(f'TG error: {e}')

def tavily_search(query, max_results=5):
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post('https://api.tavily.com/search', json={
                'api_key':TAVILY_KEY,'query':query,'max_results':max_results,
                'search_depth':'advanced','include_raw_content':True}, timeout=30)
            if resp.status_code == 200:
                results = resp.json().get('results',[])
                logging.info(f'Tavily [{len(results)}] "{query[:50]}"')
                return results
        except Exception as e:
            logging.warning(f'Tavily error: {e}')
        time.sleep(RETRY_DELAY)
    return []

SKIP_DOMAINS = ['researchgate.net','jstor.org','sci-hub']

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

def qwen_extract(text, species):
    if not text or len(text) < 100:
        return []
    prompt = EXTRACT_PROMPT.format(species=species, text=text[:3000])
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(QWEN_URL, json={
                'model':QWEN_MODEL,
                'messages':[{'role':'user','content':prompt}],
                'temperature':0.1,'max_tokens':1000}, timeout=90)
            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message']['content']
                s = content.find('['); e = content.rfind(']')+1
                if s >= 0 and e > s:
                    return json.loads(content[s:e])
                return []
        except Exception as ex:
            logging.warning(f'Qwen attempt {attempt+1}: {ex}')
        time.sleep(RETRY_DELAY)
    return []

def write_to_db(conn, species, region, kpis, url, title):
    inserted = 0
    for kpi in kpis:
        if kpi.get('confidence') == 'low': continue
        vmid = kpi.get('value_mid')
        if vmid is None: continue
        metric = kpi.get('kpi','unknown')
        year   = kpi.get('year') or 2023
        kpi_id = f"{metric}_{species}_{region.lower()}"
        if conn.execute("SELECT id FROM market_kpi WHERE kpi_id=? AND region=? AND year=?",
                        (kpi_id,region,year)).fetchone():
            continue
        conn.execute("""INSERT INTO market_kpi
            (id,region,country,species,production_stage,kpi_id,value,value_min,value_max,
             unit,year,credibility,source_type,source_url,source_title,raw_text,language,confirmed,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            str(uuid.uuid4()), region,
            'CN' if region.startswith('CN') else 'GLOBAL',
            species, kpi.get('condition',''), kpi_id,
            vmid, kpi.get('value_min'), kpi.get('value_max'),
            kpi.get('unit',''), year, 3, 'academic_background',
            url, title, f"auto_v2|{kpi.get('condition','')}",
            'zh-CN', 0, datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')))
        inserted += 1
    if inserted > 0:
        conn.commit()
    return inserted

def main():
    setup_logging()
    logging.info('='*60)
    logging.info('auto_collect_v2 START')
    if not load_tavily_key():
        tg('❌ Tavily key 讀取失敗，中止')
        return

    conn = sqlite3.connect(DB_PATH)
    total_inserted = 0
    start_time = time.time()
    round_num = 0

    tg(f'🚀 <b>auto_collect_v2 啟動</b>\n物種: {len(SPECIES_QUERIES)} 個\n'
       f'預計運行 {MAX_HOURS}h\n每輪結束才推送，不打擾睡眠')

    while True:
        elapsed = (time.time() - start_time) / 3600
        if elapsed > MAX_HOURS:
            break

        round_num += 1
        logging.info(f'=== Round {round_num} | {elapsed:.1f}h | total: {total_inserted} ===')

        round_inserted = 0
        round_detail = []

        for sp in SPECIES_QUERIES:
            species = sp['species']
            region  = sp['region']
            sp_inserted = 0

            for query in sp['queries']:
                results = tavily_search(query)
                time.sleep(SLEEP_QUERY)
                for r in results:
                    url   = r.get('url','')
                    title = r.get('title','')
                    raw   = r.get('raw_content','') or ''
                    if len(raw) < 300:
                        raw = scrape_url(url)
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

        total_rows = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
        detail_str = '\n'.join(round_detail) if round_detail else '本輪無新增'
        tg(f'📊 <b>Round {round_num} 完成</b>\n'
           f'已運行 {elapsed:.1f}h\n'
           f'本輪新增: {round_inserted} 筆\n'
           f'{detail_str}\n'
           f'DB總計: {total_rows} 筆')
        logging.info(f'Round {round_num} done. DB={total_rows} +{round_inserted}')
        logging.info(f'Sleeping {SLEEP_ROUND}s...')
        time.sleep(SLEEP_ROUND)

    elapsed = (time.time() - start_time) / 3600
    total_rows = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
    conn.close()
    tg(f'🏁 <b>完成</b>\n運行 {elapsed:.1f}h | {round_num} 輪\n'
       f'累計新增: {total_inserted} 筆\nDB總計: {total_rows} 筆')
    logging.info('DONE')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info('Interrupted.')
        tg('⚠️ auto_collect_v2 手動中止')
    except Exception as e:
        logging.error(f'Fatal: {e}')
        tg(f'❌ <b>崩潰</b>\n{e}')
