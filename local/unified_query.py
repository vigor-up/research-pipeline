# -*- coding: utf-8 -*-
"""
unified_query.py
統一查詢閘道 — 三庫智能路由
QueryRouter（Qwen意圖分類，~50 token）→ 查對應DB → 回傳結果
支援：market_data.db / ChromaDB / RAGFlow / 複合查詢
供 Telegram Bot、QClaw、PPT Engine 統一調用
"""

import sqlite3, json, requests, re, logging
from datetime import datetime

# ── 路徑設定 ──────────────────────────────────────────────
DB_PATH        = r'D:\LLM\knowledge\market\market_data.db'
CHROMA_PATH    = r'D:\LLM\knowledge\biotech\db'
QWEN_URL       = 'http://localhost:1234/v1/chat/completions'
QWEN_MODEL     = 'qwen3.6-35b'
RAGFLOW_URL    = 'http://localhost/api/v1'
RAGFLOW_API_KEY     = 'ragflow-fcCq8K0sVcefhVHboEmBOOzt5S2cQ7jCcHT5cCwhWRM'
RAGFLOW_DATASET_ID  = '6bec28ac4a8b11f190c657ee8852d812'  # 畜牧KPI研究
TELEGRAM_TOKEN = '8703702788:AAFKEiGmLYTAuFVG9GX-gRtVTUUyi-f_5mM'
TELEGRAM_CHAT  = 897274134

# ── 地區標準化 ────────────────────────────────────────────
REGION_MAP = {
    '東北': 'CN_northeast', '華北': 'CN_north', '華南': 'CN_south',
    '華東': 'CN_east',      '華中': 'CN_central','西南': 'CN_southwest',
    '馬來西亞': 'SEA_malaysia', '泰國': 'SEA_thailand',
    '越南': 'SEA_vietnam',   '台灣': 'TW_all',
    'northeast': 'CN_northeast', 'north': 'CN_north',
    'south': 'CN_south',     'east': 'CN_east',
    'malaysia': 'SEA_malaysia',  'thailand': 'SEA_thailand',
    'CN': 'CN_all', 'CN_all': 'CN_all', '全國': 'CN_all', '中國': 'CN_all',
    'CN_northeast': 'CN_northeast', 'CN_north': 'CN_north',
    'CN_south': 'CN_south', 'CN_east': 'CN_east',
    'CN_central': 'CN_central', 'CN_southwest': 'CN_southwest',
}

SPECIES_MAP = {
    '豬': 'finisher_pig', '育肥豬': 'finisher_pig', '豬': 'finisher_pig',
    '牛': 'beef_cattle',  '肉牛': 'beef_cattle',    '乳牛': 'dairy_cow',
    '羊': 'meat_sheep',   '肉羊': 'meat_sheep',
    '雞': 'broiler',      '肉雞': 'broiler',         '蛋雞': 'layer_chicken',
    '蝦': 'shrimp',       '對蝦': 'shrimp',          '白蝦': 'shrimp',
    '鴨': 'duck',         '魚': 'tilapia',
    'pig': 'finisher_pig', 'cattle': 'beef_cattle',
    'broiler': 'broiler',  'shrimp': 'shrimp',
    'chicken': 'layer_chicken',
}

KPI_MAP = {
    'FCR': 'fcr', '飼料轉化率': 'fcr', '料肉比': 'fcr',
    'ADG': 'adg', '日增重': 'adg',
    '死亡率': 'mortality', 'mortality': 'mortality',
    '產蛋率': 'egg_rate',  '產奶': 'milk_yield',
    '存活率': 'survival',
}

# ── 意圖分類 prompt ───────────────────────────────────────
INTENT_PROMPT = """你是查詢路由器。分析問題意圖，輸出JSON。
問題：{question}

意圖類型：
- number：需要精確數字（FCR/ADG/死亡率/價格/ROI計算）
- academic：需要學術論文/研究支撐/競爭情報
- mixed：需要多個類型

地區代碼規則（必須輸出以下標準代碼之一）：
東北/遼寧/吉林/黑龍江 → CN_northeast
華北/北京/天津/河北 → CN_north
華南/廣東/廣西/海南 → CN_south
華東/上海/江蘇/浙江/山東 → CN_east
華中/河南/湖北/湖南 → CN_central
西南/四川/重慶/雲南 → CN_southwest
全國/中國/不限 → CN_all
馬來西亞 → SEA_malaysia | 泰國 → SEA_thailand | 越南 → SEA_vietnam | 台灣 → TW_all

物種代碼規則：
豬/育肥豬/finisher pig → finisher_pig
牛/肉牛/beef cattle → beef_cattle
雞/肉雞/broiler → broiler
蛋雞/layer chicken → layer_chicken
羊/肉羊 → meat_sheep
蝦/對蝦/shrimp → shrimp

輸出JSON（只輸出JSON不要其他）：
{{
  "intent": "number|academic|mixed",
  "species": "物種英文名或null",
  "region": "標準地區代碼或null（比較問題可為null）",
  "kpi": "fcr|adg|mortality|milk_yield|egg_rate|survival或null",
  "compare_regions": ["CN_northeast","CN_north"] 或null（有比較意圖時必填）,
  "keywords": ["關鍵詞1","關鍵詞2"]
}}"""

