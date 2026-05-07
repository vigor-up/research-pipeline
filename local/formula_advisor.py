# -*- coding: utf-8 -*-
"""
formula_advisor.py
配方師問答系統 - 東北出差專用
回答三層問題：效果 → 配方用量 → ROI反推報價
Telegram: /formula 物種 產品
"""

import sqlite3, json, requests, argparse, sys
from datetime import datetime

DB_PATH        = r'D:\LLM\knowledge\market\market_data.db'
QWEN_URL       = 'http://localhost:1234/v1/chat/completions'
QWEN_MODEL     = 'qwen3.6-35b'
TELEGRAM_TOKEN = '8703702788:AAFKEiGmLYTAuFVG9GX-gRtVTUUyi-f_5mM'
TELEGRAM_CHAT  = 897274134

# ══════════════════════════════════════════════════════
# 產品資料庫（保密，不對外顯示）
# ══════════════════════════════════════════════════════
PRODUCTS = {
    'octacosanol': {
        'name': '二十八烷醇（Octacosanol）',
        'mechanism': '促進粒線體能量代謝，提升ATP產生效率，改善肌肉收縮效率',
        'effects': {
            'finisher_pig':    {'fcr_improve': 5.0,  'adg_improve': 8.0,  'unit': '%'},
            'beef_cattle':     {'fcr_improve': 6.0,  'adg_improve': 10.0, 'unit': '%'},
            'meat_sheep':      {'fcr_improve': 5.0,  'adg_improve': 8.0,  'unit': '%'},
            'layer_chicken':   {'egg_rate_improve': 3.0, 'fcr_improve': 4.0, 'unit': '%'},
            'broiler':         {'fcr_improve': 5.0,  'adg_improve': 7.0,  'unit': '%'},
            'lactating_sow':   {'litter_size_improve': 0.3, 'piglet_wt_improve': 5.0, 'unit': 'absolute/pct'},
        },
        'dosage': {  # g/噸飼料
            'finisher_pig':  {'low': 200, 'mid': 300, 'high': 400},
            'beef_cattle':   {'low': 300, 'mid': 400, 'high': 500},
            'meat_sheep':    {'low': 200, 'mid': 300, 'high': 400},
            'layer_chicken': {'low': 150, 'mid': 250, 'high': 350},
            'broiler':       {'low': 200, 'mid': 300, 'high': 400},
            'lactating_sow': {'low': 300, 'mid': 400, 'high': 500},
        },
        'market_price_range': (800, 1500),  # CNY/kg（市場接受範圍）
        'key_evidence': [
            'Chen et al. 2021 Animal Feed Science: FCR改善5.2%（育肥豬）',
            'Li et al. 2022 Poultry Science: 蛋雞產蛋率+2.8%',
            'Wang et al. 2023 Livestock Science: 肉牛ADG+9.3%',
        ]
    },
    'astaxanthin': {
        'name': '蝦青素（Astaxanthin）',
        'mechanism': '超強抗氧化（是VE的550倍），抗炎，免疫調節，改善繁殖性能',
        'effects': {
            'layer_chicken':   {'egg_yolk_color': '+3 Roche units', 'hatchability': 3.0,
                                'mortality_reduce': 2.0, 'unit': 'pct/absolute'},
            'broiler':         {'mortality_reduce': 1.5, 'fcr_improve': 3.0, 'unit': '%'},
            'finisher_pig':    {'mortality_reduce': 1.0, 'adg_improve': 4.0, 'unit': '%'},
            'lactating_sow':   {'piglet_survival_improve': 3.0, 'unit': '%'},
            'beef_cattle':     {'mortality_reduce': 1.0, 'adg_improve': 3.0, 'unit': '%'},
        },
        'dosage': {
            'layer_chicken': {'low': 20, 'mid': 40, 'high': 60},
            'broiler':       {'low': 20, 'mid': 40, 'high': 60},
            'finisher_pig':  {'low': 30, 'mid': 50, 'high': 80},
            'lactating_sow': {'low': 40, 'mid': 60, 'high': 80},
            'beef_cattle':   {'low': 30, 'mid': 50, 'high': 80},
        },
        'market_price_range': (3000, 8000),
        'key_evidence': [
            'DSM Carophyll Red: 蛋黃色澤+3 Roche, 孵化率+2.5%',
            'Naito et al. 2020: 抗氧化能力是VE的550倍',
            'Liu et al. 2022 Poultry Science: 蛋雞存活率+1.8%',
        ]
    },
    'bacillus_protease': {
        'name': '枯草菌源蛋白酶（Bacillus Protease）',
        'mechanism': '分解植物性抗營養因子，提升蛋白消化率，改善腸道健康',
        'effects': {
            'finisher_pig':    {'fcr_improve': 4.0, 'adg_improve': 5.0,
                                'protein_digestibility': 8.0, 'unit': '%'},
            'broiler':         {'fcr_improve': 5.0, 'adg_improve': 6.0,
                                'protein_digestibility': 10.0, 'unit': '%'},
            'layer_chicken':   {'fcr_improve': 4.0, 'egg_rate_improve': 2.0, 'unit': '%'},
            'beef_cattle':     {'fcr_improve': 3.0, 'adg_improve': 4.0, 'unit': '%'},
            'meat_sheep':      {'fcr_improve': 3.0, 'adg_improve': 4.0, 'unit': '%'},
            'lactating_sow':   {'piglet_adg_improve': 6.0, 'unit': '%'},
        },
        'dosage': {
            'finisher_pig':  {'low': 50, 'mid': 100, 'high': 150},
            'broiler':       {'low': 50, 'mid': 100, 'high': 150},
            'layer_chicken': {'low': 50, 'mid': 100, 'high': 150},
            'beef_cattle':   {'low': 80, 'mid': 150, 'high': 200},
            'meat_sheep':    {'low': 50, 'mid': 100, 'high': 150},
            'lactating_sow': {'low': 80, 'mid': 150, 'high': 200},
        },
        'market_price_range': (200, 600),
        'key_evidence': [
            '活力得® 枯草菌源蛋白酶：蛋白消化率+8-12%',
            'Bedford & Partridge 2020: 蛋白酶FCR改善4-6%',
            '腸道健康改善，壞死性腸炎發病率-30%',
        ]
    }
}

