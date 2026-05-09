# -*- coding: utf-8 -*-
"""
smart_query.py
智慧問答核心 — 取代 unified_query.query()
流程：
  1. Qwen 意圖分類
  2. 查 DB / ChromaDB / RAGFlow
  3. 有資料 → Qwen 合成口語化回答
  4. 無資料 → 背景觸發 auto_collect_v5_integrated --mode single
             → 立刻回覆「收集中」
             → 收集完成後 Telegram 推送答案
"""

import sys, subprocess, threading, logging, requests, re, json
sys.path.insert(0, r'D:\LLM\workflows\research-pipeline-v2\local')

TELEGRAM_TOKEN = '8703702788:AAFKEiGmLYTAuFVG9GX-gRtVTUUyi-f_5mM'
TELEGRAM_TOKEN_NEW = '8562713821:AAHh8D26iesEqiDYoxHJYtlBZcn-dz-47s4'
TELEGRAM_CHAT  = 897274134
BASE_DIR       = r'D:\LLM\workflows\research-pipeline-v2'
QWEN_URL       = 'http://localhost:1234/v1/chat/completions'
QWEN_MODEL     = 'Qwen3.6-35B-A3B-Q6_K.gguf'

# ALL_SPECIES 裡沒有的組合，動態補進來
DYNAMIC_SPECIES_MAP = {
    'broiler':       ['FCR', 'ADG', 'mortality'],
    'finisher_pig':  ['FCR', 'ADG', 'mortality'],
    'beef_cattle':   ['FCR', 'ADG', 'mortality'],
    'layer_chicken': ['FCR', 'egg_rate', 'mortality'],
    'meat_sheep':    ['FCR', 'ADG', 'mortality'],
    'shrimp':        ['FCR', 'survival', 'mortality'],
}

def tg(msg):
    for token in (TELEGRAM_TOKEN, TELEGRAM_TOKEN_NEW):
        try:
            requests.post(
                f'https://api.telegram.org/bot{token}/sendMessage',
                json={'chat_id': TELEGRAM_CHAT, 'text': msg, 'parse_mode': 'HTML'},
                timeout=10)
        except Exception as e:
            logging.warning(f'TG: {e}')

def qwen_call(prompt, max_tokens=600):
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

def trigger_collect(species, region, missing_kpis, original_question):
    """背景觸發收集，完成後推送答案"""
    def _run():
        kpi_str = '/'.join(missing_kpis) if missing_kpis else 'FCR/ADG/mortality'
        tg(f'⚙️ <b>自動補收中</b>\n物種: {species} | 地區: {region}\n缺少: {kpi_str}\n預計 5-15 分鐘')

        # 確認 ALL_SPECIES 有沒有這個組合，沒有就用 --mode single 強跑
        cmd = [
            sys.executable,
            r'local\auto_collect_v5_integrated.py',
            '--mode', 'single',
            '--species', species,
            '--region', region
        ]
        try:
            result = subprocess.run(
                cmd, cwd=BASE_DIR,
                capture_output=True, text=True,
                encoding='utf-8', timeout=1800)
            if result.returncode == 0:
                # 收集完成，重新查詢回答
                from unified_query import query
                answer = query(original_question, mode='auto')
                tg(f'✅ <b>補收完成，重新回答</b>\n\n{answer}')
            else:
                err = result.stderr[-300:] if result.stderr else '未知錯誤'
                tg(f'❌ 補收失敗: {err}')
        except subprocess.TimeoutExpired:
            tg(f'⏰ 補收超時（30分鐘），請手動跑 --mode single --species {species} --region {region}')
        except Exception as e:
            tg(f'❌ 補收錯誤: {e}')

    threading.Thread(target=_run, daemon=True).start()

