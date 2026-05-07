# -*- coding: utf-8 -*-
"""
tg_webhook_server.py
EVO-X2 常駐服務：接收 GitHub Actions / Telegram 指令
自動觸發 auto_collect_v4 / pricing_matrix / formula_advisor
port: 8766
"""

import html, json, logging, re, subprocess, threading, requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import sys, os

TELEGRAM_TOKEN = '8703702788:AAFKEiGmLYTAuFVG9GX-gRtVTUUyi-f_5mM'
TELEGRAM_CHAT  = 897274134
BASE_DIR       = r'D:\LLM\workflows\research-pipeline-v2'
LOG_PATH       = r'D:\LLM\workflows\research-pipeline-v2\logs\webhook.log'
WEBHOOK_PORT   = 8766
WEBHOOK_SECRET = 'vigor_up_2026'  # GitHub Actions 用這個驗證

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def tg(msg):
    try:
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id': TELEGRAM_CHAT, 'text': msg, 'parse_mode': 'HTML'},
            timeout=10)
    except Exception as e:
        logging.warning(f'TG: {e}')

def run_script(script, args=[], label=''):
    """背景執行腳本，結果推送 Telegram"""
    def _run():
        cmd = [sys.executable, f'local/{script}'] + args
        logging.info(f'Running: {" ".join(cmd)}')
        tg(f'⚙️ 開始執行: {label or script}')
        try:
            result = subprocess.run(
                cmd, cwd=BASE_DIR,
                capture_output=True, text=True,
                encoding='utf-8', timeout=3600)
            output = result.stdout[-2000:] if result.stdout else ''
            error  = result.stderr[-500:]  if result.stderr else ''
            if result.returncode == 0:
                tg(f'✅ <b>{label or script} 完成</b>\n{output}')
            else:
                tg(f'❌ <b>{label or script} 失敗</b>\n{error}')
        except subprocess.TimeoutExpired:
            tg(f'⏰ {label} 超時（1小時）')
        except Exception as e:
            tg(f'❌ {label} 執行錯誤: {e}')
    threading.Thread(target=_run, daemon=True).start()

# ── 指令路由 ────────────────────────────────────────────

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

COMMANDS = {
    # GitHub Actions 觸發
    'collect':      lambda: run_script('auto_collect_v4.py', [], '自動收集v4'),
    'price_update': lambda: run_script('price_collector.py', [], '價格更新'),
    'db_quality':   lambda: run_script('db_quality_fix.py',  [], 'DB品質修正'),

    # Telegram Bot 指令
    '/v5':          lambda args: run_script(
                        'auto_collect_v5.py',
                        ['--mode', 'single',
                         '--species', args[0] if args else 'finisher_pig',
                         '--region',  args[1] if len(args)>1 else 'CN_northeast'],
                        'v5單物種收集'),
    '/roi':         lambda args: run_script(
                        'pricing_matrix_v2.py',
                        ['--region', args[0] if args else 'CN_northeast', '--telegram'],
                        'ROI定價矩陣'),
    '/formula':     lambda args: run_script(
                        'formula_advisor.py',
                        ['--species', args[0] if args else 'finisher_pig',
                         '--product', args[1] if len(args)>1 else 'bacillus_protease',
                         '--telegram'],
                        '配方建議'),
    '/market':      lambda args: run_script(
                        'pricing_matrix_v2.py',
                        ['--region', 'CN_northeast', '--telegram'],
                        '東北市場報告'),
    '/status':      lambda args: send_status(),
    '/help':        lambda args: tg(HELP_TEXT),
}

HELP_TEXT = """🤖 <b>EVO-X2 指令中心</b>

<b>市場數據</b>
/roi [區域] — 定價矩陣（預設東北）
/market — 東北市場概況
/formula [物種] [產品] — 配方建議

<b>系統指令</b>
/status — 系統狀態
/collect — 手動觸發收集
/price_update — 更新今日價格

<b>物種代碼</b>
finisher_pig / beef_cattle / layer_chicken
broiler / meat_sheep / lactating_sow

<b>產品代碼</b>
vitalboost_growth（肥力寶）
vitalboost_repro（活力旺）"""

