lines = open('local/market_report_extractor.py', encoding='utf-8').readlines()

# 154行（0-indexed 153）：kpi_id用per-price species
lines[153] = "        species_price = p.get('species', species_main)\n" + \
             "        kpi_id   = f\"spot_price_{species_price}_{ptype}_{safe_item}_{region.lower()}\"\n"

# 165行（現在變166因為插入了一行，0-indexed 165）
for i, l in enumerate(lines):
    if 'species_main, ' in l and 'market_price' in l:
        lines[i] = lines[i].replace('species_main,', 'species_price,')
        print(f'fixed line {i+1}')
        break

open('local/market_report_extractor.py', 'w', encoding='utf-8').writelines(lines)
print('done')
