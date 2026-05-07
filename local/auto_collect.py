# -*- coding: utf-8 -*-
"""
auto_collect.py
長時程自動化：Tavily搜索 → Qwen3.6語意抽取 → 寫入market_kpi DB
運行時間：18:00 - 08:30（~14.5小時）
不停機設計：每輪間隔、錯誤重試、進度log
"""

import sqlite3
import uuid
import json
import time
import logging
import requests
from datetime import datetime
from pathlib import Path

# ── 設定 ──────────────────────────────────────────────
DB_PATH     = r'D:\LLM\knowledge\market\market_data.db'
LOG_PATH    = r'D:\LLM\workflows\research-pipeline-v2\logs\auto_collect.log'
QWEN_URL    = 'http://localhost:1234/v1/chat/completions'
QWEN_MODEL  = 'qwen3.6-35b'   # 按實際model name調整
TAVILY_KEY  = None             # 從 D:\LLM\API key.txt 讀取

SLEEP_BETWEEN_QUERIES = 8      # 秒，避免Tavily rate limit
SLEEP_BETWEEN_SPECIES = 30     # 秒
MAX_RETRIES = 3
RETRY_DELAY = 15

# ── 目標物種 & 查詢 ────────────────────────────────────
SPECIES_QUERIES = [
    {
        'species': 'dairy_goat',
        'region': 'CN_all',
        'queries': [
            'dairy goat FCR feed conversion ratio ADG daily gain China farm 2022 2023',
            '奶山羊 饲料报酬 日增重 规模化养殖 生产性能 2022 2023',
            'dairy goat milk yield lactation performance China Guanzhong breed benchmark',
            'dairy goat mortality disease loss China farm statistics',
        ]
    },
    {
        'species': 'channel_catfish',
        'region': 'CN_all',
        'queries': [
            'channel catfish FCR ADG survival rate China pond aquaculture 2022 2023',
            '斑点叉尾鮰 饲料系数 日增重 成活率 池塘养殖 2022 2023',
            'channel catfish production performance benchmark China modern farm',
        ]
    },
    {
        'species': 'dairy_cow',
        'region': 'CN_all',
        'queries': [
            'dairy cow FCR milk yield per day China Holstein 2023 benchmark farm',
            '奶牛 产奶量 饲料转化效率 规模化牧场 2023 基准值',
            'dairy cow mastitis mortality China farm disease loss 2022 2023',
        ]
    },
    {
        'species': 'layer_chicken',
        'region': 'CN_all',
        'queries': [
            'layer chicken FCR egg production rate China commercial farm 2023',
            '蛋鸡 料蛋比 产蛋率 死亡率 中国商业化养殖 2023',
            'layer hen Newcastle disease AI mortality China 2022 2023',
        ]
    },
    {
        'species': 'broiler',
        'region': 'CN_all',
        'queries': [
            'broiler FCR ADG mortality China commercial farm 2023 benchmark',
            '肉鸡 料肉比 日增重 死亡率 中国 2023 规模化',
            'broiler necrotic enteritis performance loss China 2022 2023',
        ]
    },
    {
        'species': 'shrimp',
        'region': 'CN_south',
        'queries': [
            'whiteleg shrimp FCR survival rate China pond aquaculture 2022 2023',
            '对虾 饲料系数 成活率 中国南方 池塘养殖 2022 2023',
            'Litopenaeus vannamei EMS mortality China farm benchmark',
        ]
    },
    {
        'species': 'largemouth_catfish',
        'region': 'CN_all',
        'queries': [
            'largemouth catfish FCR ADG China pond 2022 2023',
            '大口鲶 饲料系数 日增重 养殖性能 中国',
        ]
    },
]

# ── Qwen3.6 抽取 Prompt ────────────────────────────────
EXTRACT_PROMPT = """你是動物生產性能數據抽取專家。
從以下文字中抽取{species}的生產性能KPI數據。

只抽取有具體數字的指標，格式輸出JSON數組：
[
  {{
    "kpi": "fcr|adg|mortality|milk_yield|egg_rate|survival|litter_size|other",
    "value_min": 數字或null,
    "value_mid": 數字,
    "value_max": 數字或null,
    "unit": "單位",
    "condition": "條件描述（如90-120kg_commercial）",
    "metric_type": "baseline|disease_penalty",
    "year": 年份數字或null,
    "confidence": "high|medium|low"
  }}
]

如果沒有找到具體數字，回覆空數組 []。
不要編造數字，只抽取文中明確出現的數值。

文字：
{text}"""

