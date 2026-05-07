lines = open('local/market_report_extractor.py', encoding='utf-8').readlines()

# 177行（0-indexed 176）：indicator也用per-item species
lines[176] = "        species_ind = m.get('species', species_main)\n" + \
             "        kpi_id = f\"market_indicator_{species_ind}_{metric}_{year}\"\n"

# 找indicator的INSERT中的species_main
for i, l in enumerate(lines):
    if 'species_main,' in l and i > 176:
        lines[i] = lines[i].replace('species_main,', 'species_ind,')
        print(f'fixed line {i+1}')
        break

open('local/market_report_extractor.py', 'w', encoding='utf-8').writelines(lines)
print('done')
