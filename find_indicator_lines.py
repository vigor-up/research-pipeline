lines = open('local/market_report_extractor.py', encoding='utf-8').readlines()
for i, l in enumerate(lines):
    if 'market_indicator_{species_main}' in l:
        print(f'{i+1}: {l}', end='')
    if 'species_main,' in l and 'market_indicator' in lines[i-3] if i>3 else False:
        print(f'{i+1}: {l}', end='')
