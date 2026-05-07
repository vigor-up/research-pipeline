# -*- coding: utf-8 -*-
"""
pricing_matrix_v2.py
市場反推定價矩陣 v2
基準：育肥豬FCR改善25%，客戶每降0.1 FCR願付CNY30-40
物種劑量：育肥豬1kg/噸，肉牛2kg/噸，其他1kg/噸
"""
import sqlite3, json, requests, argparse
from datetime import datetime

DB_PATH        = r'D:\LLM\knowledge\market\market_data.db'
TELEGRAM_TOKEN = '8703702788:AAFKEiGmLYTAuFVG9GX-gRtVTUUyi-f_5mM'
TELEGRAM_CHAT  = 897274134

# ══════════════════════════════════════════════════════
# 物種參數（對外規格，隱藏核心原料比例）
# FCR改善幅度規律：FCR絕對值越小改善越小
# 豬2.75→25%, 牛7.0→25%, 羊5.5→20%, 雞1.8→15%
# 蛋雞用產蛋率+峰值延長計算, 蝦魚12%
# ══════════════════════════════════════════════════════
SPECIES_PARAMS = {
    'finisher_pig': {
        'name_cn':        '育肥豬（80-160kg）',
        'product':        '肥力寶',
        'dosage_kg_ton':  1.0,
        'fcr_improve_pct': 25.0,
        'wtp_per_01fcr_low':  30,
        'wtp_per_01fcr_high': 40,
        'gain_kg':        80,   # 80→160kg
        'calc_type':      'fcr',
    },
    'beef_cattle': {
        'name_cn':        '肉牛',
        'product':        '肥力寶',
        'dosage_kg_ton':  2.0,  # 肉牛2kg/噸
        'fcr_improve_pct': 25.0,
        'wtp_per_01fcr_low':  80,   # 牛體型大，每0.1FCR效益更高
        'wtp_per_01fcr_high': 120,
        'gain_kg':        150,
        'calc_type':      'fcr',
    },
    'meat_sheep': {
        'name_cn':        '肉羊',
        'product':        '肥力寶',
        'dosage_kg_ton':  1.0,
        'fcr_improve_pct': 20.0,
        'wtp_per_01fcr_low':  15,
        'wtp_per_01fcr_high': 22,
        'gain_kg':        25,
        'calc_type':      'fcr',
    },
    'broiler': {
        'name_cn':        '肉雞',
        'product':        '肥力寶',
        'dosage_kg_ton':  1.0,
        'fcr_improve_pct': 15.0,
        'adg_improve_pct': 8.0,   # 同期飼料重量增加8%體重
        'wtp_per_01fcr_low':  25,
        'wtp_per_01fcr_high': 35,
        'gain_kg':        2.4,
        'calc_type':      'fcr_adg',
    },
    'layer_chicken': {
        'name_cn':        '蛋雞',
        'product':        '肥力寶',
        'dosage_kg_ton':  1.0,
        'fcr_improve_pct': 15.0,
        'peak_extension_days': 14,
        'egg_rate_improve': 3.0,
        'daily_feed_kg':  0.115,
        'calc_type':      'layer',
    },
    'lactating_sow': {
        'name_cn':        '懷孕哺乳母豬',
        'product':        '活力旺',
        'dosage_kg_ton':  1.0,
        'litter_improve': 0.5,
        'survival_improve': 3.0,
        'weaning_wt_improve': 5.0,
        'cycles_per_year': 2.3,
        'calc_type':      'repro_sow',
    },
    'shrimp': {
        'name_cn':        '白蝦',
        'product':        '肥力寶',
        'dosage_kg_ton':  1.0,
        'fcr_improve_pct': 12.0,
        'survival_improve': 5.0,
        'gain_kg':        0.02,  # 20g/尾
        'calc_type':      'aqua',
    },
    'tilapia': {
        'name_cn':        '羅非魚',
        'product':        '肥力寶',
        'dosage_kg_ton':  1.0,
        'fcr_improve_pct': 12.0,
        'gain_kg':        0.5,
        'calc_type':      'aqua',
    },
}

