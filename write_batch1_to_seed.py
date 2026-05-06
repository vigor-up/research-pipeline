import pathlib, sys
sys.path.insert(0, ".")
exec(open("batch1_benchmarks.py", encoding="utf-8").read())

p = pathlib.Path("local/seed_benchmarks.py")
src = p.read_text(encoding="utf-8")

# 轉成 b() 格式插入
lines = []
for r in batch1_benchmarks:
    st_map = {"baseline":"academic_background","disease_penalty":"academic_background",
              "epidemiology":"gov_stats","field_survey":"gov_stats","intervention_trial":"academic_background"}
    st = st_map.get(r.get("metric_type",""), "academic_background")
    cred = 4 if r["data_quality"]=="A" else 3
    line = (f'    b("{r["species"]}","{r["kpi_id"]}",{r["value_mid"]},"{r["unit"]}",'
            f'value_min={r["value_low"]},value_max={r["value_high"]},'
            f'region="{r["region"]}",year=2023,credibility={cred},'
            f'source_type="{st}",'
            f'source_title="{r["source"]}",'
            f'note="{r.get("notes","").replace(chr(34), chr(39))}"),')
    lines.append(line)

block = "\n# batch1 2025-05-06\nBENCHMARKS += [\n" + "\n".join(lines) + "\n]\n"

# 插在 DB 寫入引擎之前
insert_marker = "\n# ══════════════════════════════════════════════════════════════════════════════\n# DB 寫入引擎"
src = src.replace(insert_marker, block + insert_marker)
p.write_text(src, encoding="utf-8")
print(f"Inserted {len(lines)} records into seed_benchmarks.py")
