import pathlib, sys
sys.path.insert(0, ".")
exec(open("batch2_benchmarks.py", encoding="utf-8").read())

p = pathlib.Path("local/seed_benchmarks.py")
src = p.read_text(encoding="utf-8")

st_map = {"baseline":"academic_background","disease_penalty":"academic_background",
          "epidemiology":"gov_stats","field_survey":"gov_stats"}

lines = []
for r in batch2_benchmarks:
    st = st_map.get(r.get("metric_type",""), "academic_background")
    cred = 4 if r["data_quality"]=="A" else 3
    note = r.get("notes","").replace('"',"'")
    line = (f'    b("{r["species"]}","{r["kpi_id"]}",{r["value_mid"]},"{r["unit"]}",'
            f'value_min={r["value_low"]},value_max={r["value_high"]},'
            f'region="{r["region"]}",year=2023,credibility={cred},'
            f'source_type="{st}",source_title="{r["source"]}",note="{note}"),')
    lines.append(line)

block = "\n# batch2 2026-05-06\nBENCHMARKS += [\n" + "\n".join(lines) + "\n]\n"
insert_marker = "\n# batch1 2025-05-06"
if insert_marker in src:
    src = src.replace(insert_marker, block + insert_marker)
else:
    src = src.rstrip() + "\n" + block
p.write_text(src, encoding="utf-8")
print(f"Inserted {len(lines)} batch2 records")