CHANNEL = {
    'terminal_ratio':     0.55,  # 終端 = 願付×55%
    'distributor_margin': 0.30,
    'dealer_margin':      0.25,
}

# ══════════════════════════════════════════════════════
# DB 查詢
# ══════════════════════════════════════════════════════
def get_kpi(conn, species, kpi, region='CN_northeast'):
    # 排除 penalty/saving/ratio，FCR限制合理範圍
    extra = "AND kpi_id NOT LIKE '%penalty%' AND kpi_id NOT LIKE '%saving%' AND kpi_id NOT LIKE '%loss%' AND kpi_id NOT LIKE '%ratio%'"
    val_filter = "AND value BETWEEN 0.5 AND 12" if kpi == 'fcr' else "AND value IS NOT NULL"
    row = conn.execute(f"""
        SELECT value, unit, source_title FROM market_kpi
        WHERE species=? AND kpi_id LIKE ? AND region=?
          {extra} {val_filter}
        ORDER BY credibility DESC, year DESC LIMIT 1
    """, (species, f'%{kpi}%', region)).fetchone()
    if not row:
        row = conn.execute(f"""
            SELECT value, unit, source_title FROM market_kpi
            WHERE species=? AND kpi_id LIKE ?
              {extra} {val_filter}
            ORDER BY credibility DESC, year DESC LIMIT 1
        """, (species, f'%{kpi}%')).fetchone()
    return row

def get_price(conn, species, region='CN_northeast'):
    row = conn.execute("""
        SELECT value, unit FROM market_kpi
        WHERE species=? AND kpi_id LIKE '%spot_price%'
          AND (region=? OR region='CN_all') AND value IS NOT NULL
        ORDER BY year DESC, credibility DESC LIMIT 1
    """, (species, region)).fetchone()
    return row

def get_feed_cost(conn, region='CN_northeast'):
    soy  = conn.execute("""SELECT value FROM market_kpi
        WHERE kpi_id LIKE '%soybean_meal%' AND (region=? OR region='CN_all')
        ORDER BY year DESC LIMIT 1""", (region,)).fetchone()
    corn = conn.execute("""SELECT value FROM market_kpi
        WHERE kpi_id LIKE '%corn%' AND (region=? OR region='CN_all')
        ORDER BY year DESC LIMIT 1""", (region,)).fetchone()
    return round(((corn[0] if corn else 2150)*0.60 +
                  (soy[0]  if soy  else 3200)*0.20 +
                  2800*0.20) / 1000, 3)

