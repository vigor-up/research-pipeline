# -*- coding: utf-8 -*-
import subprocess, sys, logging, requests
from datetime import datetime

BASE_DIR = r'D:\LLM\workflows\research-pipeline-v2'
LOG_PATH = r'D:\LLM\workflows\research-pipeline-v2\logs\collect_all.log'
TELEGRAM_TOKEN = '8703702788:AAFKEiGmLYTAuFVG9GX-gRtVTUUyi-f_5mM'
TELEGRAM_CHAT  = 897274134

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8', errors='replace'),
        logging.StreamHandler()
    ])

def tg(msg):
    try:
        requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id': TELEGRAM_CHAT, 'text': msg, 'parse_mode': 'HTML'}, timeout=10)
    except: pass

def run(label, script, args=[]):
    logging.info(f'=== {label} 開始 ===')
    tg(f'⚙️ <b>{label}</b> 開始')
    t0 = datetime.now()
    try:
        # 用 Popen 即時串流 log，不用 capture_output
        proc = subprocess.Popen(
            [sys.executable, f'local/{script}'] + args,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace'
        )
        lines = []
        try:
            for line in proc.stdout:
                line = line.rstrip()
                logging.info(f'  [{script}] {line}')
                lines.append(line)
        except Exception:
            pass
        proc.wait(timeout=3600)  # 最多等1小時
        elapsed = int((datetime.now() - t0).total_seconds() // 60)
        tail = '\n'.join(lines[-10:]) if lines else ''
        if proc.returncode == 0:
            logging.info(f'=== {label} 完成 ({elapsed}分) ===')
            tg(f'✅ <b>{label}</b> 完成（{elapsed}分）\n{tail}')
        else:
            logging.error(f'=== {label} 失敗 returncode={proc.returncode} ===')
            tg(f'❌ <b>{label}</b> 失敗（{elapsed}分）\n{tail[-300:]}')
    except subprocess.TimeoutExpired:
        proc.kill()
        logging.error(f'=== {label} 超時（60分）===')
        tg(f'⏰ <b>{label}</b> 超時（60分），已強制終止')
    except Exception as e:
        logging.error(f'=== {label} 錯誤: {e} ===')
        tg(f'❌ <b>{label}</b> 錯誤: {e}')

def db_summary():
    """回傳DB筆數摘要"""
    try:
        import sqlite3
        conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
        total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
        today = conn.execute(
            "SELECT COUNT(*) FROM market_kpi WHERE date(collected_at)=date('now','localtime')"
        ).fetchone()[0]
        ing = conn.execute('SELECT COUNT(*) FROM ingredient_evidence').fetchone()[0]
        conn.close()
        return total, today, ing
    except Exception as e:
        logging.warning(f'DB summary: {e}')
        return 0, 0, 0

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--mode', default='full',
        choices=['full','ingredient','market','prices','raw','triggered'])
    args = p.parse_args()
    start = datetime.now()

    logging.info(f'collect_all 啟動 mode={args.mode}')
    tg(f'🚀 <b>collect_all 啟動</b> mode={args.mode} {start.strftime("%m-%d %H:%M")}')

    if args.mode in ('full', 'market'):
        run('市場KPI', 'auto_collect_v5_integrated.py', ['--mode', 'full'])

    if args.mode in ('full', 'ingredient'):
        run('原料論文', 'auto_collect_v5.py', ['--mode', 'ingredient'])

    if args.mode in ('full', 'prices'):
        run('價格入庫', 'insert_prices.py')

    # [修正] raw 模式獨立，不再包含在 full 裡
    # 由 GitHub Actions webhook 觸發，避免時間差拉到舊資料
    if args.mode == 'raw':
        run('R2處理', 'process_raw.py')

    if args.mode == 'triggered':
        run('ChangeDetection觸發', 'auto_collect_v5_integrated.py', ['--mode', 'triggered'])

    # 完成摘要
    elapsed = int((datetime.now() - start).total_seconds() // 60)
    total, today, ing = db_summary()
    tg(
        f'🏁 <b>collect_all 完成</b>\n'
        f'耗時: {elapsed}分\n'
        f'市場KPI總計: {total}筆（今日新增: {today}）\n'
        f'原料論文: {ing}筆'
    )
    logging.info(f'collect_all 完成 耗時{elapsed}分')
