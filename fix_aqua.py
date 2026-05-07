content = open('local/pricing_matrix_v2.py', encoding='utf-8').read()

old = '''    elif calc_type == 'aqua':
        mkt_row  = get_price(conn, species, 'CN_south')
        mkt_p    = mkt_row[0] if mkt_row else 50.0
        fcr_row  = get_kpi(conn, species, 'fcr', 'CN_south')
        fcr_base = fcr_row[0] if fcr_row else 1.4
        fcr_new  = fcr_base * (1 - sp['fcr_improve_pct']/100)
        gain_kg  = sp['gain_kg']
        feed_saved = (fcr_base - fcr_new) * gain_kg
        cost_saved = feed_saved * feed_cost
        price_gain = mkt_p * gain_kg * sp.get('survival_improve',0)/100/10
        saving_per_head = cost_saved + price_gain
        feed_per_head   = fcr_new * gain_kg
        units_per_ton   = 1000 / (feed_per_head * dosage * 1000)
        saving_per_ton  = saving_per_head * units_per_ton
        wtp_mid  = saving_per_ton * 0.5
        wtp_low  = wtp_mid * 0.8
        wtp_high = wtp_mid * 1.2'''

new = '''    elif calc_type == 'aqua':
        mkt_row  = get_price(conn, species, 'CN_south')
        mkt_p    = mkt_row[0] if mkt_row else 50.0
        fcr_row  = get_kpi(conn, species, 'fcr', 'CN_south')
        fcr_base = fcr_row[0] if fcr_row else 1.4
        fcr_new  = fcr_base * (1 - sp['fcr_improve_pct']/100)
        # 每噸飼料可養出的水產kg數
        output_per_ton = 1000 / fcr_base
        output_new     = 1000 / fcr_new
        # FCR改善：同樣飼料多產出的水產
        extra_output   = output_new - output_per_ton
        saving_per_ton = extra_output * mkt_p
        # 存活率提升額外收益
        survival_gain  = output_per_ton * mkt_p * sp.get('survival_improve',0)/100
        saving_per_ton += survival_gain
        wtp_mid  = saving_per_ton * 0.5
        wtp_low  = wtp_mid * 0.8
        wtp_high = wtp_mid * 1.2'''

open('local/pricing_matrix_v2.py', 'w', encoding='utf-8').write(content.replace(old, new))
print('done')
