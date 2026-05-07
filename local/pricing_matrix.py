# -*- coding: utf-8 -*-
"""
pricing_matrix.py
市場反推定價矩陣
產品：肥力寶（促生長）/ 活力旺（促繁殖）
規格：1kg/噸飼料
通路：出廠價 → 區域代理商 → 終端飼料廠
"""
import sqlite3, json, argparse, requests
from datetime import datetime

DB_PATH        = r'D:\LLM\knowledge\market\market_data.db'
TELEGRAM_TOKEN = '8703702788:AAFKEiGmLYTAuFVG9GX-gRtVTUUyi-f_5mM'
TELEGRAM_CHAT  = 897274134

# ══════════════════════════════════════════════════════
# 產品效果（田間數據，隱藏原料名稱）
# ══════════════════════════════════════════════════════
PRODUCTS = {
    'vitalboost_growth': {
        'display_name': '肥力寶',
        'target': '促生長',
        'species_effects': {
            'finisher_pig': {
                'fcr_improve': 8.0, 'adg_improve': 10.0,
                'mortality_reduce': 1.0,
                'gain_kg': 55,  # 典型增重kg/頭（60→115kg）
            },
            'beef_cattle': {
                'fcr_improve': 8.0, 'adg_improve': 12.0,
                'mortality_reduce': 0.8,
                'gain_kg': 150,  # 典型育肥增重
            },
            'meat_sheep': {
                'fcr_improve': 7.0, 'adg_improve': 10.0,
                'mortality_reduce': 1.0,
                'gain_kg': 25,
            },
            'broiler': {
                'fcr_improve': 6.0, 'adg_improve': 8.0,
                'mortality_reduce': 1.2,
                'gain_kg': 2.4,
            },
            'layer_chicken': {
                'fcr_improve': 5.0, 'egg_rate_improve': 3.0,
                'peak_extension_days': 14,
                'daily_feed_kg': 0.115,
            },
        },
        'dosage_g_per_ton': 1000,  # 固定1kg/噸
    },
    'vitalboost_repro': {
        'display_name': '活力旺',
        'target': '促繁殖',
        'species_effects': {
            'lactating_sow': {
                'litter_size_improve': 0.5,   # 窩產仔+0.5頭
                'piglet_survival_improve': 3.0, # 存活率+3%
                'weaning_weight_improve': 5.0,  # 斷奶重+5%
                'cycles_per_year': 2.3,
            },
            'breeding_sow': {
                'conception_rate_improve': 3.0,
                'litter_size_improve': 0.4,
                'cycles_per_year': 2.3,
            },
            'layer_chicken': {
                'hatchability_improve': 3.0,
                'egg_rate_improve': 2.0,
                'peak_extension_days': 21,
                'daily_feed_kg': 0.115,
            },
        },
        'dosage_g_per_ton': 1000,
    }
}

# 通路加價結構
CHANNEL = {
    'distributor_margin': 0.30,  # 代理商加價30%
    'dealer_margin':      0.25,  # 終端加價25%
    'target_gross_margin': 0.45, # 目標毛利45%
}

# ══════════════════════════════════════════════════════
# DB 查詢
# ══════════════════════════════════════════════════════
def get_kpi(conn, species, kpi, region='CN_northeast'):
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

