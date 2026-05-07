"""
MG (Mycoplasma gallisepticum) Benchmark Patch
為 research-pipeline seed_benchmarks.py 新增東北區疾病基準值
"""

# === 新增至 seed_benchmarks.py 的 MG 相關資料 ===

MG_BENCHMARKS = [
    # ── MG 感染蛋雞：產蛋率損失 ──────────────────────────────
    {
        "kpi_id": "mg_infection_laying_loss",
        "species": "layer_chicken",
        "region": "northeast_china",
        "description": "MG感染後蛋雞產蛋率損失（佔正常產蛋率百分點）",
        "benchmark_value": 10.0,          # 中位數 5~15%，取10%
        "benchmark_low": 5.0,
        "benchmark_high": 15.0,
        "unit": "percentage_points",
        "source": "field_survey_northeast_china",
        "notes": "東北冬季密閉雞舍MG陽性率>80%；感染場vs健康場產蛋率差異",
        "condition": "mg_positive_winter_housing",
        "data_quality": "A",  # 有東北實地調查數據支撐
    },
    # ── MG 感染蛋雞：FCR 惡化 ────────────────────────────────
    {
        "kpi_id": "mg_infection_fcr_penalty",
        "species": "layer_chicken",
        "region": "northeast_china",
        "description": "MG感染後蛋雞料蛋比惡化值（比健康場高出量）",
        "benchmark_value": 2.4,            # 感染場FCR中位數（健康場~2.1-2.2）
        "benchmark_low": 2.3,
        "benchmark_high": 2.5,
        "unit": "ratio_g_feed_per_g_egg",
        "source": "field_survey_northeast_china",
        "notes": "感染場FCR 2.3-2.5 vs 健康場 2.1-2.2，惡化約0.2-0.3",
        "condition": "mg_positive_winter_housing",
        "data_quality": "A",
    },
    # ── MG 感染蛋雞：死淘率上升 ──────────────────────────────
    {
        "kpi_id": "mg_infection_mortality_rise",
        "species": "layer_chicken",
        "region": "northeast_china",
        "description": "MG感染後死淘率上升（絕對百分點）",
        "benchmark_value": 3.0,            # 上升約2-5%，取3%
        "benchmark_low": 2.0,
        "benchmark_high": 5.0,
        "unit": "percentage_points",
        "source": "field_survey_northeast_china",
        "notes": "感染場死淘率6-8%；健康對照場~3-5%",
        "condition": "mg_positive_winter_housing",
        "data_quality": "B",
    },
    # ── MG 陽性率（東北冬季密閉雞舍）────────────────────────
    {
        "kpi_id": "mg_prevalence_northeast_winter",
        "species": "layer_chicken",
        "region": "northeast_china",
        "description": "東北冬季密閉雞舍MG血清陽性率",
        "benchmark_value": 85.0,           # >80%，取85%
        "benchmark_low": 80.0,
        "benchmark_high": 95.0,
        "unit": "percent",
        "source": "epidemiological_survey_northeast",
        "notes": "冬季密閉、換氣不足是主因；春秋季略低",
        "condition": "winter_closed_housing_northeast_china",
        "data_quality": "A",
    },
    # ── MG 干預後（LCFA干預）：產蛋率恢復 ───────────────────
    {
        "kpi_id": "mg_lcfa_laying_recovery",
        "species": "layer_chicken",
        "region": "northeast_china",
        "description": "LCFA細胞膜干預後產蛋率回升幅度（百分點）",
        "benchmark_value": 7.0,            # 可回復60-70%的損失
        "benchmark_low": 5.0,
        "benchmark_high": 10.0,
        "unit": "percentage_points",
        "source": "intervention_trial_data",
        "notes": "基於細胞膜流動性修復機制；4-6週顯效；非抗生素路徑",
        "condition": "lcfa_intervention_mg_challenged",
        "data_quality": "B",
    },
    # ── MG 干預後（LCFA干預）：FCR改善 ──────────────────────
    {
        "kpi_id": "mg_lcfa_fcr_improvement",
        "species": "layer_chicken",
        "region": "northeast_china",
        "description": "LCFA干預後料蛋比改善值",
        "benchmark_value": 0.15,           # FCR改善0.10-0.20
        "benchmark_low": 0.10,
        "benchmark_high": 0.20,
        "unit": "ratio_improvement",
        "source": "intervention_trial_data",
        "notes": "細胞膜磷脂重建→養分吸收效率↑→料蛋比↓",
        "condition": "lcfa_intervention_mg_challenged",
        "data_quality": "B",
    },
]

# ROI 對比計算（感染場 vs LCFA干預後）
# 假設：萬羽蛋雞、雞蛋均價 8.5元/斤、飼料均價 3.2元/kg
ROI_SCENARIO = {
    "flock_size": 10000,
    "egg_price_rmb_per_jin": 8.5,       # 0.5kg
    "feed_price_rmb_per_kg": 3.2,
    "scenario_infected": {
        "laying_rate": 0.78,             # 感染場（健康場88% - 10%損失）
        "fcr": 2.40,                     # g飼料/g蛋
        "mortality_rate": 0.07,
    },
    "scenario_lcfa_intervention": {
        "laying_rate": 0.85,             # 恢復後（+7pp）
        "fcr": 2.25,                     # 改善0.15
        "mortality_rate": 0.055,
    },
    # 每萬羽每月額外收益估算
    # 蛋重60g/枚，日產蛋率差7% × 10000羽 × 60g × 30天 × 8.5元/0.5kg
    # = 700羽/天 × 60g × 30天 × 17元/kg = 700×0.06×30×17 ≈ 21,420元/月
    "monthly_extra_egg_revenue_rmb": 21420,
    # FCR改善0.15，每羽每天採食120g，1萬羽×120g×0.15×30天×3.2元/kg
    # = 10000×0.12×0.15×30×3.2 = 17,280元/月
    "monthly_feed_saving_rmb": 17280,
    "total_monthly_benefit_rmb": 38700,  # 約3.87萬元/萬羽/月
    "lcfa_cost_per_flock_monthly_rmb": 3000,  # 添加劑成本估算（佔比約8%）
    "net_roi_per_10k_birds_monthly": 35700,
}

print("=== MG 基準值 patch 準備完成 ===")
print(f"新增 KPI 數量: {len(MG_BENCHMARKS)}")
for b in MG_BENCHMARKS:
    print(f"  - {b['kpi_id']}: {b['benchmark_value']} {b['unit']} [品質:{b['data_quality']}]")
print(f"\nROI 試算（萬羽蛋雞/月）:")
print(f"  額外產蛋收益: ¥{ROI_SCENARIO['monthly_extra_egg_revenue_rmb']:,}")
print(f"  飼料節省: ¥{ROI_SCENARIO['monthly_feed_saving_rmb']:,}")
print(f"  總效益: ¥{ROI_SCENARIO['total_monthly_benefit_rmb']:,}")
print(f"  添加劑成本: ¥{ROI_SCENARIO['lcfa_cost_per_flock_monthly_rmb']:,}")
print(f"  淨ROI: ¥{ROI_SCENARIO['net_roi_per_10k_birds_monthly']:,}")
print(f"  ROI倍數: {ROI_SCENARIO['total_monthly_benefit_rmb']/ROI_SCENARIO['lcfa_cost_per_flock_monthly_rmb']:.1f}x")
