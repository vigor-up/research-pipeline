import sqlite3
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')

def q(sql, params):
    r = conn.execute(sql, params).fetchone()
    return r[0] if r else None

def chk(val, label=''):
    return f"OK {val}{label}" if val else "XX 缺"

print('=== 主力物種關鍵數據覆蓋 ===')

# 通用物種
species_list = [
    ('finisher_pig', '育肥豬'),
    ('beef_cattle', '肉牛'),
    ('meat_sheep', '肉羊'),
    ('broiler', '肉雞'),
    ('layer_chicken', '蛋雞'),
    ('duck', '肉鴨'),
    ('dairy_cow', '奶牛'),
]
for sp, name in species_list:
    price    = q("SELECT value FROM market_kpi WHERE species=? AND kpi_id LIKE '%spot_price%' ORDER BY year DESC,credibility DESC LIMIT 1", (sp,))
    fcr      = q("SELECT value FROM market_kpi WHERE species=? AND kpi_id LIKE '%fcr%' AND value BETWEEN 0.5 AND 15 ORDER BY year DESC LIMIT 1", (sp,))
    cost     = q("SELECT value FROM market_kpi WHERE species=? AND kpi_id LIKE '%total_cost%' ORDER BY year DESC LIMIT 1", (sp,))
    feed     = q("SELECT value FROM market_kpi WHERE species=? AND (kpi_id LIKE '%feed_cost%' OR kpi_id LIKE '%feed_price%') AND unit LIKE '%ton%' ORDER BY credibility DESC,year DESC LIMIT 1", (sp,))
    beven    = q("SELECT value FROM market_kpi WHERE species=? AND kpi_id LIKE '%breakeven%' ORDER BY year DESC LIMIT 1", (sp,))
    print(f"\n{name}")
    print(f"  現貨價:   {chk(price,'CNY/kg')}")
    print(f"  FCR:      {chk(fcr)}")
    print(f"  完全成本: {chk(cost)}")
    print(f"  飼料成本: {chk(feed,'元/噸')}")
    print(f"  盈亏線:   {chk(beven)}")

# 哺乳母豬專屬指標
print(f"\n哺乳母豬（專屬指標）")
slaughter = q("SELECT value FROM market_kpi WHERE species='breeding_sow' AND kpi_id LIKE '%slaughter%' ORDER BY year DESC LIMIT 1", ())
preg_price = q("SELECT value FROM market_kpi WHERE species='breeding_sow' AND kpi_id LIKE '%pregnant_sow_avg%' ORDER BY year DESC LIMIT 1", ())
feed_lac   = q("SELECT value FROM market_kpi WHERE species='breeding_sow' AND kpi_id LIKE '%lactation_ton%' ORDER BY year DESC LIMIT 1", ())
annual_cost= q("SELECT value FROM market_kpi WHERE species='breeding_sow' AND kpi_id LIKE '%annual%' AND unit LIKE '%year%' ORDER BY year DESC LIMIT 1", ())
psy        = q("SELECT value FROM market_kpi WHERE species='breeding_sow' AND kpi_id LIKE '%psy%' ORDER BY year DESC LIMIT 1", ())
piglet_cost= q("SELECT value FROM market_kpi WHERE species='breeding_sow' AND kpi_id LIKE '%weaned_piglet%' ORDER BY year DESC LIMIT 1", ())
print(f"  淘汰價:         {chk(slaughter,'CNY/kg')}")
print(f"  懷孕母豬均價:   {chk(preg_price,'元/頭')}")
print(f"  哺乳料成本:     {chk(feed_lac,'元/噸')}")
print(f"  年飼料總成本:   {chk(annual_cost,'元/年')}")
print(f"  PSY:            {chk(psy,'頭/母豬/年')}")
print(f"  每斷奶仔豬成本: {chk(piglet_cost,'元/頭')}")

conn.close()