def get_market_price(conn, species, region='CN_northeast'):
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
        SELECT value FROM market_kpi WHERE kpi_id LIKE '%soybean_meal%'
          AND (region=? OR region='CN_all')
        ORDER BY year DESC LIMIT 1""", (region,)).fetchone()
    corn = conn.execute("""
        SELECT value FROM market_kpi WHERE kpi_id LIKE '%corn%'
          AND (region=? OR region='CN_all')
        ORDER BY year DESC LIMIT 1""", (region,)).fetchone()
    soy_p  = soy[0]  if soy  else 3200
    corn_p = corn[0] if corn else 2150
    return round((corn_p*0.60 + soy_p*0.20 + 2800*0.20)/1000, 3)

# ══════════════════════════════════════════════════════
# 核心計算：市場反推定價
# ══════════════════════════════════════════════════════
def calc_growth(conn, species, prod, region):
    """促生長產品ROI計算"""
    eff       = prod['species_effects'][species]
    feed_cost = get_feed_cost(conn, region)

    fcr_row   = get_kpi(conn, species, 'fcr', region)
    mkt_row   = get_market_price(conn, species, region)

    fcr_base  = fcr_row[0] if fcr_row else None
    mkt_price = mkt_row[0] if mkt_row else None

    if not fcr_base or not feed_cost:
        return None

    gain_kg       = eff.get('gain_kg', 50)
    fcr_improve   = eff.get('fcr_improve', 5.0)
    adg_improve   = eff.get('adg_improve', 8.0)
    mort_reduce   = eff.get('mortality_reduce', 1.0)

    # FCR節省
    fcr_new       = fcr_base * (1 - fcr_improve/100)
    feed_saved_kg = (fcr_base - fcr_new) * gain_kg
    fcr_saving    = feed_saved_kg * feed_cost

    # 死亡率節省（市場價×死亡率改善×均重）
    mort_saving = 0
    if mkt_price:
        mort_saving = mkt_price * gain_kg * (mort_reduce/100)

    total_saving_per_head = fcr_saving + mort_saving

    # 添加劑用量/頭（1kg/噸飼料）
    feed_consumed   = fcr_new * gain_kg          # kg飼料/頭
    additive_per_head = feed_consumed / 1000      # kg添加劑/頭 (1kg/ton)
    additive_per_ton  = 1.0                       # kg/噸（固定規格）

    # 客戶願付（以每噸飼料計）
    # 每噸飼料帶動的增重 = 1000/fcr_new
    heads_per_ton   = 1000 / (fcr_new * gain_kg) if gain_kg > 0 else 10
    saving_per_ton_feed = total_saving_per_head * heads_per_ton

    # 客戶願付價格（per kg產品 = per ton飼料，因為1kg/ton）
    wtp_50pct = saving_per_ton_feed * 0.50   # 50%分潤
    wtp_40pct = saving_per_ton_feed * 0.40
    wtp_60pct = saving_per_ton_feed * 0.60

    return {
        'fcr_base':           fcr_base,
        'fcr_improved':       round(fcr_new, 2),
        'fcr_improve_pct':    fcr_improve,
        'feed_cost':          feed_cost,
        'feed_saved_per_head': round(feed_saved_kg, 1),
        'fcr_saving_per_head': round(fcr_saving, 1),
        'mort_saving_per_head': round(mort_saving, 1),
        'total_saving_per_head': round(total_saving_per_head, 1),
        'saving_per_ton_feed': round(saving_per_ton_feed, 1),
        'wtp_low':   round(wtp_40pct),
        'wtp_mid':   round(wtp_50pct),
        'wtp_high':  round(wtp_60pct),
    }

def calc_repro(conn, species, prod, region):
    """促繁殖產品ROI計算"""
    eff       = prod['species_effects'].get(species, {})
    feed_cost = get_feed_cost(conn, region)

    if species == 'lactating_sow':
        piglet_row = get_kpi(conn, 'nursery_pig', 'piglet_price', region)
        piglet_price = piglet_row[0] if piglet_row else 280  # CNY/頭

        litter_improve    = eff.get('litter_size_improve', 0.5)
        survival_improve  = eff.get('piglet_survival_improve', 3.0)
        cycles            = eff.get('cycles_per_year', 2.3)

        # 每頭母豬/年額外收益
        extra_piglets_per_litter = litter_improve
        extra_from_survival = 11.0 * (survival_improve/100)  # 基準11頭
        total_extra_per_litter = extra_piglets_per_litter + extra_from_survival
        extra_per_year = total_extra_per_litter * cycles

        revenue_per_year = extra_per_year * piglet_price

        # 添加劑成本/母豬/年
        daily_feed   = 3.5  # kg/天（哺乳期）
        lactation_days = 28 * cycles
        feed_per_year = daily_feed * lactation_days
        additive_cost_wtp = revenue_per_year * 0.5

        # 換算 CNY/kg 產品
        # 1kg/噸飼料 → 每kg產品覆蓋1噸飼料
        feed_per_year_ton = feed_per_year / 1000
        wtp_per_kg = additive_cost_wtp / feed_per_year_ton if feed_per_year_ton > 0 else 0

        return {
            'extra_piglets_per_litter': round(total_extra_per_litter, 2),
            'extra_piglets_per_year':   round(extra_per_year, 2),
            'piglet_price':             piglet_price,
            'revenue_gain_per_sow':     round(revenue_per_year, 0),
            'saving_per_ton_feed':      round(revenue_per_year / max(feed_per_year_ton,0.1)),
            'wtp_low':  round(wtp_per_kg * 0.8),
            'wtp_mid':  round(wtp_per_kg),
            'wtp_high': round(wtp_per_kg * 1.2),
        }

    elif species == 'layer_chicken':
        ext_days  = eff.get('peak_extension_days', 14)
        egg_row   = get_market_price(conn, 'layer_chicken', region)
        egg_price = egg_row[0] if egg_row else 8.5
        daily_feed = eff.get('daily_feed_kg', 0.115)
        egg_rate   = 0.92
        egg_wt_kg  = 0.063

        extra_egg    = egg_wt_kg * egg_rate * ext_days
        extra_rev    = extra_egg * egg_price
        extra_feed   = daily_feed * ext_days * feed_cost
        net_gain     = extra_rev - extra_feed

        feed_ton = daily_feed * ext_days / 1000
        wtp_per_kg = (net_gain * 0.5) / max(feed_ton, 0.001)

        return {
            'peak_extension_days': ext_days,
            'extra_egg_kg':        round(extra_egg*1000, 1),
            'egg_price':           egg_price,
            'net_gain_per_hen':    round(net_gain, 2),
            'saving_per_ton_feed': round(net_gain / max(feed_ton,0.001)),
            'wtp_low':  round(wtp_per_kg * 0.8),
            'wtp_mid':  round(wtp_per_kg),
            'wtp_high': round(wtp_per_kg * 1.2),
        }
    return None

# ══════════════════════════════════════════════════════
# 定價矩陣（三層通路）
# ══════════════════════════════════════════════════════
def build_price_matrix(wtp_mid):
    """從客戶願付反推三層定價"""
    terminal_price    = round(wtp_mid * 0.55)   # 終端價 = 願付55%
    distributor_price = round(terminal_price / (1 + CHANNEL['dealer_margin']))
    factory_price     = round(distributor_price / (1 + CHANNEL['distributor_margin']))
    gross_margin      = round((terminal_price - factory_price) / terminal_price * 100, 1)

    return {
        '終端飼料廠價格':   f'CNY {terminal_price:,}/kg',
        '區域代理商報價':   f'CNY {distributor_price:,}/kg',
        '建議出廠價':       f'CNY {factory_price:,}/kg',
        '通路毛利率':       f'{gross_margin}%',
        '每噸飼料添加成本': f'CNY {terminal_price:,}/噸（1kg/噸）',
    }

# ══════════════════════════════════════════════════════
# 全矩陣輸出
# ══════════════════════════════════════════════════════
def run_full_matrix(region='CN_northeast'):
    conn = sqlite3.connect(DB_PATH)
    results = {}

    # 肥力寶（促生長）× 5個物種
    prod_g = PRODUCTS['vitalboost_growth']
    for species in prod_g['species_effects']:
        r = calc_growth(conn, species, prod_g, region)
        if r:
            matrix = build_price_matrix(r['wtp_mid'])
            results[f"肥力寶_{species}"] = {**r, 'pricing': matrix}

    # 活力旺（促繁殖）× 2個物種
    prod_r = PRODUCTS['vitalboost_repro']
    for species in prod_r['species_effects']:
        r = calc_repro(conn, species, prod_r, region)
        if r:
            matrix = build_price_matrix(r['wtp_mid'])
            results[f"活力旺_{species}"] = {**r, 'pricing': matrix}

    conn.close()
    return results

def format_telegram(results, region):
    lines = [
        f'💊 <b>定價矩陣 — {region}</b>',
        f'產品規格：1kg/噸飼料 | {datetime.now().strftime("%Y-%m-%d")}',
        ''
    ]

    SPECIES_CN = {
        'finisher_pig':    '育肥豬（80-160kg）',
        'beef_cattle':     '肉牛',
        'meat_sheep':      '肉羊',
        'broiler':         '肉雞',
        'layer_chicken':   '蛋雞',
        'lactating_sow':   '懷孕哺乳母豬',
        'breeding_sow':    '種母豬',
    }

    for key, data in results.items():
        prod_name, species = key.split('_', 1)
        sp_cn = SPECIES_CN.get(species, species)
        pricing = data.get('pricing', {})

        lines.append(f'━━━━━━━━━━━━━━')
        lines.append(f'<b>{prod_name} × {sp_cn}</b>')

        # 效益
        if 'total_saving_per_head' in data:
            lines.append(f'  每頭節省: CNY {data["total_saving_per_head"]}')
            lines.append(f'  每噸飼料效益: CNY {data["saving_per_ton_feed"]}')
        elif 'revenue_gain_per_sow' in data:
            lines.append(f'  每頭母豬年增收: CNY {data["revenue_gain_per_sow"]:,.0f}')
            lines.append(f'  每噸飼料效益: CNY {data["saving_per_ton_feed"]:,}')
        elif 'net_gain_per_hen' in data:
            lines.append(f'  每隻蛋雞增收: CNY {data["net_gain_per_hen"]}')

        # 客戶願付
        lines.append(
            f'  客戶願付: CNY {data["wtp_low"]:,}~{data["wtp_high"]:,}/kg')

        # 定價
        lines.append(f'  {pricing.get("終端飼料廠價格","")}（終端）')
        lines.append(f'  {pricing.get("區域代理商報價","")}（代理商）')
        lines.append(f'  {pricing.get("建議出廠價","")}（出廠）')
        lines.append(f'  每噸添加成本: {pricing.get("每噸飼料添加成本","")}')
        lines.append('')

    return '\n'.join(lines)

def tg(msg):
    try:
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id':TELEGRAM_CHAT,'text':msg,'parse_mode':'HTML'},
            timeout=10)
        # 分段發送（避免超過4096字元限制）
    except Exception as e:
        print(f'TG: {e}')

def tg_send_long(msg):
    """分段發送長訊息"""
    chunks = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
    for chunk in chunks:
        tg(chunk)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--region',   default='CN_northeast')
    parser.add_argument('--telegram', action='store_true')
    parser.add_argument('--json',     action='store_true')
    args = parser.parse_args()

    results = run_full_matrix(args.region)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        output = format_telegram(results, args.region)
        print(output)
        if args.telegram:
            tg_send_long(output)
