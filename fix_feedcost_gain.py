content = open('local/formula_advisor.py', encoding='utf-8').read()

old = '''def get_feed_cost(conn, region='CN_northeast'):
    soy = conn.execute("""
        SELECT value FROM market_kpi
        WHERE kpi_id LIKE '%soybean_meal%'
          AND (region=? OR region='CN_all')
        ORDER BY year DESC LIMIT 1
    """, (region,)).fetchone()
    corn = conn.execute("""
        SELECT value FROM market_kpi
        WHERE kpi_id LIKE '%corn%'
          AND (region=? OR region='CN_all')
        ORDER BY year DESC LIMIT 1
    """, (region,)).fetchone()
    soy_p  = soy[0]  if soy  else 3200
    corn_p = corn[0] if corn else 2150
    # 東北典型配方：玉米60%+豆粕20%+其他20%
    return round((corn_p*0.60 + soy_p*0.20 + 2800*0.20)/1000, 3)'''

new = '''def get_feed_cost(conn, region='CN_northeast'):
    # 查飼料總成本（元/噸），優先查配合飼料基準
    feed = conn.execute("""
        SELECT value FROM market_kpi
        WHERE kpi_id='feed_cost_northeast_baseline'
          OR kpi_id LIKE '%compound_feed%'
        ORDER BY credibility DESC, year DESC LIMIT 1
    """).fetchone()
    if feed and feed[0] > 100:  # 合理範圍元/噸
        return round(feed[0]/1000, 3)
    # fallback: 從原料計算，DB存的是元/kg
    soy = conn.execute("""
        SELECT value FROM market_kpi
        WHERE kpi_id LIKE '%soybean_meal%' AND unit LIKE '%kg%'
          AND (region=? OR region='CN_all') AND value BETWEEN 2 AND 6
        ORDER BY year DESC LIMIT 1
    """, (region,)).fetchone()
    corn = conn.execute("""
        SELECT value FROM market_kpi
        WHERE kpi_id LIKE '%corn%' AND unit LIKE '%kg%'
          AND (region=? OR region='CN_all') AND value BETWEEN 1 AND 4
        ORDER BY year DESC LIMIT 1
    """, (region,)).fetchone()
    soy_p  = soy[0]  if soy  else 3.01   # 元/kg
    corn_p = corn[0] if corn else 2.22   # 元/kg
    # 東北典型配方：玉米60%+豆粕20%+其他20%×2.8元/kg
    return round(corn_p*0.60 + soy_p*0.20 + 2.8*0.20, 3)'''

if old in content:
    content = content.replace(old, new)
    # 同時修gain計算：肉牛增重應用實際數據
    old2 = "        gain        = body_weight - 60  # 默認60kg開始"
    new2 = """        # 各物種標準增重（出欄重-入場重）
        gain_map = {
            'finisher_pig': 80,    # 80-160kg
            'beef_cattle':  300,   # 架子牛350kg→出欄650kg
            'meat_sheep':   45,    # 斷奶25kg→出欄70kg
            'broiler':      2.5,   # 全程2.5kg
            'layer_chicken':1.5,   # 產蛋期體重維持，用年產蛋量kg
            'duck':         3.0,   # 出欄3kg
            'breeding_sow': 66,    # 25天斷奶窩總增重
        }
        gain = gain_map.get(species, body_weight - 60)"""
    content = content.replace(old2, new2)
    open('local/formula_advisor.py', 'w', encoding='utf-8').write(content)
    print('done')
else:
    print('ERROR: string not found')
