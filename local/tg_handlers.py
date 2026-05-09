# tg_handlers.py
import sys
sys.path.insert(0, r'D:\LLM\workflows\research-pipeline-v2\local')

def handle_ask(tg_func, args):
    """統一入口：自然語言問題，自動路由+補收"""
    if not args:
        tg_func('直接問我問題就好，例如：東北肉雞FCR多少？')
        return
    question = ' '.join(args)
    tg_func(f'🔍 查詢中: {question}')
    try:
        from smart_query import smart_query
        result = smart_query(question)
        tg_func(str(result)[:1500])
    except Exception as e:
        tg_func(f'❌ 錯誤: {e}')

# /compare /defense 都是 handle_ask 的別名
def handle_compare(tg_func, args):
    if len(args) < 3:
        tg_func('用法: /compare 豬 FCR 東北 華北\n或直接問：東北和華北豬FCR哪個高？')
        return
    species = args[0]; kpi = args[1]; regions = ' 和 '.join(args[2:])
    handle_ask(tg_func, [f'{regions} {species} {kpi} 比較'])

def handle_defense(tg_func, args):
    if not args:
        tg_func('用法: /defense astaxanthin\n或直接問：astaxanthin有什麼學術證據？')
        return
    handle_ask(tg_func, args + ['動物營養學術研究證據'])
