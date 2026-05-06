# -*- coding: utf-8 -*-
"""
import_batch2.py
batch2 41 records → D:\LLM\knowledge\market\market_data.db (market_kpi table)
Species: finisher_pig/nursery_pig/lactating_sow/beef_cattle/meat_sheep/meat_goat/tilapia/largemouth_bass/grouper
"""

import sqlite3
import uuid
from datetime import datetime

DB_PATH = r'D:\LLM\knowledge\market\market_data.db'
NOW = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

# (kpi_id, species, region, metric_type, value_min, value_mid, value_max, unit, condition, source_ref, credibility)
batch2 = [
    # --- finisher_pig ---
    ('fcr',           'finisher_pig', 'CN_all',   'baseline',        2.4,  2.6,  2.8,  'kg_feed/kg_gain', '90-120kg_commercial',      'NY/T 2894-2016', 4),
    ('adg',           'finisher_pig', 'CN_all',   'baseline',        700,  800,  900,  'g/day',           '60-120kg_phase',            'MARA 2023',      4),
    ('mortality',     'finisher_pig', 'CN_all',   'baseline',        2.0,  3.0,  5.0,  '%',               'commercial_farm',           'MARA 2023',      4),
    ('slaughter_wt',  'finisher_pig', 'CN_all',   'baseline',        105,  115,  125,  'kg',              'commercial_slaughter',      'MARA 2023',      4),
    ('prrs_fcr_penalty','finisher_pig','CN_all',  'disease_penalty', 10,   20,   30,   'pct_pts',         'prrs_endemic_farm',         'PRRS review 2022',4),
    ('asf_mortality', 'finisher_pig', 'CN_all',   'disease_penalty', 30,   50,   80,   '%',               'asf_outbreak_acute',        'MARA ASF 2022-2024',4),

    # --- nursery_pig ---
    ('fcr',           'nursery_pig',  'CN_all',   'baseline',        1.5,  1.65, 1.8,  'kg_feed/kg_gain', '7-30kg_phase',              'NY standard 2022',4),
    ('adg',           'nursery_pig',  'CN_all',   'baseline',        350,  420,  500,  'g/day',           '7-30kg_phase',              'NY standard 2022',4),
    ('mortality',     'nursery_pig',  'CN_all',   'baseline',        3.0,  5.0,  8.0,  '%',               'commercial_farm',           'MARA 2023',      4),
    ('ped_mortality', 'nursery_pig',  'CN_all',   'disease_penalty', 20,   40,   80,   '%',               'ped_acute_outbreak',        'PED review 2022-2024',4),
    ('prrs_adg_penalty','nursery_pig','CN_all',   'disease_penalty', 15,   25,   35,   'pct_pts',         'prrs_positive_farm',        'PRRS review 2021',4),

    # --- lactating_sow ---
    ('litter_size',   'lactating_sow','CN_all',   'baseline',        10.0, 11.5, 13.0, 'piglets/litter',  'total_born_alive',          'MARA 2023',      4),
    ('piglet_survival','lactating_sow','CN_all',  'baseline',        85.0, 88.0, 92.0, '%',               'birth_to_weaning',          'industry survey 2022',4),
    ('weaning_wt',    'lactating_sow','CN_all',   'baseline',        6.0,  7.0,  8.5,  'kg',              '21-28d_weaning',            'industry survey 2022',4),
    ('prrs_piglet_mortality','lactating_sow','CN_all','disease_penalty',15,25,  40,   'pct_pts',         'prrs_positive_sow_farm',    'PRRS sow trial 2022',4),
    ('ped_litter_mortality','lactating_sow','CN_all','disease_penalty',30, 60,   90,   '%',               'ped_neonatal_piglets',      'PED review 2022-2024',4),

    # --- beef_cattle ---
    ('adg',           'beef_cattle',  'CN_all',   'baseline',        0.9,  1.1,  1.3,  'kg/day',          'feedlot_finishing_120d',    'NY/T 815-2021',  4),
    ('fcr',           'beef_cattle',  'CN_all',   'baseline',        6.0,  7.0,  8.5,  'kg_feed/kg_gain', 'feedlot_finishing',         'NY/T 815-2021',  4),
    ('mortality',     'beef_cattle',  'CN_all',   'baseline',        1.0,  2.0,  3.5,  '%',               'feedlot',                   'MARA 2023',      4),
    ('brd_mortality', 'beef_cattle',  'CN_all',   'disease_penalty', 5,    15,   30,   '%',               'brd_outbreak_feedlot',      'BRD review 2022',4),
    ('brd_adg_penalty','beef_cattle', 'CN_all',   'disease_penalty', 10,   18,   25,   'pct_pts',         'brd_clinical',              'BRD trial 2021', 3),

    # --- meat_sheep ---
    ('adg',           'meat_sheep',   'CN_all',   'baseline',        200,  250,  320,  'g/day',           'intensive_feedlot_90d',     'NY/T 816-2021',  4),
    ('fcr',           'meat_sheep',   'CN_all',   'baseline',        4.5,  5.5,  7.0,  'kg_feed/kg_gain', 'intensive_feedlot',         'NY/T 816-2021',  4),
    ('mortality',     'meat_sheep',   'CN_all',   'baseline',        3.0,  5.0,  8.0,  '%',               'commercial_flock',          'MARA 2023',      4),
    ('ppr_mortality', 'meat_sheep',   'CN_all',   'disease_penalty', 20,   40,   70,   '%',               'ppr_outbreak_unvaccinated', 'OIE 2023',       4),

    # --- meat_goat ---
    ('adg',           'meat_goat',    'CN_all',   'baseline',        150,  185,  220,  'g/day',           'intensive_feedlot',         'DB/T 2022',      4),
    ('fcr',           'meat_goat',    'CN_all',   'baseline',        5.5,  6.5,  8.0,  'kg_feed/kg_gain', 'intensive_feedlot',         'DB/T 2022',       3),
    ('mortality',     'meat_goat',    'CN_all',   'baseline',        4.0,  5.5,  7.5,  '%',               'commercial_flock',          'MARA survey 2022',3),
    ('ppr_mortality', 'meat_goat',    'CN_all',   'disease_penalty', 15,   30,   50,   '%',               'ppr_outbreak',              'OIE 2023',       4),

    # --- tilapia ---
    ('fcr',           'tilapia',      'CN_south', 'baseline',        1.3,  1.45, 1.6,  'kg_feed/kg_gain', 'pond_culture_180d',         'DB44-2021',      4),
    ('adg',           'tilapia',      'CN_south', 'baseline',        2.5,  3.2,  4.0,  'g/day',           'pond_culture_commercial',   'DB44-2021',      4),
    ('survival',      'tilapia',      'CN_south', 'baseline',        75,   80,   88,   '%',               'pond_culture',              'industry 2023',  4),
    ('strep_mortality','tilapia',     'CN_south', 'disease_penalty', 15,   30,   50,   '%',               'streptococcus_outbreak_summer','tilapia disease 2022-2024',4),

    # --- largemouth_bass ---
    ('fcr',           'largemouth_bass','CN_south','baseline',       1.0,  1.25, 1.5,  'kg_feed/kg_gain', 'pond_culture_commercial',   'DB44-2022',      4),
    ('adg',           'largemouth_bass','CN_south','baseline',       3.0,  4.5,  6.0,  'g/day',           'juvenile_to_harvest',       'DB44-2022',      4),
    ('survival',      'largemouth_bass','CN_south','baseline',       70,   76,   83,   '%',               'pond_culture',              'industry 2023',  4),
    ('edwardsiella_mortality','largemouth_bass','CN_south','disease_penalty',15,28,45, '%',               'edwardsiella_outbreak',     'LMB disease 2023',3),

    # --- grouper ---
    ('fcr',           'grouper',      'CN_south', 'baseline',        1.4,  1.65, 1.9,  'kg_feed/kg_gain', 'cage_pond_culture',         'DB46-2021',      4),
    ('adg',           'grouper',      'CN_south', 'baseline',        5.0,  7.5,  10.0, 'g/day',           'commercial_size_300-500g',  'DB46-2021',      4),
    ('survival',      'grouper',      'CN_south', 'baseline',        62,   70,   78,   '%',               'cage_culture',              'industry 2023',  4),
    ('vibrio_mortality','grouper',    'CN_south', 'disease_penalty', 20,   35,   55,   '%',               'vibrio_outbreak_summer',    'grouper disease 2022-2024',4),
]

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
inserted = skipped = 0

for (metric, species, region, mtype, vmin, vmid, vmax, unit, condition, source, cred) in batch2:
    kpi_id = f'{metric}_{species}_{region.lower()}'
    existing = cur.execute(
        "SELECT id FROM market_kpi WHERE kpi_id=? AND region=?",
        (kpi_id, region)
    ).fetchone()
    if existing:
        skipped += 1
        continue

    cur.execute("""
        INSERT INTO market_kpi
            (id, region, country, species, production_stage, kpi_id,
             value, value_min, value_max, unit, year,
             credibility, source_type, source_url, source_title,
             raw_text, language, confirmed, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        str(uuid.uuid4()),
        region, 'CN',
        species, condition, kpi_id,
        vmid, vmin, vmax,
        unit, 2024,
        cred,
        'academic_background' if mtype == 'baseline' else 'gov_stats',
        '', source,
        f'{kpi_id} mid={vmid} range={vmin}-{vmax} {unit}',
        'zh-CN', 1, NOW
    ))
    inserted += 1

conn.commit()

total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
print(f'Done. Inserted: {inserted}, Skipped: {skipped}')
print(f'market_kpi total: {total} rows')
conn.close()
