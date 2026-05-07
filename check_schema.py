import sqlite3, re, pathlib

# 從 seed_benchmarks.py 找 CREATE TABLE 語句
src = pathlib.Path("local/seed_benchmarks.py").read_text(encoding="utf-8")
idx = src.find("CREATE TABLE")
print(src[idx:idx+1500])
