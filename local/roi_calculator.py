# -*- coding: utf-8 -*-
"""
roi_calculator.py
ROI 計算器 - 從 DB 拉實時數據計算客戶願付價格
支援：育肥豬 / 蛋雞 / 肉雞 / 乳牛 / 肉牛 / 蝦 / 魚
呼叫方式：
  python roi_calculator.py --species finisher_pig --improvement fcr:25
  python roi_calculator.py --species layer_chicken --improvement peak_extension:14
"""

import sqlite3, json, argparse, sys
from datetime import datetime

DB_PATH = r'D:\LLM\knowledge\market\market_data.db'

# ── DB 查詢工具 ────────────────────────────────────────
def get_kpi(conn, species, kpi_pattern, region='CN_all'):
    """從DB取最新最高可信度的KPI值"""
    rows = conn.execute("""
        SELECT value, value_min, value_max, unit, year, credibility, source_title
        FROM market_kpi
        WHERE species=? AND kpi_id LIKE ? AND region=?
          AND value IS NOT NULL
        ORDER BY credibility DESC, year DESC
        LIMIT 1
    """, (species, f'%{kpi_pattern}%', region)).fetchone()
    if not rows:
        # fallback: 不限區域
        rows = conn.execute("""
            SELECT value, value_min, value_max, unit, year, credibility, source_title
            FROM market_kpi
            WHERE species=? AND kpi_id LIKE ?
              AND value IS NOT NULL
            ORDER BY credibility DESC, year DESC
            LIMIT 1
        """, (species, f'%{kpi_pattern}%')).fetchone()
    return rows

def get_price(conn, species, price_type='spot_price'):
    """取最新現貨價格"""
    rows = conn.execute("""
        SELECT value, unit, year, source_title
        FROM market_kpi
        WHERE species=? AND kpi_id LIKE ?
          AND value IS NOT NULL
        ORDER BY year DESC, credibility DESC
        LIMIT 1
    """, (species, f'%{price_type}%')).fetchone()
    return rows

def get_feed_cost(conn):
    """取飼料成本（豆粕+玉米加權）"""
    soy = conn.execute("""
        SELECT value FROM market_kpi
        WHERE kpi_id LIKE '%soybean_meal%' AND value IS NOT NULL
        ORDER BY year DESC LIMIT 1""").fetchone()
    corn = conn.execute("""
        SELECT value FROM market_kpi
        WHERE kpi_id LIKE '%corn%' AND value IS NOT NULL
        ORDER BY year DESC LIMIT 1""").fetchone()
    # 典型配方：豆粕20% + 玉米65% + 其他15%
    soy_price  = soy[0] if soy else 3500   # CNY/ton fallback
    corn_price = corn[0] if corn else 2400
    feed_cost_per_ton = soy_price * 0.20 + corn_price * 0.65 + 2800 * 0.15
    return feed_cost_per_ton / 1000  # CNY/kg

# ── 物種計算模組 ───────────────────────────────────────