SYNTHESIZE_PROMPT = """你是動物營養市場專家，用口語化繁體中文直接回答問題，像在跟業務人員對話。

問題：{question}

可用資料：
市場KPI：{db_result}
學術論文：{chroma_result}
市場資訊：{ragflow_result}

回答規則：
- 直接給結論，數字要說出來
- 如果某地區沒資料就說「暫無該地區數據」
- 口語化，不要條列式格式
- 150字以內
- 只輸出回答，不要重複問題"""

# ── Qwen 呼叫 ─────────────────────────────────────────────
def qwen_call(prompt, max_tokens=500):
    try:
        resp = requests.post(QWEN_URL, json={
            'model': QWEN_MODEL,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.1, 'max_tokens': max_tokens, 'stream': False,
            'chat_template_kwargs': {'enable_thinking': False}},
            timeout=120)
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            content = re.sub(r'</think>', '', content).strip()
            content = re.sub(r'<think>.*', '', content, flags=re.DOTALL).strip()
            return content
    except Exception as e:
        logging.warning(f'Qwen: {e}')
    return ''

def classify_intent(question):
    """意圖分類，~50 token"""
    content = qwen_call(INTENT_PROMPT.format(question=question), max_tokens=200)
    try:
        s = content.find('{'); e = content.rfind('}') + 1
        if s >= 0 and e > s:
            return json.loads(content[s:e])
    except Exception:
        pass
    return {'intent': 'mixed', 'species': None, 'region': None,
            'kpi': None, 'compare_regions': None, 'keywords': [question]}

# ── 軌道A：market_data.db 查詢 ───────────────────────────
def query_db_kpi(species, region, kpi):
    """精確KPI查詢，含均值/stddev/樣本數"""
    conn = sqlite3.connect(DB_PATH)
    try:
        region = REGION_MAP.get(region, region) if region else None
        species = SPECIES_MAP.get(species, species) if species else None
        kpi_key = KPI_MAP.get(kpi, kpi) if kpi else None

        if not species:
            return None

        if region:
            region_code = REGION_MAP.get(region, region)
            kpi_id_pattern = f"%{kpi_key}%{region_code.lower()}%" if kpi_key else f"%{region_code.lower()}%"
            rows = conn.execute("""
                SELECT kpi_id, value, COALESCE(value_stddev,0), COALESCE(sample_count,1),
                       unit, year, credibility
                FROM market_kpi
                WHERE species=? AND region=? AND kpi_id LIKE ? AND confirmed=1
                  AND kpi_id NOT LIKE '%penalty%' AND kpi_id NOT LIKE '%saving%'
                  AND kpi_id NOT LIKE '%spot_price%' AND kpi_id NOT LIKE '%slaughter_price%'
                ORDER BY credibility DESC, year DESC LIMIT 5""",
                (SPECIES_MAP.get(species, species), region_code, kpi_id_pattern)).fetchall()
        else:
            rows = conn.execute("""
                SELECT kpi_id, value, COALESCE(value_stddev,0), COALESCE(sample_count,1),
                       unit, year, credibility
                FROM market_kpi
                WHERE species=? AND kpi_id LIKE ? AND confirmed=1
                  AND kpi_id NOT LIKE '%penalty%' AND kpi_id NOT LIKE '%saving%'
                ORDER BY credibility DESC, year DESC LIMIT 10""",
                (species, f"%{kpi_key}%")).fetchall()

        if not rows:
            return None

        results = []
        for r in rows:
            std_str = f'±{r[2]:.3f}' if r[2] > 0 else ''
            results.append(f"{r[0]}: {r[1]:.3f}{std_str} {r[4]} (n={r[3]}, {r[5]}年, 可信度{r[6]})")
        return '\n'.join(results)
    finally:
        conn.close()

