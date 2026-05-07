import re

content = open('local/market_report_extractor.py', encoding='utf-8').read()

# 1. 更新EXTRACT_PROMPT - 在prices和indicators加species欄位
old_prompt_snippet = '"species": "主要物種（finisher_pig/layer_chicken/beef_cattle/meat_sheep/shrimp等）",'
new_prompt_snippet = '"species": "整篇報告主要物種（finisher_pig/layer_chicken/beef_cattle/meat_sheep/broiler/duck/dairy_cow等）",'
content = content.replace(old_prompt_snippet, new_prompt_snippet)

old_price_format = '''      "item": "品項名稱",
      "value": 數字,
      "unit": "元/斤|元/kg|元/噸|元/頭",
      "region": "地區或CN_all",
      "price_type": "live|carcass|egg|feed|piglet"'''
new_price_format = '''      "item": "品項名稱",
      "species": "該價格對應物種（finisher_pig/beef_cattle/meat_sheep/broiler/layer_chicken/duck/dairy_cow/shrimp/nursery_pig）",
      "value": 數字,
      "unit": "元/斤|元/kg|元/噸|元/頭",
      "region": "地區或CN_all",
      "price_type": "live|carcass|egg|feed|piglet|slaughter"'''
content = content.replace(old_price_format, new_price_format)

old_indicator_format = '''      "metric": "指標名稱",
      "value": 數字或null,
      "unit": "單位",
      "trend": "up|down|stable|null",
      "description": "簡述（30字內）"'''
new_indicator_format = '''      "metric": "指標名稱",
      "species": "對應物種（同上列表）",
      "value": 數字或null,
      "unit": "單位",
      "trend": "up|down|stable|null",
      "description": "簡述（30字內）"'''
content = content.replace(old_indicator_format, new_indicator_format)

old_rules = '只提取文中明確出現的數字，不推測。\n如果某欄位無法確定，填null。'
new_rules = '''重要規則：
1. 每筆price和indicator必須有正確species，不得用報告主物種覆蓋其他物種
2. 豬肉/白條豬=finisher_pig，仔豬=nursery_pig，雞蛋=layer_chicken，毛雞=broiler
3. 只提取文中明確出現的數字，不推測
4. 如果某欄位無法確定，填null'''
content = content.replace(old_rules, new_rules)

# 2. write_to_db - price用per-item species
old_kpi = "        kpi_id   = f\"spot_price_{species_main}_{ptype}_{safe_item}_{region.lower()}\""
new_kpi = "        species_price = p.get('species', species_main)\n        kpi_id   = f\"spot_price_{species_price}_{ptype}_{safe_item}_{region.lower()}\""
content = content.replace(old_kpi, new_kpi)

old_insert_species = "                species_main, 'market_price', kpi_id,"
new_insert_species = "                species_price, 'market_price', kpi_id,"
content = content.replace(old_insert_species, new_insert_species, 1)

# 3. indicator用per-item species
old_ind_kpi = "        kpi_id = f\"market_indicator_{species_main}_{metric}_{year}\""
new_ind_kpi = "        species_ind = m.get('species', species_main)\n        kpi_id = f\"market_indicator_{species_ind}_{metric}_{year}\""
content = content.replace(old_ind_kpi, new_ind_kpi)

old_ind_insert = "                species_main, 'market_indicator', kpi_id,"
new_ind_insert = "                species_ind, 'market_indicator', kpi_id,"
content = content.replace(old_ind_insert, new_ind_insert, 1)

# 4. 加RAGFlow常數和upload函數
ragflow_const = """
RAGFLOW_API_KEY = 'ragflow-fcCq8K0sVcefhVHboEmBOOzt5S2cQ7jCcHT5cCwhWRM'
RAGFLOW_BASE_URL = 'http://localhost'
RAGFLOW_DATASET_ID = '5a68aa6e49ba11f190c657ee8852d812'
"""
content = content.replace("MCP_URL        = 'http://localhost:8765/call'",
                          "MCP_URL        = 'http://localhost:8765/call'" + ragflow_const)

ragflow_func = '''
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

'''
content = content.replace('def tg(msg):', ragflow_func + 'def tg(msg):')

# 5. process_report加upload呼叫
content = content.replace(
    '    return n, report',
    "    doc_name = f\"market_{extracted.get('report_date','unknown')}_{extracted.get('species','unknown')}.txt\"\n    upload_to_ragflow(text, doc_name)\n    return n, report"
)

open('local/market_report_extractor.py', 'w', encoding='utf-8').write(content)
print('written')

import ast
ast.parse(content)
print('syntax ok')
