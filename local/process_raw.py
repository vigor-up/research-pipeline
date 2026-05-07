# -*- coding: utf-8 -*-
"""
process_raw.py
從 R2 拉 GitHub Actions 收集的原始資料
→ Qwen3.6 抽取 KPI + 驗證 → market_data.db
EVO-X2 本地執行，依賴 Qwen3.6 port 1234
"""
import sqlite3, uuid, json, time, logging, requests, hashlib, re, math, os, boto3
from datetime import datetime
from pathlib import Path

DB_PATH        = r'D:\LLM\knowledge\market\market_data.db'
LOG_PATH       = r'D:\LLM\workflows\research-pipeline-v2\logs\process_raw.log'
QWEN_URL       = 'http://localhost:1234/v1/chat/completions'
QWEN_MODEL     = 'qwen3.6-35b'
TELEGRAM_TOKEN = '8703702788:AAFKEiGmLYTAuFVG9GX-gRtVTUUyi-f_5mM'
TELEGRAM_CHAT  = 897274134
R2_ENDPOINT    = 'https://adb1040c847f4ae4a7d6bfedcccd7b77.r2.cloudflarestorage.com'
R2_ACCESS_KEY  = 'f443b2e5acc77dd1af6a83a5d548b35b'
R2_SECRET_KEY  = 'da1c377ffbc03b865504e292480e0e2806ddb84a61bf87b7e6a2066632a4a357'
R2_BUCKET      = 'richtrong-collect'

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ])

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

INGREDIENT_EXTRACT_PROMPT = """從以下文字抽取原料在動物上的試驗效果數據。
只抽取文中明確出現的數字，不推測。
輸出純JSON數組：
[{{"kpi":"fcr|adg|mortality|egg_rate|survival|milk_yield|other",
  "control_value":對照組數字或null,"treatment_value":試驗組數字,
  "unit":"單位","improvement_pct":改善百分比或null,
  "year":年份或null,"study_type":"field_trial|lab|meta_analysis|review",
  "confidence":"high|medium|low","raw_text":"原文關鍵句子（30字內）"}}]
無數字回覆: []
文字：{text}"""

REGION_NORMALIZE = {
    'CN_northeast': 'CN_northeast', 'CN_north': 'CN_north',
    'CN_east': 'CN_east',           'CN_south': 'CN_south',
    'CN_central': 'CN_central',     'CN_southwest': 'CN_southwest',
    'SEA_malaysia': 'SEA_malaysia',  'SEA_thailand': 'SEA_thailand',
    'SEA_vietnam': 'SEA_vietnam',    'TW_all': 'TW_all',
    'GLOBAL': 'GLOBAL',             'CN_all': 'CN_all',
}

def tg(msg):
    try:
        requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id': TELEGRAM_CHAT, 'text': msg, 'parse_mode': 'HTML'}, timeout=10)
    except Exception as e:
        logging.warning(f'TG: {e}')

def qwen_call(prompt, max_tokens=1200):
    for attempt in range(3):
        try:
            resp = requests.post(QWEN_URL, json={
                'model': QWEN_MODEL,
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.1, 'max_tokens': max_tokens, 'stream': False},
                timeout=90)
            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message']['content']
                return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        except Exception as e:
            logging.warning(f'Qwen attempt {attempt+1}: {e}')
        time.sleep(10)
    return ''

