lines = open('local/market_report_extractor.py', encoding='utf-8').readlines()

new_prompt = [
    'EXTRACT_PROMPT = """你是中國畜牧市場數據分析師。\n',
    '從以下市場報告文字中提取所有可量化的關鍵指標。\n',
    '輸出純JSON，格式如下：\n',
    '{{\n',
    '  "report_date": "YYYY-MM-DD或null",\n',
    '  "report_title": "報告標題",\n',
    '  "species": "整篇報告主要物種（finisher_pig/layer_chicken/beef_cattle/meat_sheep/shrimp/broiler/duck/dairy_cow等）",\n',
    '  "prices": [\n',
    '    {{\n',
    '      "item": "品項名稱",\n',
    '      "species": "該價格對應物種（finisher_pig/beef_cattle/meat_sheep/broiler/layer_chicken/duck/dairy_cow/shrimp/nursery_pig等）",\n',
    '      "value": 數字,\n',
    '      "unit": "元/斤|元/kg|元/噸|元/頭",\n',
    '      "region": "地區或CN_all",\n',
    '      "price_type": "live|carcass|egg|feed|piglet|slaughter"\n',
    '    }}\n',
    '  ],\n',
    '  "market_indicators": [\n',
    '    {{\n',
    '      "metric": "指標名稱",\n',
    '      "species": "對應物種（同上列表）",\n',
    '      "value": 數字或null,\n',
    '      "unit": "單位",\n',
    '      "trend": "up|down|stable|null",\n',
    '      "description": "簡述（30字內）"\n',
    '    }}\n',
    '  ],\n',
    '  "roi_insights": [\n',
    '    "對ROI銷售有用的市場洞察（每條50字內）"\n',
    '  ],\n',
    '  "summary": "100字內市場摘要"\n',
    '}}\n',
    '重要規則：\n',
    '1. 每筆price和indicator必須有正確的species，不得用報告主物種覆蓋其他物種\n',
    '2. 豬肉/白條豬=finisher_pig，仔豬=nursery_pig，雞蛋=layer_chicken，毛雞=broiler\n',
    '3. 只提取文中明確出現的數字，不推測\n',
    '4. 如果某欄位無法確定，填null\n',
    '文字：\n',
    '{text}"""\n',
]

# 替換33-68行（0-indexed 32-67）
lines[32:68] = new_prompt
open('local/market_report_extractor.py', 'w', encoding='utf-8').writelines(lines)
print(f'done, total lines: {len(lines)}')
