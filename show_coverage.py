lines = open('check_coverage.py', encoding='utf-8').readlines()
for i, l in enumerate(lines):
    print(f"{i+1}: {l}", end='')
