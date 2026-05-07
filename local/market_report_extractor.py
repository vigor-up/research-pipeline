# -*- coding: utf-8 -*-
"""
market_report_extractor.py
智慧抓取市場報告 → 自動提取關鍵指標 → 寫入DB
用法：
  python market_report_extractor.py --url <URL>
  python market_report_extractor.py --text <貼上文字>
  python market_report_extractor.py --image <圖片路徑>  (OCR)
Telegram 指令：
  /report <URL或貼文>
"""

import sqlite3, uuid, json, argparse, requests, logging, sys
from datetime import datetime
from pathlib import Path

DB_PATH        = r'D:\LLM\knowledge\market\market_data.db'
QWEN_URL       = 'http://localhost:1234/v1/chat/completions'
QWEN_MODEL     = 'qwen3.6-35b'
TELEGRAM_TOKEN = '8703702788:AAFKEiGmLYTAuFVG9GX-gRtVTUUyi-f_5mM'
TELEGRAM_CHAT  = 897274134
FIRECRAWL_API_KEY = 'fc-f1b23a25854a4c96aa56acb89c65e930'
MCP_URL        = 'http://localhost:8765/call'
RAGFLOW_API_KEY = 'ragflow-fcCq8K0sVcefhVHboEmBOOzt5S2cQ7jCcHT5cCwhWRM'
RAGFLOW_BASE_URL = 'http://localhost'
RAGFLOW_DATASET_ID = '5a68aa6e49ba11f190c657ee8852d812'

RAGFLOW_API_KEY = 'ragflow-fcCq8K0sVcefhVHboEmBOOzt5S2cQ7jCcHT5cCwhWRM'
RAGFLOW_BASE_URL = 'http://localhost'
RAGFLOW_DATASET_ID = '5a68aa6e49ba11f190c657ee8852d812'


logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s')

# ── Qwen 提取 Prompt ────────────────────────────────────
EXTRACT_PROMPT = """你是中國畜牧市場數據分析師。
從以下市場報告文字中提取所有可量化的關鍵指標。

輸出純JSON，格式如下：
{{
  "report_date": "YYYY-MM-DD或null",
  "report_title": "報告標題",
  "species": "整篇報告主要物種（finisher_pig/layer_chicken/beef_cattle/meat_sheep/broiler/duck/dairy_cow等）",
  "prices": [
    {{
      "item": "品項名稱",
      "species": "該價格對應物種（finisher_pig/beef_cattle/meat_sheep/broiler/layer_chicken/duck/dairy_cow/shrimp/nursery_pig）",
      "value": 數字,
      "unit": "元/斤|元/kg|元/噸|元/頭",
      "region": "地區或CN_all",
      "price_type": "live|carcass|egg|feed|piglet|slaughter"
    }}
  ],
  "market_indicators": [
    {{
      "metric": "指標名稱",
      "species": "對應物種（同上列表）",
      "value": 數字或null,
      "unit": "單位",
      "trend": "up|down|stable|null",
      "description": "簡述（30字內）"
    }}
  ],
  "roi_insights": [
    "對ROI銷售有用的市場洞察（每條50字內）"
  ],
  "summary": "100字內市場摘要"
}}

重要規則：
1. 每筆price和indicator必須有正確species，不得用報告主物種覆蓋其他物種
2. 豬肉/白條豬=finisher_pig，仔豬=nursery_pig，雞蛋=layer_chicken，毛雞=broiler
3. 只提取文中明確出現的數字，不推測
4. 如果某欄位無法確定，填null

文字：
{text}"""

def qwen_extract(text):
    prompt = EXTRACT_PROMPT.format(text=text[:4000])
    try:
        resp = requests.post(QWEN_URL, json={
            'model': QWEN_MODEL,
            'messages': [{'role':'user','content':prompt}],
            'temperature': 0.1, 'max_tokens': 2000}, timeout=120)
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            s = content.find('{'); e = content.rfind('}')+1
            if s >= 0 and e > s:
                return json.loads(content[s:e])
    except Exception as ex:
        logging.error(f'Qwen extract: {ex}')
    return None

