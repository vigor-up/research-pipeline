content = open('local/formula_advisor.py', encoding='utf-8').read()

old = '''        feed_saved  = (fcr_base - fcr_new) * gain
        cost_saved  = feed_saved * feed_cost
        # 添加劑用量/頭
        # feed_per_head(kg) * dosage(g/噸) / 1_000_000 = 添加劑用量(kg/頭)
        # 例: 297kg feed * 1000g/噸 / 1_000_000 = 0.297kg = 297g
        feed_per_head     = fcr_new * gain
        additive_per_head = feed_per_head * dosage['mid'] / 1_000_000  # kg/頭'''

new = '''        # 計算方式：每噸飼料效益（適用所有物種）
        # 每噸飼料改善前產出 = 1000/FCR_base kg肉（或蛋）
        # 每噸飼料改善後產出 = 1000/FCR_new kg肉
        # 差值 × 市場價 = 每噸飼料效益
        if mkt_p and fcr_new > 0:
            output_base = 1000 / fcr_base   # kg/噸飼料
            output_new  = 1000 / fcr_new
            extra_output = output_new - output_base
            saving_per_ton = extra_output * mkt_p
        else:
            saving_per_ton = 0
        # 每頭效益（向後兼容）
        feed_per_head     = fcr_new * gain
        feed_saved        = (fcr_base - fcr_new) * gain
        cost_saved_head   = feed_saved * feed_cost
        # 用每噸效益作為主要計算基礎
        additive_per_ton  = dosage['mid'] / 1000  # kg/噸飼料
        additive_per_head = feed_per_head * dosage['mid'] / 1_000_000  # kg/頭
        # 每頭添加劑成本
        additive_cost_per_head = additive_per_head * sum(mkt_price)/2
        # WTP反推（效益反推，每噸飼料）
        wtp_per_ton = saving_per_ton * 0.5  # 50%分潤
        wtp_kg = wtp_per_ton / additive_per_ton if additive_per_ton > 0 else 0
        # cost_saved用每頭數字顯示
        cost_saved = cost_saved_head'''

if old in content:
    content = content.replace(old, new)
    # 同時修WTP顯示部分
    old2 = '''        wtp_per_head = cost_saved * 0.5  # 50%分潤
        if additive_per_head > 0:
            wtp_kg = wtp_per_head / additive_per_head  # CNY/kg（添加劑產品報價）
            roi['客戶願付（50%分潤）'] = f"CNY {wtp_kg:,.0f}/kg"'''
    new2 = '''        roi['每噸飼料效益'] = f"CNY {saving_per_ton:,.0f}/噸"
        roi['客戶願付（50%分潤）'] = f"CNY {wtp_kg:,.0f}/kg"'''
    content = content.replace(old2, new2)
    open('local/formula_advisor.py', 'w', encoding='utf-8').write(content)
    print('done')
else:
    print('ERROR: not found')