def query_db_compare(species, regions, kpi):
    """跨地區比較"""
    conn = sqlite3.connect(DB_PATH)
    try:
        kpi_key = KPI_MAP.get(kpi, kpi) if kpi else 'fcr'
        sp = SPECIES_MAP.get(species, species) if species else species
        results = {}
        for region in regions:
            region_code = REGION_MAP.get(region, region)
            # 地區中文顯示名
            region_zh = {v: k for k, v in REGION_MAP.items() if len(k) <= 4}.get(region_code, region_code)
            row = conn.execute("""
                SELECT value, COALESCE(value_stddev,0), COALESCE(sample_count,1), unit, year
                FROM market_kpi
                WHERE species=? AND region=? AND kpi_id LIKE ? AND confirmed=1
                ORDER BY credibility DESC LIMIT 1""",
                (sp, region_code, f"{kpi_key}%")).fetchone()
            if row:
                std_str = f'±{row[1]:.3f}' if row[1] > 0 else ''
                results[region_zh] = f"{row[0]:.3f}{std_str} {row[3]} (n={row[2]}, {row[4]}年)"
            else:
                results[region_zh] = "暫無數據"
        if all(v == "暫無數據" for v in results.values()):
            return None
        lines = [f"📊 {sp} {kpi_key} 跨地區比較："]
        for region_label, val in results.items():
            lines.append(f"  {region_label}: {val}")
        return '\n'.join(lines)
    finally:
        conn.close()

def query_db_roi(species, region):
    """ROI快速查詢"""
    conn = sqlite3.connect(DB_PATH)
    try:
        sp = SPECIES_MAP.get(species, species) if species else species
        region_code = REGION_MAP.get(region, region) if region else 'CN_northeast'
        fcr_row = conn.execute("""
            SELECT value, unit FROM market_kpi
            WHERE species=? AND region=? AND kpi_id LIKE 'fcr%' AND confirmed=1
            ORDER BY credibility DESC LIMIT 1""", (sp, region_code)).fetchone()
        price_row = conn.execute("""
            SELECT value, unit FROM market_kpi
            WHERE species=? AND kpi_id LIKE 'spot%' AND confirmed=1
            ORDER BY year DESC LIMIT 1""", (sp,)).fetchone()
        if not fcr_row:
            return None
        fcr = fcr_row[0]
        price_str = f"現貨價={price_row[0]}{price_row[1]}" if price_row else "價格未知"
        return f"{sp}/{region_code}: FCR={fcr:.2f}, {price_str}"
    finally:
        conn.close()

# ── 軌道B：ChromaDB 查詢（使用 search_engine.py 同款邏輯）──
_embed_model_cache = {}

def _get_embed_model():
    if 'model' not in _embed_model_cache:
        from sentence_transformers import SentenceTransformer
        _embed_model_cache['model'] = SentenceTransformer('BAAI/bge-m3')
    return _embed_model_cache['model']

def query_chromadb(keywords, n_results=5, topic=None, min_quality=0):
    try:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        col = client.get_collection(name='biotech_papers')  # 不傳 ef，避免衝突
        query_text = ' '.join(keywords) if isinstance(keywords, list) else keywords
        model = _get_embed_model()
        qvec = model.encode([query_text], normalize_embeddings=True).tolist()

        where_clauses = []
        if topic:
            where_clauses.append({'topic': topic})
        if min_quality > 0:
            where_clauses.append({'quality_score': {'$gte': min_quality}})
        where = None
        if len(where_clauses) == 1:
            where = where_clauses[0]
        elif len(where_clauses) > 1:
            where = {'$and': where_clauses}

        results = col.query(
            query_embeddings=qvec,
            n_results=n_results * 2,
            where=where,
            include=['documents', 'metadatas', 'distances']
        )
        if not results['documents'] or not results['documents'][0]:
            return None

        lines = []
        for i in range(min(n_results, len(results['documents'][0]))):
            meta = results['metadatas'][0][i]
            dist = results['distances'][0][i]
            sim  = round(1 - dist, 3)
            title   = meta.get('title', 'Unknown')[:80]
            year    = meta.get('year', '')
            species = meta.get('species', '')
            fcr     = meta.get('FCR', 'N/A')
            adg     = meta.get('ADG', 'N/A')
            summary = meta.get('intel_summary', '')[:200]
            lines.append(
                f"📄 [{sim}] {title} ({year}, {species})\n"
                f"   FCR={fcr} ADG={adg}\n"
                f"   {summary}"
            )
        return '\n\n'.join(lines)
    except Exception as e:
        logging.warning(f'ChromaDB query: {e}')
    return None

# ── 軌道C：RAGFlow（已廢棄，功能由 SQLite + ChromaDB 覆蓋）──
def query_ragflow(question, top_k=3):
    return None  # RAGFlow 維護成本高，暫停使用

