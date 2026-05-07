import pathlib, sqlite3, logging
from local.seed_benchmarks import seed, BENCHMARKS

# 確認 seed() 簽名需要什麼參數
import inspect
print(inspect.signature(seed))