def send_status():
    import sqlite3
    try:
        conn = sqlite3.connect(r'D:\LLM\knowledge\market\market_data.db')
        total = conn.execute('SELECT COUNT(*) FROM market_kpi').fetchone()[0]
        conf  = conn.execute('SELECT COUNT(*) FROM market_kpi WHERE confirmed=1').fetchone()[0]
        ne    = conn.execute("SELECT COUNT(*) FROM market_kpi WHERE region='CN_northeast'").fetchone()[0]
        conn.close()
        tg(f'📊 <b>EVO-X2 系統狀態</b>\n'
           f'DB: {total}筆（✅{conf} / ⏳{total-conf}）\n'
           f'東北數據: {ne}筆\n'
           f'MCP Server: port 8765\n'
           f'Webhook: port 8766\n'
           f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    except Exception as e:
        tg(f'❌ 狀態查詢失敗: {e}')

# ── HTTP Server ─────────────────────────────────────────
class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logging.info(f'HTTP {format % args}')

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/health':
            self.send_json({'status': 'ok', 'server': 'evo-x2-webhook'})
        else:
            self.send_json({'error': 'not found'}, 404)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length)
        try:
            data = json.loads(body)
        except Exception:
            self.send_json({'error': 'invalid json'}, 400)
            return

        # ── GitHub Actions 觸發 ──────────────────────────
        if self.path == '/webhook/github':
            secret = self.headers.get('X-Webhook-Secret', '')
            if secret != WEBHOOK_SECRET:
                self.send_json({'error': 'unauthorized'}, 401)
                return
            action = data.get('action', '')
            handler = COMMANDS.get(action)
            if handler:
                handler()
                self.send_json({'status': 'triggered', 'action': action})
                logging.info(f'GitHub webhook: {action}')
            else:
                self.send_json({'error': f'unknown action: {action}'}, 400)

        # ── Telegram Bot 更新 ────────────────────────────
        elif self.path == '/webhook/telegram':
            message = data.get('message', {})
            text    = message.get('text', '').strip()
            chat_id = message.get('chat', {}).get('id')

            if chat_id != TELEGRAM_CHAT:
                self.send_json({'status': 'ignored'})
                return

            parts   = text.split()
            cmd     = parts[0].lower() if parts else ''
            args    = parts[1:] if len(parts) > 1 else []

            handler = COMMANDS.get(cmd)
            if handler:
                try:
                    handler(args)
                except TypeError:
                    handler()
                self.send_json({'status': 'ok'})
            else:
                tg(f'❓ 未知指令: {cmd}\n輸入 /help 查看說明')
                self.send_json({'status': 'unknown_command'})

        elif self.path == '/webhook':
            title = html.escape(data.get('title', 'ChangeDetection通知'))
            raw = re.sub(r'<[^>]+>', '', str(data.get('message', ''))).strip()
            diff = html.escape(raw[:400])
            msg = f'🔔 <b>頁面變更</b>\n<b>{title}</b>\n\n{diff}'
            tg(msg)
            self.send_json({'status': 'ok'})
            logging.info(f'ChangeDetection: {title}')

        elif self.path == '/webhook':
            title = html.escape(data.get('title', 'ChangeDetection通知'))
            raw = re.sub(r'<[^>]+>', '', str(data.get('message', ''))).strip()
            diff = html.escape(raw[:400])
            msg = f'🔔 <b>頁面變更</b>\n<b>{title}</b>\n\n{diff}'
            tg(msg)
            self.send_json({'status': 'ok'})
            logging.info(f'ChangeDetection: {title}')

        else:
            self.send_json({'error': 'unknown path'}, 404)

# ── Telegram 長輪詢（備用，不需要公網IP）────────────────
def telegram_polling():
    """當沒有公網IP時，用長輪詢接收Telegram指令"""
    offset = 0
    logging.info('Telegram polling started')
    while True:
        try:
            resp = requests.get(
                f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates',
                params={'offset': offset, 'timeout': 30},
                timeout=35)
            if resp.ok:
                updates = resp.json().get('result', [])
                for upd in updates:
                    offset = upd['update_id'] + 1
                    msg    = upd.get('message', {})
                    text   = msg.get('text', '').strip()
                    chat_id = msg.get('chat', {}).get('id')

                    if chat_id != TELEGRAM_CHAT or not text:
                        continue

                    logging.info(f'TG msg: {text}')
                    parts = text.split()
                    cmd   = parts[0].lower()
                    args  = parts[1:] if len(parts) > 1 else []

                    handler = COMMANDS.get(cmd)
                    if handler:
                        try:
                            handler(translate_args(args))
                        except TypeError:
                            handler()
                    else:
                        tg(f'❓ 未知指令: {cmd}\n輸入 /help 查看說明')
        except Exception as e:
            logging.warning(f'Polling error: {e}')
            import time; time.sleep(5)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', default='polling',
                        choices=['polling', 'webhook'],
                        help='polling=長輪詢（無需公網IP），webhook=需要公網IP')
    parser.add_argument('--port', type=int, default=WEBHOOK_PORT)
    args = parser.parse_args()

    tg(f'🚀 <b>EVO-X2 Webhook Server 啟動</b>\n'
       f'模式: {args.mode}\n'
       f'輸入 /help 查看指令')

    if args.mode == 'webhook':
        # 同時啟動 HTTP server 和 Telegram polling
        poll_thread = threading.Thread(target=telegram_polling, daemon=True)
        poll_thread.start()
        server = HTTPServer(('0.0.0.0', args.port), WebhookHandler)
        logging.info(f'Webhook server on port {args.port}')
        server.serve_forever()
    else:
        # 純輪詢模式（推薦，無需公網IP）
        server_thread = threading.Thread(
            target=lambda: HTTPServer(('localhost', args.port),
                                       WebhookHandler).serve_forever(),
            daemon=True)
        server_thread.start()
        logging.info(f'Local webhook on port {args.port}')
        telegram_polling()