def smart_query(question):
    """
    主入口：智慧查詢 + 自動補收
    """
    from unified_query import (
        classify_intent, query_db_kpi, query_db_compare,
        query_chromadb, query_ragflow,
        REGION_MAP, SPECIES_MAP, KPI_MAP,
        SYNTHESIZE_PROMPT
    )

    # 1. 意圖分類
    intent_data = classify_intent(question)
    intent   = intent_data.get('intent', 'mixed')
    species  = intent_data.get('species')
    region   = intent_data.get('region')
    kpi      = intent_data.get('kpi')
    compare  = intent_data.get('compare_regions')
    keywords = intent_data.get('keywords', [question])

    results = {}
    missing_info = []  # 記錄哪些資料缺失，用於觸發收集

    # 2. 查詢
    if intent in ('number', 'mixed'):
        if compare and len(compare) >= 2:
            # 跨地區比較：逐一查，記錄缺失
            import sqlite3
            from unified_query import DB_PATH
            conn = sqlite3.connect(DB_PATH)
            sp = SPECIES_MAP.get(species, species) if species else species
            kpi_key = KPI_MAP.get(kpi, kpi) if kpi else 'fcr'
            lines = [f'📊 {sp} {kpi_key} 跨地區比較：']
            any_found = False
            for reg in compare:
                region_code = REGION_MAP.get(reg, reg)
                row = conn.execute("""
                    SELECT value, unit, year FROM market_kpi
                    WHERE species=? AND region=? AND kpi_id LIKE ? AND confirmed=1
                    ORDER BY credibility DESC LIMIT 1""",
                    (sp, region_code, f'%{kpi_key}%')).fetchone()
                if row:
                    lines.append(f'  {reg}（{region_code}）: {row[0]:.3f} {row[1]} ({row[2]}年)')
                    any_found = True
                else:
                    lines.append(f'  {reg}（{region_code}）: 暫無數據')
                    if sp and sp in DYNAMIC_SPECIES_MAP:
                        missing_info.append((sp, region_code, DYNAMIC_SPECIES_MAP[sp]))
            conn.close()
            if any_found:
                results['db'] = '\n'.join(lines)
        elif species and kpi:
            db_result = query_db_kpi(species, region, kpi)
            if db_result:
                results['db'] = db_result
            else:
                sp = SPECIES_MAP.get(species, species) if species else species
                rc = REGION_MAP.get(region, region) if region else None
                if sp and rc and sp in DYNAMIC_SPECIES_MAP:
                    missing_info.append((sp, rc, DYNAMIC_SPECIES_MAP[sp]))
        elif species:
            db_result = query_db_kpi(species, region, kpi)
            if db_result:
                results['db'] = db_result

    if intent in ('academic', 'mixed'):
        chroma = query_chromadb(keywords)
        if chroma:
            results['chroma'] = chroma

    if intent in ('market', 'mixed'):
        ragflow = query_ragflow(question)
        if ragflow:
            results['ragflow'] = ragflow

    # 3. 有資料 → Qwen 合成
    if results:
        synthesized = qwen_call(SYNTHESIZE_PROMPT.format(
            question=question,
            db_result=results.get('db') or '無數據',
            chroma_result=results.get('chroma') or '無相關論文',
            ragflow_result=results.get('ragflow') or '無市場資料'),
            max_tokens=600)
        answer = synthesized or '\n\n'.join(results.values())

        # 有部分缺失 → 背景補收，不阻塞回答
        for sp, rc, kpis in missing_info:
            trigger_collect(sp, rc, kpis, question)

        return answer

    # 4. 完全無資料 → 觸發補收，立刻回覆
    if missing_info:
        for sp, rc, kpis in missing_info:
            trigger_collect(sp, rc, kpis, question)
        regions_str = '、'.join(set(rc for _, rc, _ in missing_info))
        return f'目前缺少 {regions_str} 的數據，已自動啟動收集，預計 5-15 分鐘後完成。完成後會直接推送答案給你。'

    return '查無相關資料，且無法自動補收（物種/地區不在支援清單）。'

