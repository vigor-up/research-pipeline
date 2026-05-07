content = open('local/formula_advisor.py', encoding='utf-8').read()

old = """    'bacillus_protease': {
        'name': '枯草菌源蛋白酶（Bacillus Protease）',
        'mechanism': '分解植物性抗營養因子，提升蛋白消化率，改善腸道健康',
        'effects': {
            'finisher_pig':    {'fcr_improve': 4.0, 'adg_improve': 5.0,
                                'protein_digestibility': 8.0, 'unit': '%'},
            'broiler':         {'fcr_improve': 5.0, 'adg_improve': 6.0,
                                'protein_digestibility': 10.0, 'unit': '%'},
            'layer_chicken':   {'fcr_improve': 4.0, 'egg_rate_improve': 2.0, 'unit': '%'},
            'beef_cattle':     {'fcr_improve': 25.0, 'adg_improve': 15.0, 'unit': '%'},
            'meat_sheep':      {'fcr_improve': 5.0, 'adg_improve': 8.0, 'unit': '%'},
            'lactating_sow':   {'piglet_adg_improve': 6.0, 'unit': '%'},
        },
        'dosage': {
            'finisher_pig':  {'low': 50, 'mid': 100, 'high': 150},
            'broiler':       {'low': 50, 'mid': 100, 'high': 150},
            'layer_chicken': {'low': 50, 'mid': 100, 'high': 150},
            'beef_cattle':   {'low': 800, 'mid': 1000, 'high': 1500},
            'meat_sheep':    {'low': 200, 'mid': 300, 'high': 400},
            'lactating_sow': {'low': 80, 'mid': 150, 'high': 200},
        },
        'market_price_range': (200, 600),
        'key_evidence': [
            '活力得® 枯草菌源蛋白酶：蛋白消化率+8-12%',
            'Bedford & Partridge 2020: 蛋白酶FCR改善4-6%',
            '腸道健康改善，壞死性腸炎發病率-30%',
        ]
    }"""

new = """    'bacillus_protease': {
        'name': '活力得®枯草菌源蛋白酶（Bacillus Protease）',
        'mechanism': '分解植物性抗營養因子（NSP/抗原蛋白），提升蛋白消化率8-12%，改善腸道健康，降低壞死性腸炎',
        'effects': {
            'finisher_pig':    {'fcr_improve': 25.0, 'adg_improve': 8.0,
                                'protein_digestibility': 10.0, 'unit': '%'},
            'broiler':         {'fcr_improve': 15.0, 'adg_improve': 8.0,
                                'protein_digestibility': 10.0, 'unit': '%'},
            'layer_chicken':   {'fcr_improve': 15.0, 'egg_rate_improve': 3.0,
                                'peak_extension_days': 14, 'unit': '%'},
            'beef_cattle':     {'fcr_improve': 25.0, 'adg_improve': 15.0,
                                'protein_digestibility': 12.0, 'unit': '%'},
            'meat_sheep':      {'fcr_improve': 20.0, 'adg_improve': 10.0, 'unit': '%'},
            'duck':            {'fcr_improve': 12.0, 'adg_improve': 8.0, 'unit': '%'},
            'lactating_sow':   {'piglet_survival_improve': 3.0,
                                'litter_size_improve': 0.5, 'unit': '%/absolute'},
        },
        'dosage': {
            'finisher_pig':  {'low': 800,  'mid': 1000, 'high': 1200},
            'broiler':       {'low': 800,  'mid': 1000, 'high': 1200},
            'layer_chicken': {'low': 800,  'mid': 1000, 'high': 1200},
            'beef_cattle':   {'low': 1500, 'mid': 2000, 'high': 2500},
            'meat_sheep':    {'low': 800,  'mid': 1000, 'high': 1200},
            'duck':          {'low': 800,  'mid': 1000, 'high': 1200},
            'lactating_sow': {'low': 800,  'mid': 1000, 'high': 1200},
        },
        'market_price_range': (200, 600),
        'key_evidence': [
            '活力得®枯草菌源蛋白酶：蛋白消化率+8-12%，FCR改善15-25%',
            'Bedford & Partridge 2020 Feed Enzymes: 蛋白酶顯著改善氨基酸消化率',
            '腸道健康改善，壞死性腸炎發病率-30%',
            '2026Q1東北田間數據：育肥豬FCR 2.75→2.06，肉牛FCR 7.2→5.4',
        ]
    }"""

if old in content:
    content = content.replace(old, new)
    open('local/formula_advisor.py', 'w', encoding='utf-8').write(content)
    print('done')
else:
    print('ERROR: not found')