# ══════════════════════════════════════════════════════
# 計算引擎
# ══════════════════════════════════════════════════════
def calc_roi(conn, species, sp, region):
    calc_type = sp['calc_type']
    feed_cost = get_feed_cost(conn, region)
    dosage    = sp['dosage_kg_ton']

    if calc_type == 'fcr':
        fcr_row  = get_kpi(conn, species, 'fcr', region)
        mkt_row  = get_price(conn, species, region)
        fcr_base = fcr_row[0] if fcr_row else None
        mkt_p    = mkt_row[0] if mkt_row else None
        if not fcr_base: return None

        fcr_new   = fcr_base * (1 - sp['fcr_improve_pct']/100)
        fcr_drop  = fcr_base - fcr_new
        units_01  = fcr_drop / 0.1

        wtp_low  = units_01 * sp['wtp_per_01fcr_low']
        wtp_high = units_01 * sp['wtp_per_01fcr_high']
        wtp_mid  = (wtp_low + wtp_high) / 2

        # 每頭節省
        gain_kg      = sp['gain_kg']
        feed_saved   = (fcr_base - fcr_new) * gain_kg
        cost_saved   = feed_saved * feed_cost
        mort_row     = get_kpi(conn, species, 'mortality', region)
        mort_saving  = (mkt_p * gain_kg * 0.01) if mkt_p else 0

        # 每噸飼料效益換算
        feed_per_head     = fcr_new * gain_kg
        heads_per_ton_add = 1000 / (feed_per_head * dosage) if feed_per_head > 0 else 0
        saving_per_ton    = (cost_saved + mort_saving) * heads_per_ton_add

        return {
            'fcr_base': fcr_base,
            'fcr_new': round(fcr_new,2),
            'fcr_drop': round(fcr_drop,3),
            'fcr_improve_pct': sp['fcr_improve_pct'],
            'cost_saved_per_head': round(cost_saved,1),
            'saving_per_ton_feed': round(saving_per_ton,0),
            'wtp_low': round(wtp_low,0),
            'wtp_mid': round(wtp_mid,0),
            'wtp_high': round(wtp_high,0),
            'dosage': dosage,
            'mkt_price': mkt_p,
            'source_fcr': fcr_row[2] if fcr_row else '估算',
        }

    elif calc_type == 'fcr_adg':
        fcr_row  = get_kpi(conn, species, 'fcr', region)
        mkt_row  = get_price(conn, species, region)
        fcr_base = fcr_row[0] if fcr_row else 1.85
        mkt_p    = mkt_row[0] if mkt_row else 12.0

        fcr_new   = fcr_base * (1 - sp['fcr_improve_pct']/100)
        fcr_drop  = fcr_base - fcr_new
        units_01  = fcr_drop / 0.1
        wtp_low   = units_01 * sp['wtp_per_01fcr_low']
        wtp_high  = units_01 * sp['wtp_per_01fcr_high']

        # 肉雞：同期飼料增加8%體重
        gain_kg      = sp['gain_kg']
        adg_improve  = sp.get('adg_improve_pct', 0)
        extra_weight = gain_kg * adg_improve/100
        adg_revenue  = extra_weight * mkt_p

        wtp_mid = (wtp_low + wtp_high) / 2 + adg_revenue * 10

        feed_per_bird = fcr_new * gain_kg
        birds_per_ton = 1000 / (feed_per_bird * dosage)
        saving_per_ton = ((fcr_base-fcr_new)*gain_kg*feed_cost + adg_revenue) * birds_per_ton

        return {
            'fcr_base': fcr_base,
            'fcr_new': round(fcr_new,2),
            'fcr_improve_pct': sp['fcr_improve_pct'],
            'adg_improve_pct': adg_improve,
            'extra_weight_per_bird': round(extra_weight*1000,1),
            'adg_revenue_per_bird': round(adg_revenue,2),
            'saving_per_ton_feed': round(saving_per_ton,0),
            'wtp_low': round(wtp_low,0),
            'wtp_mid': round(wtp_mid,0),
            'wtp_high': round(wtp_high,0),
            'dosage': dosage,
        }

    elif calc_type == 'layer':
        egg_row   = get_price(conn, 'layer_chicken', region)
        egg_price = egg_row[0] if egg_row else 8.5
        ext_days  = sp['peak_extension_days']
        egg_rate  = 0.92
        egg_wt    = 0.063
        daily_feed = sp['daily_feed_kg']

        # FCR改善效益
        fcr_row  = get_kpi(conn, 'layer_chicken', 'fcr', region)
        fcr_base = fcr_row[0] if fcr_row else 2.2
        fcr_new  = fcr_base * (1 - sp['fcr_improve_pct']/100)

        # 峰值延長效益
        extra_egg    = egg_wt * egg_rate * ext_days
        extra_rev    = extra_egg * egg_price
        extra_feed_c = daily_feed * ext_days * feed_cost
        net_peak     = extra_rev - extra_feed_c

        # 產蛋率提升（以300天計）
        egg_rate_gain = sp.get('egg_rate_improve',0)/100
        net_egg_rate  = egg_wt * egg_rate_gain * 300 * egg_price

        total_saving_per_hen = net_peak + net_egg_rate

        # 每噸飼料
        feed_yr_kg  = daily_feed * 300
        ton_per_hen = feed_yr_kg / 1000
        saving_per_ton = total_saving_per_hen / (ton_per_hen * dosage)

        wtp_mid  = saving_per_ton * 0.5
        wtp_low  = wtp_mid * 0.8
        wtp_high = wtp_mid * 1.2

        return {
            'fcr_base': fcr_base,
            'fcr_new': round(fcr_new,2),
            'peak_extension_days': ext_days,
            'extra_egg_per_hen_g': round(extra_egg*1000,1),
            'net_peak_revenue': round(net_peak,2),
            'net_egg_rate_revenue': round(net_egg_rate,2),
            'total_saving_per_hen': round(total_saving_per_hen,2),
            'saving_per_ton_feed': round(saving_per_ton,0),
            'wtp_low': round(wtp_low,0),
            'wtp_mid': round(wtp_mid,0),
            'wtp_high': round(wtp_high,0),
            'dosage': dosage,
        }

    elif calc_type == 'repro_sow':
        piglet_row   = get_kpi(conn, 'nursery_pig', 'piglet_price', region)
        piglet_price = piglet_row[0] if piglet_row else 280
        cycles       = sp['cycles_per_year']
        litter_base  = 11.0

        extra_per_litter = sp['litter_improve'] + litter_base*(sp['survival_improve']/100)
        extra_per_year   = extra_per_litter * cycles
        revenue_per_year = extra_per_year * piglet_price

        daily_feed    = 3.5
        lactation_d   = 28 * cycles
        feed_yr_ton   = daily_feed * lactation_d / 1000
        saving_per_ton = revenue_per_year / (feed_yr_ton * dosage)

        wtp_mid  = saving_per_ton * 0.5
        wtp_low  = wtp_mid * 0.8
        wtp_high = wtp_mid * 1.2

        return {
            'extra_piglets_per_litter': round(extra_per_litter,2),
            'extra_piglets_per_year':   round(extra_per_year,2),
            'piglet_price':             piglet_price,
            'revenue_per_sow_year':     round(revenue_per_year,0),
            'saving_per_ton_feed':      round(saving_per_ton,0),
            'wtp_low':  round(wtp_low,0),
            'wtp_mid':  round(wtp_mid,0),
            'wtp_high': round(wtp_high,0),
            'dosage':   dosage,
        }

    elif calc_type == 'aqua':
        mkt_row  = get_price(conn, species, 'CN_south')
        mkt_p    = mkt_row[0] if mkt_row else 50.0
        fcr_row  = get_kpi(conn, species, 'fcr', 'CN_south')
        fcr_base = fcr_row[0] if fcr_row else 1.4
        fcr_new  = fcr_base * (1 - sp['fcr_improve_pct']/100)
        # 每噸飼料產出水產kg數
        output_base    = 1000 / fcr_base
        output_new     = 1000 / fcr_new
        extra_output   = output_new - output_base
        saving_per_ton = extra_output * mkt_p
        survival_gain  = output_base * mkt_p * sp.get('survival_improve',0)/100
        saving_per_ton += survival_gain
        wtp_mid  = saving_per_ton * 0.5
        wtp_low  = wtp_mid * 0.8
        wtp_high = wtp_mid * 1.2
        gain_kg  = sp['gain_kg']
        wtp_mid  = saving_per_ton * 0.5
        wtp_low  = wtp_mid * 0.8
        wtp_high = wtp_mid * 1.2

        return {
            'fcr_base': fcr_base,
            'fcr_new': round(fcr_new,3),
            'fcr_improve_pct': sp['fcr_improve_pct'],
            'saving_per_ton_feed': round(saving_per_ton,0),
            'mkt_price': mkt_p,
            'wtp_low': round(wtp_low,0),
            'wtp_mid': round(wtp_mid,0),
            'wtp_high': round(wtp_high,0),
            'dosage': dosage,
        }
    return None

