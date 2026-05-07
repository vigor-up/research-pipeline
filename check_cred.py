from local.seed_benchmarks import BENCHMARKS
vals = set(r.get("credibility") for r in BENCHMARKS)
print("credibility values in use:", sorted(vals))
