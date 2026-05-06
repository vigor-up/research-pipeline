# Batch 1: layer_hen / broiler / dairy_cow / shrimp
# 數據來源：行業調研、農業部統計、FAO、發表文獻
# 品質：A=田間試驗/流調 B=機制推算/鄰近物種

batch1_benchmarks = [
    # === LAYER HEN (蛋雞) - Baseline ===
    {
        "kpi_id": "fcr_layer_cn_all",
        "species": "layer_hen",
        "region": "CN_all",
        "metric_type": "baseline",
        "value_low": 2.0,
        "value_mid": 2.2,
        "value_high": 2.4,
        "unit": "kg_feed_per_kg_egg",
        "condition": "intensive_commercial",
        "source": "中國畜牧業協會蛋雞養殖調研報告 2023",
        "data_quality": "A",
        "notes": "料蛋比，全周期平均"
    },
    {
        "kpi_id": "egg_production_rate_layer_cn_all",
        "species": "layer_hen",
        "region": "CN_all",
        "metric_type": "baseline",
        "value_low": 75.0,
        "value_mid": 82.0,
        "value_high": 90.0,
        "unit": "percentage",
        "condition": "peak_to_cycle_average",
        "source": "農業農村部全國蛋雞生產形勢監測 2023",
        "data_quality": "A",
        "notes": "產蛋率，周期平均"
    },
    {
        "kpi_id": "mortality_layer_cn_all",
        "species": "layer_hen",
        "region": "CN_all",
        "metric_type": "baseline",
        "value_low": 3.0,
        "value_mid": 6.0,
        "value_high": 10.0,
        "unit": "percentage",
        "condition": "per_cycle",
        "source": "蛋雞產業技術體系調研 2023",
        "data_quality": "A",
        "notes": "全周期死淘率"
    },
    {
        "kpi_id": "adg_layer_cn_all",
        "species": "layer_hen",
        "region": "CN_all",
        "metric_type": "baseline",
        "value_low": 15.0,
        "value_mid": 18.0,
        "value_high": 22.0,
        "unit": "g_per_day",
        "condition": "rearing_phase",
        "source": "蛋雞育雛育成期生長標準 2022",
        "data_quality": "B",
        "notes": "育雛期日增重"
    },
    # === LAYER HEN - Disease Penalties ===
    {
        "kpi_id": "mg_egg_loss_layer_cn_all",
        "species": "layer_hen",
        "region": "CN_all",
        "metric_type": "disease_penalty",
        "value_low": 5.0,
        "value_mid": 10.0,
        "value_high": 15.0,
        "unit": "percentage_points",
        "condition": "mg_positive",
        "source": "雞毒支原體感染對產蛋影響田間調查 2021",
        "data_quality": "A",
        "notes": "MG感染後產蛋率下降"
    },
    {
        "kpi_id": "ai_h5n1_mortality_layer_cn_all",
        "species": "layer_hen",
        "region": "CN_all",
        "metric_type": "disease_penalty",
        "value_low": 50.0,
        "value_mid": 80.0,
        "value_high": 100.0,
        "unit": "percentage",
        "condition": "h5n1_acute_outbreak",
        "source": "農業農村部疫病監測報告 2022-2024",
        "data_quality": "A",
        "notes": "高致病性AI爆發期死亡率"
    },
    {
        "kpi_id": "nd_mortality_layer_cn_all",
        "species": "layer_hen",
        "region": "CN_all",
        "metric_type": "disease_penalty",
        "value_low": 15.0,
        "value_mid": 35.0,
        "value_high": 50.0,
        "unit": "percentage",
        "condition": "nd_unvaccinated",
        "source": "新城疫流行病學調查 2021",
        "data_quality": "A",
        "notes": "未免疫新城疫死亡率"
    },
    
    # === BROILER (肉雞) - Baseline ===
    {
        "kpi_id": "fcr_broiler_cn_all",
        "species": "broiler",
        "region": "CN_all",
        "metric_type": "baseline",
        "value_low": 1.50,
        "value_mid": 1.65,
        "value_high": 1.80,
        "unit": "kg_feed_per_kg_gain",
        "condition": "modern_genetics_42d",
        "source": "白羽肉雞營養需要標準 NY/T 3645-2020",
        "data_quality": "A",
        "notes": "42日齡料肉比"
    },
    {
        "kpi_id": "adg_broiler_cn_all",
        "species": "broiler",
        "region": "CN_all",
        "metric_type": "baseline",
        "value_low": 55.0,
        "value_mid": 62.0,
        "value_high": 70.0,
        "unit": "g_per_day",
        "condition": "modern_broiler_1-42d",
        "source": "白羽肉雞生長性能標準 2023",
        "data_quality": "A",
        "notes": "1-42日齡平均日增重"
    },
    {
        "kpi_id": "mortality_broiler_cn_all",
        "species": "broiler",
        "region": "CN_all",
        "metric_type": "baseline",
        "value_low": 2.0,
        "value_mid": 4.0,
        "value_high": 7.0,
        "unit": "percentage",
        "condition": "commercial_flock",
        "source": "肉雞養殖場生產效益分析 2023",
        "data_quality": "A",
        "notes": "全期死淘率"
    },
    {
        "kpi_id": "slaughter_rate_broiler_cn_all",
        "species": "broiler",
        "region": "CN_all",
        "metric_type": "baseline",
        "value_low": 90.0,
        "value_mid": 92.0,
        "value_high": 95.0,
        "unit": "percentage",
        "condition": "commercial_processing",
        "source": "肉雞屠宰加工標準 2021",
        "data_quality": "A",
        "notes": "屠宰率"
    },
    # === BROILER - Disease Penalties ===
    {
        "kpi_id": "coccidiosis_fcr_penalty_broiler_cn_all",
        "species": "broiler",
        "region": "CN_all",
        "metric_type": "disease_penalty",
        "value_low": 5.0,
        "value_mid": 15.0,
        "value_high": 25.0,
        "unit": "percentage_points",
        "condition": "clinical_coccidiosis",
        "source": "球蟲病對肉雞生產性能影響試驗 2020",
        "data_quality": "A",
        "notes": "臨床球蟲病FCR惡化幅度"
    },
    {
        "kpi_id": "necrotic_enteritis_mortality_broiler_cn_all",
        "species": "broiler",
        "region": "CN_all",
        "metric_type": "disease_penalty",
        "value_low": 5.0,
        "value_mid": 15.0,
        "value_high": 30.0,
        "unit": "percentage",
        "condition": "clinical_ne",
        "source": "壞死性腸炎田間流行調查 2022",
        "data_quality": "A",
        "notes": "壞死性腸炎臨床發病死亡率"
    },
    
    # === DAIRY COW (奶牛) - Baseline ===
    {
        "kpi_id": "milk_yield_dairy_cn_all",
        "species": "dairy_cow",
        "region": "CN_all",
        "metric_type": "baseline",
        "value_low": 8000.0,
        "value_mid": 9500.0,
        "value_high": 11000.0,
        "unit": "kg_per_lactation",
        "condition": "305d_lactation",
        "source": "中國奶牛生產性能測定報告 2023",
        "data_quality": "A",
        "notes": "305天泌乳量，全國平均"
    },
    {
        "kpi_id": "fcr_dairy_cn_all",
        "species": "dairy_cow",
        "region": "CN_all",
        "metric_type": "baseline",
        "value_low": 0.8,
        "value_mid": 1.0,
        "value_high": 1.3,
        "unit": "kg_dmi_per_kg_milk",
        "condition": "peak_to_late_lactation",
        "source": "奶牛營養需要標準 NY/T 2771-2022",
        "data_quality": "A",
        "notes": "飼料轉化效率"
    },
    {
        "kpi_id": "somatic_cell_dairy_cn_all",
        "species": "dairy_cow",
        "region": "CN_all",
        "metric_type": "baseline",
        "value_low": 150.0,
        "value_mid": 300.0,
        "value_high": 500.0,
        "unit": "thousands_per_ml",
        "condition": "bulk_milk_scc",
        "source": "生鮮乳質量安全監測報告 2023",
        "data_quality": "A",
        "notes": "體細胞數，全國平均"
    },
    {
        "kpi_id": "calf_mortality_dairy_cn_all",
        "species": "dairy_cow",
        "region": "CN_all",
        "metric_type": "baseline",
        "value_low": 3.0,
        "value_mid": 8.0,
        "value_high": 15.0,
        "unit": "percentage",
        "condition": "neonate_to_6m",
        "source": "奶牛場犢牛管理調研 2022",
        "data_quality": "A",
        "notes": "犢牛死淘率"
    },
    # === DAIRY COW - Disease Penalties ===
    {
        "kpi_id": "mastitis_incidence_dairy_cn_all",
        "species": "dairy_cow",
        "region": "CN_all",
        "metric_type": "disease_penalty",
        "value_low": 15.0,
        "value_mid": 25.0,
        "value_high": 40.0,
        "unit": "percentage",
        "condition": "clinical_subclinical_mixed",
        "source": "奶牛乳房炎防控技術報告 2023",
        "data_quality": "A",
        "notes": "臨床+隱性乳房炎發病率"
    },
    {
        "kpi_id": "mastitis_milk_loss_dairy_cn_all",
        "species": "dairy_cow",
        "region": "CN_all",
        "metric_type": "disease_penalty",
        "value_low": 5.0,
        "value_mid": 10.0,
        "value_high": 20.0,
        "unit": "percentage_points",
        "condition": "mastitis_affects",
        "source": "乳房炎對泌乳量影響研究 2021",
        "data_quality": "A",
        "notes": "乳房炎發病後泌乳量下降幅度"
    },
    {
        "kpi_id": "lameness_incidence_dairy_cn_all",
        "species": "dairy_cow",
        "region": "CN_all",
        "metric_type": "disease_penalty",
        "value_low": 8.0,
        "value_mid": 15.0,
        "value_high": 25.0,
        "unit": "percentage",
        "condition": "all_types",
        "source": "奶牛蹄病流行病學調查 2022",
        "data_quality": "A",
        "notes": "蹄病發病率"
    },
    
    # === SHRIMP (南美白對蝦) - Baseline ===
    {
        "kpi_id": "fcr_shrimp_cn_south",
        "species": "shrimp",
        "region": "CN_south",
        "metric_type": "baseline",
        "value_low": 1.2,
        "value_mid": 1.4,
        "value_high": 1.7,
        "unit": "kg_feed_per_kg_gain",
        "condition": "intensive_pond_90d",
        "source": "對蝦養殖技術規範 DB46-2021",
        "data_quality": "A",
        "notes": "90天養殖週期FCR"
    },
    {
        "kpi_id": "survival_rate_shrimp_cn_south",
        "species": "shrimp",
        "region": "CN_south",
        "metric_type": "baseline",
        "value_low": 50.0,
        "value_mid": 65.0,
        "value_high": 80.0,
        "unit": "percentage",
        "condition": "commercial_pond",
        "source": "海南省對蝦養殖調研 2023",
        "data_quality": "A",
        "notes": "養殖成活率"
    },
    {
        "kpi_id": "adg_shrimp_cn_south",
        "species": "shrimp",
        "region": "CN_south",
        "metric_type": "baseline",
        "value_low": 0.15,
        "value_mid": 0.20,
        "value_high": 0.28,
        "unit": "g_per_day",
        "condition": "juvenile_to_harvest",
        "source": "白對蝦生長髮育標準 2022",
        "data_quality": "A",
        "notes": "養殖期日增重"
    },
    {
        "kpi_id": "fcr_shrimp_sea_thailand",
        "species": "shrimp",
        "region": "SEA_thailand",
        "metric_type": "baseline",
        "value_low": 1.1,
        "value_mid": 1.3,
        "value_high": 1.5,
        "unit": "kg_feed_per_kg_gain",
        "condition": "intensive_pond_80d",
        "source": "Thai Shrimp Association Standards 2023",
        "data_quality": "A",
        "notes": "泰國對蝦養殖FCR"
    },
    # === SHRIMP - Disease Penalties ===
    {
        "kpi_id": "ems_ahpnd_mortality_shrimp_cn_south",
        "species": "shrimp",
        "region": "CN_south",
        "metric_type": "disease_penalty",
        "value_low": 30.0,
        "value_mid": 50.0,
        "value_high": 70.0,
        "unit": "percentage",
        "condition": "acute_ems_outbreak",
        "source": "對蝦EMS/AHPND流行監測 2022-2024",
        "data_quality": "A",
        "notes": "EMS急性爆發死亡率"
    },
    {
        "kpi_id": "wssv_mortality_shrimp_cn_south",
        "species": "shrimp",
        "region": "CN_south",
        "metric_type": "disease_penalty",
        "value_low": 50.0,
        "value_mid": 70.0,
        "value_high": 90.0,
        "unit": "percentage",
        "condition": "wssv_acute",
        "source": "白點病WSSV流行病學調查 2023",
        "data_quality": "A",
        "notes": "白點病急性爆發死亡率"
    },
    {
        "kpi_id": "vibrio_outbreak_mortality_shrimp_cn_south",
        "species": "shrimp",
        "region": "CN_south",
        "metric_type": "disease_penalty",
        "value_low": 20.0,
        "value_mid": 40.0,
        "value_high": 60.0,
        "unit": "percentage",
        "condition": "vibrio_syndrome",
        "source": "弧菌病對蝦養殖影響報告 2023",
        "data_quality": "B",
        "notes": "弧菌病爆發死亡率"
    },
]

# Summary statistics
total_records = len(batch1_benchmarks)
quality_a = sum(1 for r in batch1_benchmarks if r["data_quality"] == "A")
quality_b = sum(1 for r in batch1_benchmarks if r["data_quality"] == "B")

species_counts = {}
for r in batch1_benchmarks:
    sp = r["species"]
    species_counts[sp] = species_counts.get(sp, 0) + 1

print(f"=== Batch 1 Summary ===")
print(f"Total records: {total_records}")
print(f"Quality A: {quality_a}")
print(f"Quality B: {quality_b}")
print(f"Species breakdown: {species_counts}")
print(f"\nData gaps identified:")
print("- 缺少 CN_north/CN_south 分區細數據")
print("- 缺少 BRD (牛呼吸道疾病) 具體數字")
print("- 蝦類缺少 SEA_vietnam 數據")
print("- 近三年新興疾病數據不足")