def calc_finisher_pig(conn, params):
    """
    育肥豬 ROI
    params: fcr_improvement(%), body_weight(kg), price_override(CNY/kg)
    """
    fcr_improve_pct = float(params.get('fcr_improvement', 25))
    body_weight     = float(params.get('body_weight', 115))  # 出欄體重
    start_weight    = float(params.get('start_weight', 60))
    gain            = body_weight - start_weight

    # 從DB取數據
    fcr_row   = get_kpi(conn, 'finisher_pig', 'fcr')
    price_row = get_price(conn, 'finisher_pig', 'spot_price')
    feed_cost = get_feed_cost(conn)

    fcr_base  = fcr_row[0] if fcr_row else 2.6
    fcr_min   = fcr_row[1] if fcr_row and fcr_row[1] else 2.4
    fcr_max   = fcr_row[2] if fcr_row and fcr_row[2] else 2.8

    # 豬肉價格
    if price_row:
        pig_price = price_row[0]  # CNY/kg
    else:
        pig_price = float(params.get('price_override', 10.0))

    # 計算
    fcr_improved     = fcr_base * (1 - fcr_improve_pct/100)
    feed_saved_kg    = (fcr_base - fcr_improved) * gain      # kg/頭
    feed_cost_saved  = feed_saved_kg * feed_cost              # CNY/頭
    revenue_gain     = feed_cost_saved  # FCR改善=飼料節省

    # 客戶願付（每0.1 FCR改善 30-40 CNY/kg添加劑）
    fcr_drop         = fcr_base - fcr_improved
    units_of_01      = fcr_drop / 0.1
    wtp_low          = units_of_01 * 30   # CNY/kg添加劑（低估）
    wtp_high         = units_of_01 * 40   # CNY/kg添加劑（高估）

    # 添加劑用量假設 0.5kg/噸飼料
    additive_per_pig = fcr_improved * gain * 0.0005  # kg/頭

    return {
        'species': '育肥豬',
        'scenario': f'{start_weight}-{body_weight}kg（{gain}kg增重）',
        'data_sources': {
            'FCR基準': f'{fcr_base}（{fcr_min}-{fcr_max}）來源: {fcr_row[6] if fcr_row else "估算"}',
            '豬肉價格': f'CNY {pig_price}/kg 來源: {price_row[3] if price_row else "估算"}',
            '飼料成本': f'CNY {feed_cost:.2f}/kg（豆粕+玉米加權）',
        },
        'calculation': {
            'FCR改善': f'{fcr_base} → {fcr_improved:.2f}（{fcr_improve_pct}%）',
            '每頭節省飼料': f'{feed_saved_kg:.1f} kg',
            '每頭節省成本': f'CNY {feed_cost_saved:.1f}',
            '每頭添加劑用量': f'{additive_per_pig*1000:.1f}g',
        },
        'wtp': {
            '客戶願付低': f'CNY {wtp_low:.0f}/kg 添加劑',
            '客戶願付高': f'CNY {wtp_high:.0f}/kg 添加劑',
            '建議報價區間': f'CNY {wtp_low*0.6:.0f} ~ {wtp_high*0.7:.0f}/kg',
            '每頭ROI（客戶）': f'CNY {feed_cost_saved:.1f}/頭',
        },
        'scale_roi': {
            '1000頭/批': f'CNY {feed_cost_saved*1000:,.0f}/批',
            '10000頭/批': f'CNY {feed_cost_saved*10000:,.0f}/批',
        }
    }