# ══════════════════════════════════════════════════════
# DB 查詢
# ══════════════════════════════════════════════════════
def get_baseline(conn, species, kpi, region='CN_northeast'):
    row = conn.execute("""
        SELECT value, value_min, value_max, unit, source_title
        FROM market_kpi
        WHERE species=? AND kpi_id LIKE ? AND region=?
          AND value IS NOT NULL
        ORDER BY credibility DESC, year DESC LIMIT 1
    """, (species, f'%{kpi}%', region)).fetchone()
    if not row:
        row = conn.execute("""
            SELECT value, value_min, value_max, unit, source_title
            FROM market_kpi
            WHERE species=? AND kpi_id LIKE ?
              AND value IS NOT NULL
            ORDER BY credibility DESC, year DESC LIMIT 1
        """, (species, f'%{kpi}%')).fetchone()
    return row

def get_price(conn, species, region='CN_northeast'):
    row = conn.execute("""
        SELECT value, unit, source_title
        FROM market_kpi
        WHERE species=? AND kpi_id LIKE '%spot_price%'
          AND (region=? OR region='CN_all')
          AND value IS NOT NULL
        ORDER BY year DESC, credibility DESC LIMIT 1
    """, (species, region)).fetchone()
    return row

def get_feed_cost(conn, region='CN_northeast'):
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
    return round((corn_p*0.60 + soy_p*0.20 + 2800*0.20)/1000, 3)

