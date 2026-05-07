lines = open('local/formula_advisor.py', encoding='utf-8').readlines()

# 替換259-284行（0-indexed 258-283）為新的ROI計算邏輯
new_block = [
    '        feed_saved  = (fcr_base - fcr_new) * gain\n',
    '        cost_saved  = feed_saved * feed_cost\n',
    '        # 每噸飼料效益（主要計算基準）\n',
    '        if mkt_p and fcr_new > 0:\n',
    '            output_base  = 1000 / fcr_base\n',
    '            output_new   = 1000 / fcr_new\n',
    '            extra_output = output_new - output_base\n',
    '            saving_per_ton = extra_output * mkt_p\n',
    '        else:\n',
    '            saving_per_ton = 0\n',
    '        # 添加劑用量\n',
    '        feed_per_head     = fcr_new * gain\n',
    '        additive_per_ton  = dosage[\'mid\'] / 1000  # kg/噸飼料\n',
    '        additive_per_head = feed_per_head * dosage[\'mid\'] / 1_000_000  # kg/頭\n',
    '        roi[\'FCR改善\'] = f"{fcr_base} → {fcr_new:.2f}（{fcr_improve_pct}%）"\n',
    '        roi[\'每頭節省飼料成本\'] = f"CNY {cost_saved:.1f}"\n',
    '        roi[\'每噸飼料效益\'] = f"CNY {saving_per_ton:,.0f}/噸"\n',
    '        roi[f\'{scale}頭規模節省\'] = f"CNY {cost_saved*scale:,.0f}"\n',
    '        # 效益反推WTP（每噸飼料基準）\n',
    '        wtp_per_ton = saving_per_ton * 0.5\n',
    '        wtp_kg = wtp_per_ton / additive_per_ton if additive_per_ton > 0 else 0\n',
    '        wtp_per_head = cost_saved * 0.5\n',
    '        if additive_per_head > 0:\n',
    '            roi[\'客戶願付（50%分潤）\'] = f"CNY {wtp_kg:,.0f}/kg"\n',
    '            roi[\'建議報價區間\'] = f"CNY {wtp_kg*0.4:,.0f} ~ {wtp_kg*0.6:,.0f}/kg"\n',
    '            roi[\'市場接受範圍\'] = f"CNY {mkt_price[0]:,} ~ {mkt_price[1]:,}/kg"\n',
    '            mid_wtp = wtp_kg * 0.5\n',
    '            if mkt_price[0] <= mid_wtp <= mkt_price[1]:\n',
    '                roi[\'定價結論\'] = f"OK 報價在市場接受範圍內，建議定價 CNY {mid_wtp:,.0f}/kg"\n',
    '            elif mid_wtp > mkt_price[1]:\n',
    '                roi[\'定價結論\'] = f"WARN 理論報價超出市場上限，強調差異化價值或調整用量"\n',
]

# 找結束行（下一個elif或else在273行之後）
end_line = 284  # 0-indexed 283
lines[258:end_line] = new_block
open('local/formula_advisor.py', 'w', encoding='utf-8').writelines(lines)
print(f'done, total lines: {len(lines)}')
