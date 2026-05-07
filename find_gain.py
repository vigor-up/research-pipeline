lines = open('local/formula_advisor.py', encoding='utf-8').readlines()
for i, l in enumerate(lines):
    if 'gain_map' in l:
        print(f'{i+1}: {l}', end='')
    if 'layer_chicken' in l and ('1.5' in l or 'gain' in l.lower()):
        print(f'{i+1}: {l}', end='')
