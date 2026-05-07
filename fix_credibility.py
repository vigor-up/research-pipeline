import pathlib, re

# 修 import_batch1.py 的 credibility 轉換
p = pathlib.Path("import_batch1.py")
src = p.read_text(encoding="utf-8")
src = src.replace(
    '"credibility":   0.8 if r["data_quality"] == "A" else 0.65,',
    '"credibility":   4 if r["data_quality"] == "A" else 3,'
)
p.write_text(src, encoding="utf-8")
print("import_batch1.py patched")

# 修 seed_benchmarks.py 裡 MG patch 的 credibility 值
p2 = pathlib.Path("local/seed_benchmarks.py")
src2 = p2.read_text(encoding="utf-8")
src2 = src2.replace('"credibility":0.8,', '"credibility":4,')
src2 = src2.replace('"credibility":0.85,', '"credibility":4,')
src2 = src2.replace('"credibility":0.7,', '"credibility":3,')
p2.write_text(src2, encoding="utf-8")
print("seed_benchmarks.py MG credibility patched")