# ══════════════════════════════════════════════════════
# 核心計算：效果→配方→ROI→反推報價
# ══════════════════════════════════════════════════════
def calculate(species, product_key, region='CN_northeast',
              scale=1000, body_weight=115):
    conn   = sqlite3.connect(DB_PATH)
    prod   = PRODUCTS.get(product_key)
    if not prod:
        return {'error': f'產品 {product_key} 不存在'}

    effects   = prod['effects'].get(species, {})
    dosage    = prod['dosage'].get(species, {'low':100,'mid':200,'high':300})
    mkt_price = prod['market_price_range']

    # 基準數據
    fcr_row    = get_baseline(conn, species, 'fcr', region)
    adg_row    = get_baseline(conn, species, 'adg', region)
    mort_row   = get_baseline(conn, species, 'mortality', region)
    price_row  = get_price(conn, species, region)
    feed_cost  = get_feed_cost(conn, region)
    conn.close()

    fcr_base  = fcr_row[0]  if fcr_row  else None
    adg_base  = adg_row[0]  if adg_row  else None
    mort_base = mort_row[0] if mort_row else None
    mkt_p     = price_row[0] if price_row else None

    # FCR 節省計算
    fcr_improve_pct = effects.get('fcr_improve', 0)
    adg_improve_pct = effects.get('adg_improve', 0)

    results = {
        'product':  prod['name'],
        'species':  species,
        'region':   region,
        'mechanism': prod['mechanism'],
    }

    # 數據來源標注
    results['data_sources'] = {
        'FCR基準':  f"{fcr_base}（{fcr_row[4] if fcr_row else '估算'}）" if fcr_base else '無數據',
        'ADG基準':  f"{adg_base}g/day（{adg_row[4] if adg_row else '估算'}）" if adg_base else '無數據',
        '市場價格': f"CNY {mkt_p}/kg（{price_row[2] if price_row else '估算'}）" if mkt_p else '無數據',
        '飼料成本': f"CNY {feed_cost}/kg（東北玉米+豆粕加權）",
    }

    # 配方建議
    results['formula'] = {
        '建議用量': f"{dosage['mid']} g/噸飼料",
        '用量範圍': f"{dosage['low']}-{dosage['high']} g/噸",
        '每噸飼料添加劑成本（市場中間價）':
            f"CNY {dosage['mid']/1000 * sum(mkt_price)/2:.1f}/噸",
    }

    # ROI計算
    roi = {}
    if fcr_base and fcr_improve_pct and feed_cost:
        fcr_new     = fcr_base * (1 - fcr_improve_pct/100)
        gain        = body_weight - 60  # 默認60kg開始
        feed_saved  = (fcr_base - fcr_new) * gain
        cost_saved  = feed_saved * feed_cost

        # 添加劑成本/頭
        feed_per_head    = fcr_new * gain
        additive_per_ton = dosage['mid'] / 1000  # kg/噸
        additive_per_head = feed_per_head * additive_per_ton  # kg/頭

        roi['FCR改善'] = f"{fcr_base} → {fcr_new:.2f}（{fcr_improve_pct}%）"
        roi['每頭節省飼料成本'] = f"CNY {cost_saved:.1f}"
        roi[f'{scale}頭規模節省'] = f"CNY {cost_saved*scale:,.0f}"

        # 反推客戶願付價格
        wtp_per_head = cost_saved * 0.5  # 50%分潤
        if additive_per_head > 0:
            wtp_kg = wtp_per_head / additive_per_head
            roi['客戶願付（50%分潤）'] = f"CNY {wtp_kg:,.0f}/kg"
            roi['建議報價區間'] = f"CNY {wtp_kg*0.4:,.0f} ~ {wtp_kg*0.6:,.0f}/kg"
            roi['市場接受範圍'] = f"CNY {mkt_price[0]:,} ~ {mkt_price[1]:,}/kg"

            # 判斷定價空間
            mid_wtp = wtp_kg * 0.5
            if mkt_price[0] <= mid_wtp <= mkt_price[1]:
                roi['定價結論'] = f"✅ 報價在市場接受範圍內，建議定價 CNY {mid_wtp:,.0f}/kg"
            elif mid_wtp > mkt_price[1]:
                roi['定價結論'] = f"⚠️ 理論報價超出市場上限，強調差異化價值或調整用量"
            else:
                roi['定價結論'] = f"💪 報價低於市場下限，有提價空間至 CNY {mkt_price[0]:,}/kg"

    results['roi'] = roi
    results['evidence'] = prod['key_evidence']
    results['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M')

    return results

def format_output(result, mode='telegram'):
    if 'error' in result:
        return f"❌ {result['error']}"

    lines = [
        f"🧪 <b>{result['product']}</b>",
        f"物種：{result['species']} | 區域：{result['region']}",
        f"",
        f"⚙️ <b>作用機制</b>",
        f"{result['mechanism']}",
        f"",
        f"📌 <b>數據基準</b>",
    ]
    for k, v in result['data_sources'].items():
        lines.append(f"  {k}: {v}")

    lines += ["", "🔬 <b>配方建議</b>"]
    for k, v in result['formula'].items():
        lines.append(f"  {k}: {v}")

    if result['roi']:
        lines += ["", "💰 <b>ROI & 反推報價</b>"]
        for k, v in result['roi'].items():
            lines.append(f"  {k}: {v}")

    lines += ["", "📚 <b>關鍵文獻</b>"]
    for e in result['evidence'][:3]:
        lines.append(f"  • {e}")

    lines.append(f"\n⏱ {result['timestamp']} | 東北區域數據")
    return '\n'.join(lines)

def tg(msg):
    try:
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id':TELEGRAM_CHAT,'text':msg,'parse_mode':'HTML'},
            timeout=10)
    except Exception as e:
        print(f'TG error: {e}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--species',  required=True,
        help='finisher_pig|beef_cattle|layer_chicken|broiler|meat_sheep|lactating_sow')
    parser.add_argument('--product',  required=True,
        help='octacosanol|astaxanthin|bacillus_protease')
    parser.add_argument('--region',   default='CN_northeast')
    parser.add_argument('--scale',    type=int, default=1000)
    parser.add_argument('--weight',   type=float, default=115)
    parser.add_argument('--telegram', action='store_true')
    args = parser.parse_args()

    result = calculate(args.species, args.product,
                       args.region, args.scale, args.weight)
    output = format_output(result)
    print(output)
    if args.telegram:
        tg(output)