# ── 初始化 ─────────────────────────────────────────────
def setup_logging():
    Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(LOG_PATH, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def load_tavily_key():
    global TAVILY_KEY
    try:
        with open(r'D:\LLM\API key.txt', encoding='utf-8') as f:
            for line in f:
                if 'tavily' in line.lower() or 'TAVILY' in line:
                    TAVILY_KEY = line.split('=')[-1].strip().strip('"').strip("'")
                    logging.info(f'Tavily key loaded: {TAVILY_KEY[:8]}...')
                    return True
    except Exception as e:
        logging.error(f'Failed to load Tavily key: {e}')
    return False

# ── Tavily 搜索 ────────────────────────────────────────
def tavily_search(query, max_results=5):
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                'https://api.tavily.com/search',
                json={
                    'api_key': TAVILY_KEY,
                    'query': query,
                    'max_results': max_results,
                    'search_depth': 'advanced',
                    'include_raw_content': True,
                },
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get('results', [])
                logging.info(f'Tavily: "{query[:50]}" → {len(results)} results')
                return results
            else:
                logging.warning(f'Tavily HTTP {resp.status_code}, attempt {attempt+1}')
        except Exception as e:
            logging.warning(f'Tavily error: {e}, attempt {attempt+1}')
        time.sleep(RETRY_DELAY)
    return []

# ── Qwen3.6 抽取 ───────────────────────────────────────
def qwen_extract(text, species):
    if not text or len(text) < 50:
        return []
    # 截斷避免超過context
    text = text[:3000]
    prompt = EXTRACT_PROMPT.format(species=species, text=text)
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                QWEN_URL,
                json={
                    'model': QWEN_MODEL,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.1,
                    'max_tokens': 800,
                },
                timeout=60
            )
            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message']['content']
                # 取出JSON部分
                start = content.find('[')
                end = content.rfind(']') + 1
                if start >= 0 and end > start:
                    extracted = json.loads(content[start:end])
                    logging.info(f'Qwen extracted {len(extracted)} KPIs')
                    return extracted
                return []
        except Exception as e:
            logging.warning(f'Qwen error: {e}, attempt {attempt+1}')
        time.sleep(RETRY_DELAY)
    return []

# ── 寫入 DB ────────────────────────────────────────────
def write_to_db(conn, species, region, kpis, source_url, source_title, year_hint):
    inserted = 0
    for kpi in kpis:
        if kpi.get('confidence') == 'low':
            continue
        if not kpi.get('value_mid'):
            continue
        metric = kpi.get('kpi', 'unknown')
        kpi_id = f"{metric}_{species}_{region.lower()}"
        year = kpi.get('year') or year_hint or 2023

        existing = conn.execute(
            "SELECT id FROM market_kpi WHERE kpi_id=? AND region=? AND year=?",
            (kpi_id, region, year)
        ).fetchone()
        if existing:
            continue

        conn.execute("""
            INSERT INTO market_kpi
                (id, region, country, species, production_stage, kpi_id,
                 value, value_min, value_max, unit, year,
                 credibility, source_type, source_url, source_title,
                 raw_text, language, confirmed, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            str(uuid.uuid4()),
            region, 'CN' if region.startswith('CN') else 'GLOBAL',
            species,
            kpi.get('condition', ''),
            kpi_id,
            kpi['value_mid'],
            kpi.get('value_min'),
            kpi.get('value_max'),
            kpi.get('unit', ''),
            year,
            3,  # credibility: web搜索=3，後續人工確認升4
            'academic_background' if kpi.get('metric_type') == 'baseline' else 'industry_media',
            source_url,
            source_title,
            f"auto_collected | {kpi.get('condition','')}",
            'zh-CN',
            0,  # confirmed=0，待人工確認
            datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        ))
        inserted += 1

    if inserted > 0:
        conn.commit()
    return inserted

# ── 主循環 ─────────────────────────────────────────────
def main():
    setup_logging()
    logging.info('=' * 60)
    logging.info('auto_collect.py START')
    logging.info('=' * 60)

    if not load_tavily_key():
        logging.error('No Tavily key, abort.')
        return

    conn = sqlite3.connect(DB_PATH)
    total_inserted = 0
    start_time = time.time()

    # 持續循環直到手動停止（Ctrl+C 或 14小時後）
    MAX_HOURS = 14
    round_num = 0

    while True:
        elapsed = (time.time() - start_time) / 3600
        if elapsed > MAX_HOURS:
            logging.info(f'Max time {MAX_HOURS}h reached. Done.')
            break

        round_num += 1
        logging.info(f'--- Round {round_num} | Elapsed {elapsed:.1f}h | Total inserted: {total_inserted} ---')

        for sp in SPECIES_QUERIES:
            species = sp['species']
            region  = sp['region']

            # 檢查這個物種已有多少筆
            existing_count = conn.execute(
                "SELECT COUNT(*) FROM market_kpi WHERE species=? AND confirmed=1",
                (species,)
            ).fetchone()[0]
            unconfirmed = conn.execute(
                "SELECT COUNT(*) FROM market_kpi WHERE species=? AND confirmed=0",
                (species,)
            ).fetchone()[0]
            logging.info(f'{species}: {existing_count} confirmed, {unconfirmed} unconfirmed')

            for query in sp['queries']:
                results = tavily_search(query)
                time.sleep(SLEEP_BETWEEN_QUERIES)

                for r in results:
                    raw = r.get('raw_content') or r.get('content', '')
                    url = r.get('url', '')
                    title = r.get('title', '')

                    kpis = qwen_extract(raw, species)
                    if kpis:
                        n = write_to_db(conn, species, region, kpis, url, title, 2023)
                        total_inserted += n
                        if n > 0:
                            logging.info(f'  ✅ {species} +{n} rows from {url[:60]}')

            time.sleep(SLEEP_BETWEEN_SPECIES)

        # 每輪結束統計
        total_rows = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
        logging.info(f'Round {round_num} done. DB total: {total_rows} rows')

        # 第二輪開始間隔拉長（避免重複抓同樣資料）
        if round_num >= 2:
            logging.info('Sleeping 1800s before next round...')
            time.sleep(1800)  # 30分鐘後再跑下一輪

    conn.close()
    logging.info(f'auto_collect.py END. Total inserted: {total_inserted}')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info('Interrupted by user.')
