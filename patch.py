with open('local/pricing_matrix_v2.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace(
    "f'  FCR: {roi[\"fcr_base\"]} -> {roi[\"fcr_new\"]}'\n                f'({roi[\"fcr_improve_pct\"]}%)'",
    "f'  FCR: {roi.get(\"fcr_base\",\"?\")} -> {roi.get(\"fcr_new\",\"?\")} ({roi.get(\"fcr_improve_pct\",\"?\")}%)'"
)
with open('local/pricing_matrix_v2.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('done')