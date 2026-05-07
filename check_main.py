import pathlib
src = pathlib.Path('local/seed_benchmarks.py').read_text(encoding='utf-8')
# 找 if __name__ 區塊
idx = src.find('if __name__')
print(src[idx:idx+300] if idx >= 0 else "NO __main__ block found")