def fetch_from_r2(date_str=None):
    s3 = boto3.client('s3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        region_name='auto')
    if not date_str:
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
    key = f'raw/{date_str}/collected.json'
    try:
        obj = s3.get_object(Bucket=R2_BUCKET, Key=key)
        records = json.loads(obj['Body'].read().decode('utf-8'))
        logging.info(f'R2 fetch: {key} ({len(records)} records)')
        return records
    except Exception as e:
        logging.error(f'R2 fetch fail: {e}')
        return []

def write_kpi(conn, species, region, kpis, url, title):
    inserted = updated = 0
    region = REGION_NORMALIZE.get(region, region)
    for kpi in kpis:
        if kpi.get('confidence') == 'low': continue
        vmid = kpi.get('value_mid')
        if vmid is None: continue
        metric = kpi.get('kpi','unknown')
        year   = kpi.get('year') or 2024
        kpi_id = f"{metric}_{species}_{region.lower()}"
        existing = conn.execute(
            "SELECT id,value,value_min,value_max,sample_count,value_stddev "
            "FROM market_kpi WHERE kpi_id=? AND region=? AND year=?",
            (kpi_id, region, year)).fetchone()
        if existing:
            eid, old_val, old_min, old_max, n, old_std = existing
            n = n or 1; new_n = n + 1
            new_val = (old_val*n + vmid)/new_n
            delta = vmid - old_val; delta2 = vmid - new_val
            old_m2 = ((old_std or 0)**2)*(n-1)
            new_m2 = old_m2 + delta*delta2
            new_std = math.sqrt(new_m2/(new_n-1)) if new_n>1 else 0
            mins = [x for x in [old_min,kpi.get('value_min'),vmid] if x is not None]
            maxs = [x for x in [old_max,kpi.get('value_max'),vmid] if x is not None]
            conn.execute("""UPDATE market_kpi SET
                value=?,value_min=?,value_max=?,sample_count=?,value_stddev=?,
                confirmed=MAX(confirmed,1),updated_at=? WHERE id=?""",
                (new_val,min(mins) if mins else None,max(maxs) if maxs else None,
                 new_n,new_std,datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),eid))
            updated += 1
        else:
            conn.execute("""INSERT INTO market_kpi
                (id,region,country,species,production_stage,kpi_id,value,value_min,value_max,
                 unit,year,credibility,source_type,source_url,source_title,raw_text,language,
                 confirmed,updated_at,sample_count,value_stddev)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                str(uuid.uuid4()),region,
                'CN' if region.startswith('CN') else
                'SEA' if region.startswith('SEA') else 'GLOBAL',
                species,kpi.get('condition',''),kpi_id,
                vmid,kpi.get('value_min'),kpi.get('value_max'),
                kpi.get('unit',''),year,3,'academic_background',
                url,title,f"process_raw|{kpi.get('condition','')}",
                'zh-CN',1,datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),1,None))
            inserted += 1
    if inserted+updated > 0: conn.commit()
    return inserted, updated

def write_evidence(conn, record, kpis):
    inserted = 0
    query = record.get('query','')
    url   = record.get('url','')
    title = record.get('title','')
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
            str(uuid.uuid4()),
            'unknown', 'unknown', 'GLOBAL', kpi.get('kpi','unknown'),
            effect, kpi.get('unit',''), ctrl, effect, impv,
            kpi.get('year',2024), kpi.get('study_type','field_trial'),
            3, url, title, kpi.get('raw_text',''),
            1, datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')))
        inserted += 1
    if inserted > 0: conn.commit()
    return inserted

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default='', help='YYYY-MM-DD, default=today')
    args = parser.parse_args()

    date_str = args.date or datetime.utcnow().strftime('%Y-%m-%d')
    logging.info(f'process_raw START date={date_str}')
    tg(f'⚙️ <b>process_raw 開始入庫</b>\n日期: {date_str}')

    records = fetch_from_r2(date_str)
    if not records:
        tg(f'⚠️ R2 無資料: raw/{date_str}/collected.json')
        return

    conn = sqlite3.connect(DB_PATH)
    total_new = total_upd = total_evid = 0
    market_records = [r for r in records if r.get('type') == 'market_kpi']
    ingredient_records = [r for r in records if r.get('type') == 'ingredient_evidence']

    # 處理市場KPI
    for i, rec in enumerate(market_records):
        species = rec.get('species','')
        region  = rec.get('region','')
        text    = rec.get('text','')
        url     = rec.get('url','')
        title   = rec.get('title','')
        if not text or not species: continue

        content = qwen_call(EXTRACT_PROMPT.format(species=species, text=text[:4000]))
        try:
            s = content.find('['); e = content.rfind(']')+1
            if s >= 0 and e > s:
                kpis = json.loads(content[s:e])
                n, u = write_kpi(conn, species, region, kpis, url, title)
                total_new += n; total_upd += u
                if n+u > 0:
                    logging.info(f'[{i+1}/{len(market_records)}] {species}/{region} +{n} upd={u}')
        except Exception as ex:
            logging.warning(f'Extract fail: {ex}')
        time.sleep(3)

    # 處理原料論文
    for rec in ingredient_records:
        text  = rec.get('text','')
        url   = rec.get('url','')
        title = rec.get('title','')
        if not text: continue
        content = qwen_call(INGREDIENT_EXTRACT_PROMPT.format(text=text[:4000]))
        try:
            s = content.find('['); e = content.rfind(']')+1
            if s >= 0 and e > s:
                kpis = json.loads(content[s:e])
                n = write_evidence(conn, rec, kpis)
                total_evid += n
        except Exception:
            pass
        time.sleep(3)

    total_rows = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
    conf_rows  = conn.execute('SELECT COUNT(*) FROM market_kpi WHERE confirmed=1').fetchone()[0]
    conn.close()

    tg(f'✅ <b>process_raw 完成</b>\n'
       f'日期: {date_str}\n'
       f'新增: {total_new} | 更新: {total_upd} | 原料論文: {total_evid}\n'
       f'DB總計: {total_rows}筆 | ✅{conf_rows}')
    logging.info(f'Done. new={total_new} upd={total_upd} evid={total_evid}')

if __name__ == '__main__':
    main()
