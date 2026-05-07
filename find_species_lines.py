lines = open('local/market_report_extractor.py', encoding='utf-8').readlines()

# 找到需要修改的行
for i, l in enumerate(lines):
    if 'species_main, ' in l and 'market_price' in l:
        print(f'{i+1}: {l}', end='')
    if "kpi_id   = f\"spot_price_{species_main}" in l:
        print(f'{i+1}: {l}', end='')
