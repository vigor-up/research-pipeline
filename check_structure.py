import pathlib, re
src = pathlib.Path('local/seed_benchmarks.py').read_text(encoding='utf-8')
# 找所有 def 函數名
fns = re.findall(r'^def (\w+)', src, re.MULTILINE)
print("functions:", fns)
# 找 BENCHMARKS 變數名
bms = re.findall(r'^(BENCHMARKS\w*)\s*=', src, re.MULTILINE)
print("benchmark vars:", bms)
# 最後20行
lines = src.splitlines()
print("\n--- last 20 lines ---")
print('\n'.join(lines[-20:]))
