import pathlib, re

p = pathlib.Path('local/seed_benchmarks.py')
src = p.read_text(encoding='utf-8')

# 找到 MG patch block 替換成正確 schema
old_block = '''
    # MG northeast_china patch 2025-05-06
    {"kpi_id":"mg_infection_laying_loss","species":"layer_chicken","region":"northeast_china","metric_type":"disease_penalty","value_low":5.0,"value_mid":10.0,"value_high":15.0,"unit":"percentage_points","condition":"mg_positive_winter_housing","source":"field_survey_northeast_china","data_quality":"A"},
    {"kpi_id":"mg_infection_fcr_penalty","species":"layer_chicken","region":"northeast_china","metric_type":"disease_penalty","value_low":2.3,"value_mid":2.4,"value_high":2.5,"unit":"ratio_g_feed_per_g_egg","condition":"mg_positive_winter_housing","source":"field_survey_northeast_china","data_quality":"A"},
    {"kpi_id":"mg_infection_mortality_rise","species":"layer_chicken","region":"northeast_china","metric_type":"disease_penalty","value_low":2.0,"value_mid":3.0,"value_high":5.0,"unit":"percentage_points","condition":"mg_positive_winter_housing","source":"field_survey_northeast_china","data_quality":"B"},
    {"kpi_id":"mg_prevalence_northeast_winter","species":"layer_chicken","region":"northeast_china","metric_type":"epidemiology","value_low":80.0,"value_mid":85.0,"value_high":95.0,"unit":"percent","condition":"winter_closed_housing","source":"epidemiological_survey_northeast","data_quality":"A"},
    {"kpi_id":"mg_lcfa_laying_recovery","species":"layer_chicken","region":"northeast_china","metric_type":"intervention_effect","value_low":5.0,"value_mid":7.0,"value_high":10.0,"unit":"percentage_points","condition":"lcfa_intervention_mg_challenged","source":"intervention_trial_data","data_quality":"B"},
    {"kpi_id":"mg_lcfa_fcr_improvement","species":"layer_chicken","region":"northeast_china","metric_type":"intervention_effect","value_low":0.10,"value_mid":0.15,"value_high":0.20,"unit":"ratio_improvement","condition":"lcfa_intervention_mg_challenged","source":"intervention_trial_data","data_quality":"B"},'''

new_block = '''
    # MG northeast_china patch 2025-05-06
    {"kpi_id":"mg_infection_laying_loss","species":"layer_chicken","region":"CN_north","value":10.0,"value_min":5.0,"value_max":15.0,"unit":"percentage_points","credibility":0.8,"source_type":"field_survey","source_title":"Northeast China MG field survey 2023","note":"东北冬季密闭鸡舍MG阳性率>80%","production_stage":"laying","year":2023},
    {"kpi_id":"mg_infection_fcr_penalty","species":"layer_chicken","region":"CN_north","value":2.4,"value_min":2.3,"value_max":2.5,"unit":"ratio_g_feed_per_g_egg","credibility":0.8,"source_type":"field_survey","source_title":"Northeast China MG field survey 2023","note":"健康场2.1-2.2；感染场2.3-2.5","production_stage":"laying","year":2023},
    {"kpi_id":"mg_infection_mortality_rise","species":"layer_chicken","region":"CN_north","value":3.0,"value_min":2.0,"value_max":5.0,"unit":"percentage_points","credibility":0.7,"source_type":"field_survey","source_title":"Northeast China MG field survey 2023","note":"感染场死淘率6-8%；健康场3-5%","production_stage":"laying","year":2023},
    {"kpi_id":"mg_prevalence_northeast_winter","species":"layer_chicken","region":"CN_north","value":85.0,"value_min":80.0,"value_max":95.0,"unit":"percent","credibility":0.85,"source_type":"epidemiology","source_title":"Northeast China poultry MG epidemiology 2022-2024","note":"冬季密闭保温换气不足是主因","production_stage":"laying","year":2023},
    {"kpi_id":"mg_lcfa_laying_recovery","species":"layer_chicken","region":"CN_north","value":7.0,"value_min":5.0,"value_max":10.0,"unit":"percentage_points","credibility":0.7,"source_type":"intervention_trial","source_title":"LCFA membrane intervention layer hen trial 2023","note":"4-6周显效；细胞膜流动性修复","production_stage":"laying","year":2023},
    {"kpi_id":"mg_lcfa_fcr_improvement","species":"layer_chicken","region":"CN_north","value":0.15,"value_min":0.10,"value_max":0.20,"unit":"ratio_improvement","credibility":0.7,"source_type":"intervention_trial","source_title":"LCFA membrane intervention layer hen trial 2023","note":"细胞膜磷脂重建→养分吸收效率提升","production_stage":"laying","year":2023},'''

if old_block in src:
    src = src.replace(old_block, new_block)
    p.write_text(src, encoding='utf-8')
    print("patched OK")
else:
    print("block not found — printing current MG section:")
    idx = src.find("MG northeast_china patch")
    print(src[idx:idx+500])
