lines = open('local/formula_advisor.py', encoding='utf-8').readlines()
# 254行（0-indexed 253）改layer_chicken的gain
lines[253] = "            'layer_chicken':18.0,  # 年產蛋量18kg（500天産蛋18-20kg/只均值）\n"
open('local/formula_advisor.py', 'w', encoding='utf-8').writelines(lines)
print('done')
