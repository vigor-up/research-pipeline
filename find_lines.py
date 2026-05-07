lines = open('local/formula_advisor.py', encoding='utf-8').readlines()

# 找關鍵行號
for i, l in enumerate(lines):
    if 'feed_saved  = (fcr_base - fcr_new) * gain' in l:
        print(f'feed_saved line: {i+1}')
    if 'wtp_per_head = cost_saved * 0.5' in l:
        print(f'wtp line: {i+1}')
    if 'additive_per_head = feed_per_head' in l:
        print(f'additive line: {i+1}')