# ══════════════════════════════════════════════════════
# 定價矩陣
# ══════════════════════════════════════════════════════
def build_matrix(wtp_mid, dosage):
    terminal    = round(wtp_mid * CHANNEL['terminal_ratio'])
    distributor = round(terminal / (1 + CHANNEL['dealer_margin']))
    factory     = round(distributor / (1 + CHANNEL['distributor_margin']))
    return {
        'terminal':    terminal,
        'distributor': distributor,
        'factory':     factory,
        'per_ton_cost': terminal * dosage,
    }

def run_all(region='CN_northeast'):
    conn = sqlite3.connect(DB_PATH)
    results = {}
    for species, sp in SPECIES_PARAMS.items():
        r = calc_roi(conn, species, sp, region)
        if r:
            m = build_matrix(r['wtp_mid'], sp['dosage_kg_ton'])
            results[species] = {**sp, 'roi': r, 'matrix': m}
    conn.close()
    return results

def format_output(results, region):
    lines = [
        f'💊 <b>定價矩陣 v2 — {region}</b>',
        f'基準：育肥豬FCR↓25%，每↓0.1願付CNY30-40',
        f'規格：1kg/噸（肉牛2kg/噸）| {datetime.now().strftime("%Y-%m-%d")}',
        '',
    ]
    for species, data in results.items():
        roi = data['roi']
        m   = data['matrix']
        lines += [
            f'━━━━━━━━━━━━━━',
            f'<b>{data["product"]} × {data["name_cn"]}</b>',
            f'  用量：{data["dosage_kg_ton"]}kg/噸飼料',
        ]
        if 'fcr_base' in roi:
            lines.append(
                f'  FCR: {roi.get("fcr_base","?")} → {roi.get("fcr_new","?")}'
                f'（改善{roi.get("fcr_improve_pct","?")}%）')
        if 'saving_per_ton_feed' in roi:
            lines.append(f'  每噸飼料效益: CNY {roi["saving_per_ton_feed"]:,}')
        if 'revenue_per_sow_year' in roi:
            lines.append(
                f'  每頭母豬年增收: CNY {roi["revenue_per_sow_year"]:,}'
                f'（+{roi["extra_piglets_per_year"]}頭仔豬/年）')
        if 'total_saving_per_hen' in roi:
            lines.append(
                f'  每隻蛋雞增收: CNY {roi["total_saving_per_hen"]}'
                f'（峰值+{roi["peak_extension_days"]}天）')
        if 'extra_weight_per_bird' in roi:
            lines.append(
                f'  同期增重: +{roi["extra_weight_per_bird"]}g/隻'
                f'（+{roi["adg_improve_pct"]}%）')
        lines += [
            f'  客戶願付: CNY {roi["wtp_low"]:,}~{roi["wtp_high"]:,}/kg',
            f'  ┌ 終端飼料廠: CNY {m["terminal"]:,}/kg',
            f'  ├ 區域代理商: CNY {m["distributor"]:,}/kg',
            f'  └ 出廠建議價: CNY {m["factory"]:,}/kg',
            f'  每噸飼料添加成本: CNY {m["per_ton_cost"]:,}/噸',
            '',
        ]
    return '\n'.join(lines)

def tg_send(msg):
    for chunk in [msg[i:i+4000] for i in range(0, len(msg), 4000)]:
        try:
            requests.post(
                f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
                json={'chat_id':TELEGRAM_CHAT,'text':chunk,'parse_mode':'HTML'},
                timeout=10)
        except Exception as e:
            print(f'TG: {e}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--region',   default='CN_northeast')
    parser.add_argument('--telegram', action='store_true')
    args = parser.parse_args()

    results = run_all(args.region)
    output  = format_output(results, args.region)
    print(output)
    if args.telegram:
        tg_send(output)