def scrape_url(url):
    """透過 MCP Server 抓取"""
    try:
        resp = requests.post(MCP_URL, json={
            'tool': 'scrape_url',
            'params': {'url': url, 'mode': 'auto',
                       'extract_type': 'text', 'max_tokens': 4000}
        }, timeout=60)
        if resp.status_code == 200:
            r = resp.json()
            return r.get('content', '')
    except Exception:
        pass
    # fallback requests
    try:
        r = requests.get(url, timeout=15,
            headers={'User-Agent':'Mozilla/5.0'})
        return r.text[:5000]
    except Exception as e:
        logging.error(f'Scrape failed: {e}')
    # Firecrawl fallback (JS dynamic pages)
    try:
        fc_resp = requests.post(
            'https://api.firecrawl.dev/v0/scrape',
            headers={'Authorization': f'Bearer {FIRECRAWL_API_KEY}'},
            json={'url': url, 'pageOptions': {'onlyMainContent': True}},
            timeout=30)
        if fc_resp.ok:
            data = fc_resp.json()
            content = data.get('data', {}).get('content', '')
            if content:
                logging.info(f'[Firecrawl] OK: {url}')
                return content[:8000]
    except Exception as e:
        logging.warning(f'[Firecrawl] Failed: {e}')
    return ''

