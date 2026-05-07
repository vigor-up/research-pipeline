import sys, pathlib
sys.path.insert(0, str(pathlib.Path(".")))
from local.seed_benchmarks import seed, BENCHMARKS

# 讀 batch1 資料
exec(open("batch1_benchmarks.py", encoding="utf-8").read())

# 轉換 schema：value_mid -> value, value_low -> value_min, value_high -> value_max
converted = []
for r in batch1_benchmarks:
    converted.append({
        "kpi_id":        r["kpi_id"],
        "species":       r["species"],
        "region":        r["region"],
        "value":         r["value_mid"],
        "value_min":     r["value_low"],
        "value_max":     r["value_high"],
        "unit":          r["unit"],
        "credibility":   4 if r["data_quality"] == "A" else 3,
        "source_type":   r["metric_type"],
        "source_title":  r["source"],
        "note":          r.get("notes", ""),
        "production_stage": r.get("condition", ""),
        "year":          2023,
    })

# append 到 BENCHMARKS 並寫入 DB
import sqlite3, logging
logging.basicConfig(level=logging.INFO)

# 直接用 seed() 的內部邏輯寫入
src = pathlib.Path("local/seed_benchmarks.py").read_text(encoding="utf-8")

# 注入 converted 進 BENCHMARKS 再呼叫 seed
import types, importlib.util
spec = importlib.util.spec_from_file_location("sb", "local/seed_benchmarks.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

original_len = len(mod.BENCHMARKS)
mod.BENCHMARKS.extend(converted)
print(f"BENCHMARKS: {original_len} + {len(converted)} = {len(mod.BENCHMARKS)}")

# 呼叫 seed
mod.seed(dry_run=False, species_filter="")
