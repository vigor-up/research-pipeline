lines = open('local/market_report_extractor.py', encoding='utf-8').readlines()
for i, l in enumerate(lines):
    if 'EXTRACT_PROMPT' in l:
        print(f'{i+1}: {l}', end='')
    if 'report_title' in l and 'species' in l:
        print(f'{i+1}: {l}', end='')