def write_to_db(conn, extracted, source_url, source_title):
    cur = conn.cursor()
    n = 0
    NOW  = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    date = extracted.get('report_date', '')
    year = int(date[:4]) if date and len(date) >= 4 else 2026
    species_main = extracted.get('species', 'unknown')

    # 寫入價格數據
    for p in extracted.get('prices', []):
        val  = p.get('value')
        if not val: continue
        unit = p.get('unit','')
        # 換算為 CNY/kg
        if '斤' in unit:
            val_kg = round(float(val)*2, 2)
            unit_std = 'CNY/kg'
        elif '噸' in unit:
            val_kg = round(float(val)/1000, 2)
            unit_std = 'CNY/kg'
        else:
            val_kg = float(val)
            unit_std = unit

        region   = p.get('region','CN_all')
        ptype    = p.get('price_type','spot')
        safe_item = p.get('item','').replace(' ','_')[:20]
        species_price = p.get('species', species_main)
        kpi_id   = f"spot_price_{species_price}_{ptype}_{safe_item}_{region.lower()}"

        if not cur.execute(
            "SELECT id FROM market_kpi WHERE kpi_id=? AND year=?",
            (kpi_id, year)).fetchone():
            cur.execute("""INSERT INTO market_kpi
                (id,region,country,species,production_stage,kpi_id,
                 value,unit,year,credibility,source_type,
                 source_url,source_title,raw_text,language,confirmed,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                str(uuid.uuid4()), region, 'CN',
                species_price, 'market_price', kpi_id,
                val_kg, unit_std, year, 4, 'industry_media',
                source_url, source_title,
                f"{p.get('item')} {val}{unit} → {val_kg}CNY/kg",
                'zh-CN', 1, NOW))
            n += 1

    # 寫入市場指標
    for m in extracted.get('market_indicators', []):
        val = m.get('value')
        metric = m.get('metric','').replace(' ','_')[:30]
        species_ind = m.get('species', species_main)
        kpi_id = f"market_indicator_{species_ind}_{metric}_{year}"
        if val is not None and not cur.execute(
            "SELECT id FROM market_kpi WHERE kpi_id=?", (kpi_id,)).fetchone():
            cur.execute("""INSERT INTO market_kpi
                (id,region,country,species,production_stage,kpi_id,
                 value,unit,year,credibility,source_type,
                 source_url,source_title,raw_text,language,confirmed,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                str(uuid.uuid4()), 'CN_all', 'CN',
                species_ind, 'market_indicator', kpi_id,
                float(val), m.get('unit',''), year,
                3, 'industry_media',
                source_url, source_title,
                f"{m.get('metric')} {val} {m.get('unit','')} trend={m.get('trend','')} | {m.get('description','')}",
                'zh-CN', 0, NOW))
            n += 1

    # 寫入市場背景摘要
    summary = extracted.get('summary','')
    insights = '\n'.join(extracted.get('roi_insights',[]))
    if summary:
        comp_id = f"market_report_{species_main}_{date or year}"
        if not cur.execute(
            "SELECT id FROM competitor_market WHERE competitor_id=?",
            (comp_id,)).fetchone():
            cur.execute("""INSERT INTO competitor_market
                (id,competitor_id,competitor_name,region,market_claim,
                 claim_metric,species,source_url,source_type,
                 credibility,year,raw_text,confirmed,collected_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                str(uuid.uuid4()), comp_id,
                extracted.get('report_title', source_title),
                'CN_all',
                f"{summary}\n\nROI洞察：\n{insights}",
                'market_background', species_main,
                source_url, 'industry_media',
                4, year,
                f"AUTO_EXTRACTED | {extracted.get('report_title','')}",
                1, NOW))
            n += 1

    conn.commit()
    return n


def upload_to_ragflow(text, doc_name):
    import tempfile, os, requests, logging
    headers = {'Authorization': f'Bearer {RAGFLOW_API_KEY}'}
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    tmp.write(text); tmp.close()
    try:
        with open(tmp.name, 'rb') as f:
            resp = requests.post(
                f'{RAGFLOW_BASE_URL}/api/v1/datasets/{RAGFLOW_DATASET_ID}/documents',
                headers=headers,
                files={'file': (doc_name, f, 'text/plain')}
            )
        if resp.status_code == 200 and resp.json().get('code') == 0:
            doc_id = resp.json()['data'][0]['id']
            requests.post(
                f'{RAGFLOW_BASE_URL}/api/v1/datasets/{RAGFLOW_DATASET_ID}/chunks',
                headers=headers,
                json={'document_ids': [doc_id]}
            )
            logging.info(f'[RAGFlow] 上傳成功: {doc_name}')
            return True
    except Exception as e:
        logging.error(f'[RAGFlow] 上傳失敗: {e}')
    finally:
        os.unlink(tmp.name)
    return False


def upload_to_ragflow(text, doc_name):
    import tempfile, os
    headers = {'Authorization': f'Bearer {RAGFLOW_API_KEY}'}
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    tmp.write(text); tmp.close()
    try:
        with open(tmp.name, 'rb') as f:
            resp = requests.post(
                f'{RAGFLOW_BASE_URL}/api/v1/datasets/{RAGFLOW_DATASET_ID}/documents',
                headers=headers,
                files={'file': (doc_name, f, 'text/plain')}
            )
        if resp.status_code == 200 and resp.json().get('code') == 0:
            doc_id = resp.json()['data'][0]['id']
            requests.post(
                f'{RAGFLOW_BASE_URL}/api/v1/datasets/{RAGFLOW_DATASET_ID}/chunks',
                headers=headers,
                json={'document_ids': [doc_id]}
            )
            logging.info(f'[RAGFlow] 上傳成功: {doc_name}')
            return True
    except Exception as e:
        logging.error(f'[RAGFlow] 上傳失敗: {e}')
    finally:
        os.unlink(tmp.name)
    return False

def tg(msg):
    try:
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id':TELEGRAM_CHAT,'text':msg,'parse_mode':'HTML'},
            timeout=10)
    except Exception:
        pass

def process_report(text, source_url='', source_title=''):
    logging.info(f'Extracting from {len(text)} chars...')
    extracted = qwen_extract(text)
    if not extracted:
        return 0, '提取失敗'

    conn = sqlite3.connect(DB_PATH)
    n = write_to_db(conn, extracted, source_url, source_title)
    total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
    conn.close()

    summary = extracted.get('summary','無摘要')
    prices_count = len(extracted.get('prices',[]))
    indicators_count = len(extracted.get('market_indicators',[]))

    report = (
        f'📰 <b>市場報告提取完成</b>\n'
        f'標題: {extracted.get("report_title","未知")}\n'
        f'日期: {extracted.get("report_date","未知")}\n'
        f'物種: {extracted.get("species","未知")}\n\n'
        f'提取: 價格{prices_count}筆 + 指標{indicators_count}筆\n'
        f'寫入DB: {n}筆新增\n'
        f'DB總計: {total}筆\n\n'
        f'📋 摘要:\n{summary}\n\n'
        f'💡 ROI洞察:\n' +
        '\n'.join(f'• {i}' for i in extracted.get('roi_insights',[])[:3])
    )
    doc_name = f"market_{extracted.get('report_date','unknown')}_{extracted.get('species','unknown')}.txt"
    upload_to_ragflow(text, doc_name)
    doc_name = f"market_{extracted.get('report_date','unknown')}_{extracted.get('species','unknown')}.txt"
    upload_to_ragflow(text, doc_name)
    return n, report

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url',   help='報告URL')
    parser.add_argument('--text',  help='直接貼入文字')
    parser.add_argument('--title', default='', help='報告標題')
    parser.add_argument('--telegram', action='store_true')
    args = parser.parse_args()

    if args.url:
        logging.info(f'Scraping {args.url}...')
        text = scrape_url(args.url)
        if not text:
            print('抓取失敗')
            sys.exit(1)
        title = args.title or args.url
        url   = args.url
    elif args.text:
        text  = args.text
        title = args.title or '手動輸入'
        url   = ''
    else:
        # 互動模式：從stdin讀取
        print('請貼入報告文字（輸入完後按 Ctrl+Z 或 Ctrl+D）：')
        text  = sys.stdin.read()
        title = args.title or '手動輸入'
        url   = ''

    n, report = process_report(text, url, title)
    print(report)

    if args.telegram:
        tg(report)
