lines = open('local/pricing_matrix_v2.py', encoding='utf-8').readlines()
# 318-334行（0-indexed 317-333）替換aqua計算邏輯
new_lines = [
    '    elif calc_type == \'aqua\':\n',
    '        mkt_row  = get_price(conn, species, \'CN_south\')\n',
    '        mkt_p    = mkt_row[0] if mkt_row else 50.0\n',
    '        fcr_row  = get_kpi(conn, species, \'fcr\', \'CN_south\')\n',
    '        fcr_base = fcr_row[0] if fcr_row else 1.4\n',
    '        fcr_new  = fcr_base * (1 - sp[\'fcr_improve_pct\']/100)\n',
    '        # 每噸飼料產出水產kg數\n',
    '        output_base    = 1000 / fcr_base\n',
    '        output_new     = 1000 / fcr_new\n',
    '        extra_output   = output_new - output_base\n',
    '        saving_per_ton = extra_output * mkt_p\n',
    '        survival_gain  = output_base * mkt_p * sp.get(\'survival_improve\',0)/100\n',
    '        saving_per_ton += survival_gain\n',
    '        wtp_mid  = saving_per_ton * 0.5\n',
    '        wtp_low  = wtp_mid * 0.8\n',
    '        wtp_high = wtp_mid * 1.2\n',
    '        gain_kg  = sp[\'gain_kg\']\n',
]
lines[317:334] = new_lines
open('local/pricing_matrix_v2.py', 'w', encoding='utf-8').writelines(lines)
print('done, lines now:', len(lines))