def calc_layer_chicken(conn, params):
    """
    蛋雞 ROI
    params: peak_extension_days(天), flock_size(隻), age(天), price_override
    """
    ext_days    = float(params.get('peak_extension_days', 14))
    flock_size  = float(params.get('flock_size', 10000))
    age         = int(params.get('age', 500))

    # 從DB取數據
    egg_rate_row  = get_kpi(conn, 'layer_chicken', 'egg_rate')
    price_row     = get_price(conn, 'layer_chicken', 'spot_price_egg')
    feed_cost     = get_feed_cost(conn)

    egg_rate  = (egg_rate_row[0]/100) if egg_rate_row else 0.92
    egg_price = price_row[0] if price_row else 8.0  # CNY/kg

    # 蛋雞參數
    egg_weight_g    = 63      # g/顆
    daily_feed_g    = 115     # g/隻/天
    daily_egg_kg    = egg_weight_g * egg_rate / 1000  # kg/隻/天

    # 計算
    extra_egg_kg     = daily_egg_kg * ext_days          # kg/隻
    extra_revenue    = extra_egg_kg * egg_price          # CNY/隻
    extra_feed_cost  = (daily_feed_g/1000) * ext_days * feed_cost
    net_gain_per_hen = extra_revenue - extra_feed_cost

    # 添加劑用量假設 0.3kg/噸飼料
    additive_per_hen = (daily_feed_g/1000) * ext_days * 0.0003  # kg/隻

    wtp_per_hen  = net_gain_per_hen * 0.5   # 客戶願付淨增收50%
    wtp_per_kg   = wtp_per_hen / additive_per_hen if additive_per_hen > 0 else 0

    return {
        'species': '蛋雞',
        'scenario': f'{age}日齡，延長產蛋峰值 {ext_days} 天',
        'data_sources': {
            '產蛋率': f'{egg_rate*100:.1f}% 來源: {egg_rate_row[6] if egg_rate_row else "估算"}',
            '雞蛋價格': f'CNY {egg_price}/kg 來源: {price_row[3] if price_row else "估算"}',
            '飼料成本': f'CNY {feed_cost:.2f}/kg',
        },
        'calculation': {
            '每日產蛋': f'{daily_egg_kg*1000:.1f}g/隻',
            f'延長{ext_days}天額外產蛋': f'{extra_egg_kg*1000:.1f}g/隻',
            '額外蛋收入/隻': f'CNY {extra_revenue:.2f}',
            '額外飼料成本/隻': f'CNY {extra_feed_cost:.2f}',
            '淨增收/隻': f'CNY {net_gain_per_hen:.2f}',
        },
        'wtp': {
            '客戶願付（50%分潤）': f'CNY {wtp_per_hen:.2f}/隻',
            '換算添加劑價格': f'CNY {wtp_per_kg:,.0f}/kg',
            '建議報價區間': f'CNY {wtp_per_kg*0.4:,.0f} ~ {wtp_per_kg*0.6:,.0f}/kg',
        },
        'scale_roi': {
            f'{int(flock_size):,}隻雞場': f'CNY {net_gain_per_hen*flock_size:,.0f}',
            '10萬隻雞場': f'CNY {net_gain_per_hen*100000:,.0f}',
        }
    }

def calc_broiler(conn, params):
    """肉雞 ROI"""
    fcr_improve_pct = float(params.get('fcr_improvement', 10))
    body_weight     = float(params.get('body_weight', 2.5))
    start_weight    = 0.04

    fcr_row   = get_kpi(conn, 'broiler', 'fcr')
    price_row = get_price(conn, 'broiler', 'spot_price')
    feed_cost = get_feed_cost(conn)

    fcr_base  = fcr_row[0] if fcr_row else 1.75
    gain      = body_weight - start_weight
    fcr_impr  = fcr_base * (1 - fcr_improve_pct/100)
    feed_saved = (fcr_base - fcr_impr) * gain
    cost_saved = feed_saved * feed_cost

    chicken_price = price_row[0] if price_row else 14.0
    additive_per_bird = fcr_impr * gain * 0.0005

    wtp_low  = cost_saved / additive_per_bird * 0.4 if additive_per_bird else 0
    wtp_high = cost_saved / additive_per_bird * 0.6 if additive_per_bird else 0

    return {
        'species': '肉雞',
        'scenario': f'出欄 {body_weight}kg，FCR改善 {fcr_improve_pct}%',
        'data_sources': {
            'FCR基準': f'{fcr_base} 來源: {fcr_row[6] if fcr_row else "估算"}',
            '肉雞價格': f'CNY {chicken_price}/kg',
            '飼料成本': f'CNY {feed_cost:.2f}/kg',
        },
        'calculation': {
            'FCR改善': f'{fcr_base} → {fcr_impr:.2f}',
            '每隻節省飼料': f'{feed_saved*1000:.1f}g',
            '每隻節省成本': f'CNY {cost_saved:.2f}',
        },
        'wtp': {
            '客戶願付區間': f'CNY {wtp_low:,.0f} ~ {wtp_high:,.0f}/kg 添加劑',
        },
        'scale_roi': {
            '10萬隻/批': f'CNY {cost_saved*100000:,.0f}',
        }
    }