# ── 主查詢入口 ────────────────────────────────────────────
def query(question, mode='auto'):
    """
    統一查詢閘道
    mode: auto=自動路由 | db=只查market_db | academic=只查ChromaDB | market=只查RAGFlow
    """
    results = {}

    if mode == 'auto':
        intent_data = classify_intent(question)
        intent = intent_data.get('intent', 'mixed')
        species  = intent_data.get('species')
        region   = intent_data.get('region')
        kpi      = intent_data.get('kpi')
        compare  = intent_data.get('compare_regions')
        keywords = intent_data.get('keywords', [question])
    else:
        intent = mode
        species = region = kpi = compare = None
        keywords = [question]

    # 跨地區比較 → 放進 results 繼續走 Qwen 合成
    if compare and len(compare) >= 2:
        # species=None 時從 keywords 推斷
        if not species:
            kw_str = ' '.join(keywords).lower()
            for zh, en in [('肉雞','broiler'),('broiler','broiler'),('豬','finisher_pig'),
                           ('牛','beef_cattle'),('蛋雞','layer_chicken'),('羊','meat_sheep'),('蝦','shrimp')]:
                if zh in kw_str:
                    species = en
                    break
        results['db'] = query_db_compare(species, compare, kpi or 'FCR')

    # 市場KPI數字（compare 已有結果就跳過，避免覆蓋）
    if intent in ('number', 'mixed', 'db') and 'db' not in results:
        if species and kpi:
            db_result = query_db_kpi(species, region, kpi)
        elif species:
            db_result = query_db_roi(species, region)
        else:
            db_result = None
        results['db'] = db_result

    # 學術論文
    if intent in ('academic', 'mixed'):
        results['chroma'] = query_chromadb(keywords)

    # 市場背景
    if intent in ('market', 'mixed'):
        results['ragflow'] = query_ragflow(question)

    # 有資料 → 一律走 Qwen 合成口語化回答
    non_empty = {k: v for k, v in results.items() if v}
    if non_empty:
        synthesized = qwen_call(SYNTHESIZE_PROMPT.format(
            question=question,
            db_result=results.get('db') or '無數據',
            chroma_result=results.get('chroma') or '無相關論文',
            ragflow_result=results.get('ragflow') or '無'),
            max_tokens=600)
        return synthesized or '\n\n'.join(non_empty.values())

    return '查無相關資料，建議補充收集該物種/地區數據。'

def format_response(question, db_result, chroma_result, ragflow_result, intent):
    parts = []
    if db_result:
        parts.append(f"📊 市場KPI數據：\n{db_result}")
    if chroma_result:
        parts.append(f"🔬 學術論文：\n{chroma_result}")
    if ragflow_result:
        parts.append(f"📰 市場資訊：\n{ragflow_result}")
    return '\n\n'.join(parts) if parts else '查無相關資料。'

# ── Telegram Bot 整合 ─────────────────────────────────────
def handle_bot_command(text):
    """
    /roi [物種] [地區] → ROI數據
    /compare [物種] [KPI] [地區1] [地區2] → 跨地區比較
    /ask [問題] → 統一查詢
    /market [物種] → 市場背景
    /defense [原料] → 學術支撐（查ChromaDB）
    """
    parts = text.strip().split()
    cmd = parts[0].lower() if parts else ''

    if cmd == '/roi' and len(parts) >= 2:
        species = SPECIES_MAP.get(parts[1], parts[1])
        region  = REGION_MAP.get(parts[2], parts[2]) if len(parts) > 2 else 'CN_northeast'
        result  = query_db_roi(species, region) or '無數據'
        return f"💰 ROI查詢\n{result}"

    elif cmd == '/compare' and len(parts) >= 4:
        species = SPECIES_MAP.get(parts[1], parts[1])
        kpi     = KPI_MAP.get(parts[2], parts[2])
        regions = parts[3:]
        result  = query_db_compare(species, regions, kpi) or '無數據'
        return result

    elif cmd == '/defense' and len(parts) >= 2:
        ingredient = ' '.join(parts[1:])
        result = query_chromadb([ingredient], n_results=5)
        return f"🔬 學術支撐：{ingredient}\n{result}" if result else '無相關論文。'

    elif cmd == '/market' and len(parts) >= 2:
        q = ' '.join(parts[1:]) + ' 市場趨勢'
        result = query_ragflow(q)
        return f"📰 市場資訊\n{result}" if result else '無市場資料。'

    elif cmd == '/ask' and len(parts) >= 2:
        question = ' '.join(parts[1:])
        return query(question, mode='auto')

    else:
        return query(text, mode='auto')

# ── CLI 測試 ──────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        question = ' '.join(sys.argv[1:])
        print(f"\n問題：{question}")
        print("-" * 50)
        result = query(question)
        print(result)
    else:
        # 互動模式
        print("統一查詢閘道（輸入 quit 退出）")
        while True:
            q = input("\n> ").strip()
            if q.lower() in ('quit', 'exit', 'q'): break
            if not q: continue
            print(query(q))
