# -*- coding: utf-8 -*-
"""
price_sources.py
各物種現貨價格定向爬蟲來源配置
整合進 auto_collect_v4 的 price_collector 模組
"""

PRICE_SOURCES = [
    # ── 生豬 ──────────────────────────────────────────
    {
        'species': 'finisher_pig',
        'kpi': 'spot_price',
        'unit': 'CNY/kg',
        'region': 'CN_all',
        'sources': [
            {
                'name': '新牧網生豬價格',
                'url': 'https://www.xumuwang.com/pigprice/',
                'mode': 'fast',
                'credibility': 4,
            },
            {
                'name': '農業農村部生豬價格',
                'url': 'http://zdscxx.moa.gov.cn:8080/misportal/public/publicationViewRedirect.do?websiteCode=ZLJGXX',
                'mode': 'fast',
                'credibility': 5,
            },
        ]
    },
    # ── 雞蛋/肉雞 ──────────────────────────────────────
    {
        'species': 'layer_chicken',
        'kpi': 'spot_price_egg',
        'unit': 'CNY/kg',
        'region': 'CN_all',
        'sources': [
            {
                'name': '中國禽業協會雞蛋價格',
                'url': 'https://www.caaa.cn/market/egg/',
                'mode': 'fast',
                'credibility': 4,
            },
            {
                'name': '新牧網雞蛋行情',
                'url': 'https://www.xumuwang.com/eggprice/',
                'mode': 'fast',
                'credibility': 4,
            },
        ]
    },
    {
        'species': 'broiler',
        'kpi': 'spot_price',
        'unit': 'CNY/kg',
        'region': 'CN_all',
        'sources': [
            {
                'name': '新牧網肉雞價格',
                'url': 'https://www.xumuwang.com/broilerprice/',
                'mode': 'fast',
                'credibility': 4,
            },
        ]
    },
    # ── 牛 ────────────────────────────────────────────
    {
        'species': 'beef_cattle',
        'kpi': 'spot_price',
        'unit': 'CNY/kg',
        'region': 'CN_all',
        'sources': [
            {
                'name': '新牧網牛價行情',
                'url': 'https://www.xumuwang.com/cattleprice/',
                'mode': 'fast',
                'credibility': 4,
            },
            {
                'name': '農業農村部牛肉價格監測',
                'url': 'http://zdscxx.moa.gov.cn:8080/misportal/public/beef.do',
                'mode': 'fast',
                'credibility': 5,
            },
        ]
    },
    # ── 羊 ────────────────────────────────────────────
    {
        'species': 'meat_sheep',
        'kpi': 'spot_price',
        'unit': 'CNY/kg',
        'region': 'CN_all',
        'sources': [
            {
                'name': '新牧網羊價行情',
                'url': 'https://www.xumuwang.com/sheepprice/',
                'mode': 'fast',
                'credibility': 4,
            },
        ]
    },
    # ── 水產：蝦 ──────────────────────────────────────
    {
        'species': 'shrimp',
        'kpi': 'spot_price',
        'unit': 'CNY/kg',
        'region': 'CN_south',
        'sources': [
            {
                'name': '中國水產門戶網蝦價',
                'url': 'https://www.shuichan.cc/price_list-0-4.html',
                'mode': 'fast',
                'credibility': 4,
            },
            {
                'name': '水產養殖網蝦類行情',
                'url': 'https://www.yc-sc.com/price/shrimp/',
                'mode': 'fast',
                'credibility': 3,
            },
        ]
    },
    # ── 水產：魚（羅非魚/大口鱸/石斑）─────────────────
    {
        'species': 'tilapia',
        'kpi': 'spot_price',
        'unit': 'CNY/kg',
        'region': 'CN_south',
        'sources': [
            {
                'name': '中國水產門戶網羅非魚價',
                'url': 'https://www.shuichan.cc/price_list-0-2.html',
                'mode': 'fast',
                'credibility': 4,
            },
        ]
    },
    {
        'species': 'largemouth_bass',
        'kpi': 'spot_price',
        'unit': 'CNY/kg',
        'region': 'CN_south',
        'sources': [
            {
                'name': '中國水產門戶網加州鱸價',
                'url': 'https://www.shuichan.cc/price_list-0-1.html',
                'mode': 'fast',
                'credibility': 4,
            },
        ]
    },
    {
        'species': 'grouper',
        'kpi': 'spot_price',
        'unit': 'CNY/kg',
        'region': 'CN_south',
        'sources': [
            {
                'name': '中國水產門戶網石斑魚價',
                'url': 'https://www.shuichan.cc/price_list-0-3.html',
                'mode': 'fast',
                'credibility': 4,
            },
        ]
    },
    # ── 飼料原料（成本端）─────────────────────────────
    {
        'species': 'feed_ingredient',
        'kpi': 'spot_price_soybean_meal',
        'unit': 'CNY/ton',
        'region': 'CN_all',
        'sources': [
            {
                'name': '大連商品交易所豆粕期貨',
                'url': 'https://www.dce.com.cn/dceweb/quotation/showMemberLevelQuotation.html',
                'mode': 'fast',
                'credibility': 5,
            },
            {
                'name': '中國飼料行業信息網豆粕',
                'url': 'http://www.feedtrade.com.cn/market/soybean_meal.html',
                'mode': 'fast',
                'credibility': 4,
            },
        ]
    },
    {
        'species': 'feed_ingredient',
        'kpi': 'spot_price_corn',
        'unit': 'CNY/ton',
        'region': 'CN_all',
        'sources': [
            {
                'name': '大連商品交易所玉米期貨',
                'url': 'https://www.dce.com.cn/dceweb/quotation/showMemberLevelQuotation.html',
                'mode': 'fast',
                'credibility': 5,
            },
            {
                'name': '中國飼料行業信息網玉米',
                'url': 'http://www.feedtrade.com.cn/market/corn.html',
                'mode': 'fast',
                'credibility': 4,
            },
        ]
    },
]