def calc_shrimp(conn, params):
    """蝦 ROI"""
    survival_improve = float(params.get('survival_improvement', 10))  # %
    pond_area_mu     = float(params.get('pond_area', 10))  # 畝

    survival_row = get_kpi(conn, 'shrimp', 'survival')
    price_row    = get_price(conn, 'shrimp', 'spot_price')
    feed_cost    = get_feed_cost(conn)

    survival_base = (survival_row[0]/100) if survival_row else 0.80
    shrimp_price  = price_row[0] if price_row else 50.0  # CNY/kg
    density       = 60000  # 尾/畝
    harvest_wt_g  = 20     # g/尾

    extra_survive = density * pond_area_mu * (survival_improve/100)
    extra_kg      = extra_survive * harvest_wt_g / 1000
    extra_revenue = extra_kg * shrimp_price

    feed_per_mu   = 300    # kg/畝/季 估算
    additive_total = feed_per_mu * pond_area_mu * 0.0005

    net_gain = extra_revenue * 0.8
    wtp      = net_gain / additive_total if additive_total else 0

    return {
        'species': '白蝦',
        'scenario': f'{pond_area_mu}畝，存活率提升 {survival_improve}%',
        'data_sources': {
            '基準存活率': f'{survival_base*100:.0f}% 來源: {survival_row[6] if survival_row else "估算"}',
            '蝦現貨價': f'CNY {shrimp_price}/kg',
        },
        'calculation': {
            '額外存活尾數': f'{extra_survive:,.0f} 尾',
            '額外收穫': f'{extra_kg:.1f} kg',
            '額外收入': f'CNY {extra_revenue:,.0f}',
        },
        'wtp': {
            '客戶願付': f'CNY {wtp:,.0f}/kg 添加劑',
            '建議報價': f'CNY {wtp*0.4:,.0f} ~ {wtp*0.6:,.0f}/kg',
        }
    }

# ── 統一入口 ───────────────────────────────────────────
CALC_MAP = {
    'finisher_pig':    calc_finisher_pig,
    'layer_chicken':   calc_layer_chicken,
    'broiler':         calc_broiler,
    'shrimp':          calc_shrimp,
}

def calculate_roi(species, params, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    calc_fn = CALC_MAP.get(species)
    if not calc_fn:
        return {'error': f'物種 {species} 尚未支援，可用: {list(CALC_MAP.keys())}'}
    result = calc_fn(conn, params)
    conn.close()
    return result

def format_telegram(result):
    """格式化為 Telegram 友好訊息"""
    if 'error' in result:
        return f'❌ {result["error"]}'

    lines = [
        f'📊 <b>ROI 計算報告</b>',
        f'物種：{result["species"]}',
        f'場景：{result["scenario"]}',
        '',
        '📌 <b>數據來源</b>',
    ]
    for k, v in result.get('data_sources', {}).items():
        lines.append(f'  {k}: {v}')

    lines += ['', '🔢 <b>計算結果</b>']
    for k, v in result.get('calculation', {}).items():
        lines.append(f'  {k}: {v}')

    lines += ['', '💰 <b>客戶願付價格</b>']
    for k, v in result.get('wtp', {}).items():
        lines.append(f'  {k}: {v}')

    lines += ['', '📈 <b>規模效益</b>']
    for k, v in result.get('scale_roi', {}).items():
        lines.append(f'  {k}: {v}')

    lines += ['', f'⏱ {datetime.now().strftime("%Y-%m-%d %H:%M")} | 數據來自本機DB']
    return '\n'.join(lines)

# ── CLI / Telegram 呼叫入口 ────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ROI Calculator')
    parser.add_argument('--species', required=True,
        help='finisher_pig | layer_chicken | broiler | shrimp')
    parser.add_argument('--params', default='{}',
        help='JSON格式參數，例如 {"fcr_improvement":25,"body_weight":115}')
    parser.add_argument('--telegram', action='store_true',
        help='輸出Telegram格式')
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
    except Exception:
        params = {}

    result = calculate_roi(args.species, params)

    if args.telegram:
        print(format_telegram(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
