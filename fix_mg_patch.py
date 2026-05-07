import pathlib, re

p = pathlib.Path('local/seed_benchmarks.py')
src = p.read_text(encoding='utf-8')

# 1. 補回被切斷的 ]
old = 'confirmed = conn.execute("SELECT COUNT(*) FROM market_kpi WHERE confirmed=1").fetchone()[0'
new = 'confirmed = conn.execute("SELECT COUNT(*) FROM market_kpi WHERE confirmed=1").fetchone()[0]'
src = src.replace(old, new, 1)

# 2. 找到誤插的 patch block 並移除
marker = '    # MG northeast_china patch 2025-05-06'
# 找到 fetchone()[0] 之後的 marker 位置
anchor = src.find('fetchone()[0]')
bad_start = src.find('\n' + marker, anchor)
# patch block 結尾：找下一個不屬於 patch 的行（confirmed =）
bad_end = src.find('\n    confirmed = ', bad_start)
src = src[:bad_start] + src[bad_end:]

# 3. 把 patch 插到真正的 BENCHMARKS list 結尾（最後一個 ] 之前）
patch_block = '''
    # MG northeast_china patch 2025-05-06
    {"kpi_id":"mg_infection_laying_loss","species":"layer_chicken","region":"northeast_china","metric_type":"disease_penalty","value_low":5.0,"value_mid":10.0,"value_high":15.0,"unit":"percentage_points","condition":"mg_positive_winter_housing","source":"field_survey_northeast_china","data_quality":"A"},
    {"kpi_id":"mg_infection_fcr_penalty","species":"layer_chicken","region":"northeast_china","metric_type":"disease_penalty","value_low":2.3,"value_mid":2.4,"value_high":2.5,"unit":"ratio_g_feed_per_g_egg","condition":"mg_positive_winter_housing","source":"field_survey_northeast_china","data_quality":"A"},
    {"kpi_id":"mg_infection_mortality_rise","species":"layer_chicken","region":"northeast_china","metric_type":"disease_penalty","value_low":2.0,"value_mid":3.0,"value_high":5.0,"unit":"percentage_points","condition":"mg_positive_winter_housing","source":"field_survey_northeast_china","data_quality":"B"},
    {"kpi_id":"mg_prevalence_northeast_winter","species":"layer_chicken","region":"northeast_china","metric_type":"epidemiology","value_low":80.0,"value_mid":85.0,"value_high":95.0,"unit":"percent","condition":"winter_closed_housing","source":"epidemiological_survey_northeast","data_quality":"A"},
    {"kpi_id":"mg_lcfa_laying_recovery","species":"layer_chicken","region":"northeast_china","metric_type":"intervention_effect","value_low":5.0,"value_mid":7.0,"value_high":10.0,"unit":"percentage_points","condition":"lcfa_intervention_mg_challenged","source":"intervention_trial_data","data_quality":"B"},
    {"kpi_id":"mg_lcfa_fcr_improvement","species":"layer_chicken","region":"northeast_china","metric_type":"intervention_effect","value_low":0.10,"value_mid":0.15,"value_high":0.20,"unit":"ratio_improvement","condition":"lcfa_intervention_mg_challenged","source":"intervention_trial_data","data_quality":"B"},
'''

# BENCHMARKS list 的最後一個 ] — 找 ]\n\ndef 或 ]\n\nif 這種結尾模式
m = list(re.finditer(r'\n\]\n', src))
insert_idx = m[-1].start()  # 最後一個 ]\n 前
src = src[:insert_idx] + patch_block + src[insert_idx:]

p.write_text(src, encoding='utf-8')
print('done')
