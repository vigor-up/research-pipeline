import sqlite3
conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')

priority = [
    ('finisher_pig', '育肥豬'),
    ('breeding_sow', '哺乳母豬'),
    ('beef_cattle', '肉牛'),
    ('meat_sheep', '肉羊'),
    ('broiler', '肉雞'),
    ('layer_chicken', '蛋雞'),
    ('duck', '鴨'),
]

print('=== 主力物種資料覆蓋狀況 ===')
for sp, name in priority:
    price = conn.execute("""
        SELECT value, unit, region, year FROM market_kpi
        WHERE species=? AND kpi_id LIKE '%spot_price%'
        ORDER BY year DESC, credibility DESC LIMIT 1
    """, (sp,)).fetchone()
    fcr = conn.execute("""
        SELECT value FROM market_kpi
        WHERE species=? AND kpi_id LIKE '%fcr%'
        AND value BETWEEN 0.5 AND 15
        ORDER BY year DESC LIMIT 1
    """, (sp,)).fetchone()
    survival = conn.execute("""
        SELECT value FROM market_kpi
        WHERE species=? AND (kpi_id LIKE '%surviv%' OR kpi_id LIKE '%mortality%')
        ORDER BY year DESC LIMIT 1
    """, (sp,)).fetchone()
    feed_cost = conn.execute("""
        SELECT value FROM market_kpi
        WHERE species=? AND kpi_id LIKE '%feed_cost%'
        ORDER BY year DESC LIMIT 1
    """, (sp,)).fetchone()

    price_str = f"{price[0]}{price[1]}({price[2]},{price[3]})" if price else "❌缺價格"
    fcr_str = f"FCR={fcr[0]}" if fcr else "❌缺FCR"
    surv_str = f"存活={survival[0]}" if survival else "❌缺存活率"
    feed_str = f"飼料成本={feed_cost[0]}" if feed_cost else "❌缺飼料成本"
    print(f"{name:8} | {price_str:35} | {fcr_str:12} | {surv_str:15} | {feed_str}")

conn.close()
