content = open('local/tg_webhook_server.py', encoding='utf-8').read()

species_map = """
SPECIES_MAP = {
    '肉牛': 'beef_cattle', '牛': 'beef_cattle',
    '育肥豬': 'finisher_pig', '豬': 'finisher_pig', '肉豬': 'finisher_pig',
    '肉羊': 'meat_sheep', '羊': 'meat_sheep',
    '肉雞': 'broiler', '雞': 'broiler',
    '蛋雞': 'layer_chicken', '蛋': 'layer_chicken',
    '肉鴨': 'duck', '鴨': 'duck',
    '母豬': 'lactating_sow', '哺乳母豬': 'lactating_sow',
    '奶牛': 'dairy_cow',
    '白蝦': 'shrimp', '蝦': 'shrimp',
}
PRODUCT_MAP = {
    '蛋白酶': 'bacillus_protease', '枯草菌': 'bacillus_protease', '活力得': 'bacillus_protease',
    '蝦青素': 'astaxanthin', '二十八烷醇': 'octacosanol', '八烷醇': 'octacosanol',
}
def translate_args(args):
    return [SPECIES_MAP.get(a, PRODUCT_MAP.get(a, a)) for a in args]
"""

# 插入在COMMANDS之前
content = content.replace("COMMANDS = {", species_map + "\nCOMMANDS = {")

# 兩個handler(args)呼叫都加translate
content = content.replace(
    "                    handler(args)\n                        except TypeError:",
    "                    handler(translate_args(args))\n                        except TypeError:"
)
# polling的handler
old = "                    if handler:\n                        try:\n                            handler(args)\n                        except TypeError:\n                            handler()"
new = "                    if handler:\n                        try:\n                            handler(translate_args(args))\n                        except TypeError:\n                            handler()"
content = content.replace(old, new)

open('local/tg_webhook_server.py', 'w', encoding='utf-8').write(content)

import ast
ast.parse(content)
print('done, syntax ok')
