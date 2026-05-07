# -*- coding: utf-8 -*-
"""
scrapling_mcp_server.py
Scrapling MCP Server - 讓 Qwen3.6 透過 MCP 協議直接呼叫
啟動：python scrapling_mcp_server.py
端口：預設 8765
QClaw 設定：在 openclaw.json 的 mcpServers 加入此服務
"""

import json, logging, asyncio, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import threading

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s')

# ── Scrapling 工具定義 ─────────────────────────────────
TOOLS = [
    {
        "name": "scrape_url",
        "description": "抓取指定URL的完整頁面文字內容。適合用於：農業行情頁面、學術論文摘要、行業報告、競品網站。會自動處理JavaScript渲染。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要抓取的網頁URL"
                },
                "mode": {
                    "type": "string",
                    "enum": ["fast", "stealth"],
                    "description": "fast=普通頁面，stealth=有反爬蟲的頁面（預設fast）",
                    "default": "fast"
                },
                "max_chars": {
                    "type": "integer",
                    "description": "回傳最大字元數（預設5000）",
                    "default": 5000
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "scrape_price_page",
        "description": "專門抓取農業現貨價格頁面，自動提取表格數據。適合：搜豬網、新牧網、水產門戶、飼料行業網等價格頁面。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "價格頁面URL"
                },
                "species": {
                    "type": "string",
                    "description": "物種（如 finisher_pig, layer_chicken, beef_cattle, shrimp）"
                }
            },
            "required": ["url", "species"]
        }
    },
    {
        "name": "search_and_scrape",
        "description": "Tavily搜索後自動抓取最相關的頁面全文。一步完成搜索+抓取。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查詢字串"
                },
                "max_results": {
                    "type": "integer",
                    "description": "抓取前幾個結果（預設3）",
                    "default": 3
                }
            },
            "required": ["query"]
        }
    }
]

# ── 工具執行 ───────────────────────────────────────────
def execute_scrape_url(url, mode='fast', max_chars=5000):
    try:
        from scrapling import Fetcher, StealthyFetcher
        if mode == 'stealth':
            page = StealthyFetcher.fetch(url, headless=True, timeout=30)
        else:
            fetcher = Fetcher(auto_match=False)
            page = fetcher.get(url, timeout=20)
        text = page.get_all_text(
            ignore_tags=('script','style','nav','footer','header','aside'))
        text = ' '.join(text.split())  # 清理空白
        return {
            'success': True,
            'url': url,
            'char_count': len(text),
            'content': text[:max_chars]
        }
    except Exception as e:
        # fallback: requests
        try:
            import requests
            r = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            })
            text = r.text[:max_chars]
            return {'success': True, 'url': url,
                    'char_count': len(text), 'content': text,
                    'note': f'scrapling failed, used requests fallback: {e}'}
        except Exception as e2:
            return {'success': False, 'url': url, 'error': str(e2)}

def execute_scrape_price_page(url, species):
    result = execute_scrape_url(url, mode='fast', max_chars=6000)
    if not result['success']:
        return result
    # 附加 species 標記方便 Qwen 後續抽取
    result['species'] = species
    result['hint'] = f'請從以上內容中抽取 {species} 的現貨價格數據（元/斤或元/kg）'
    return result

def execute_search_and_scrape(query, max_results=3):
    import os, requests as req

    # 讀 Tavily key
    tavily_key = None
    try:
        for enc in ('utf-8-sig', 'utf-8', 'cp950'):
            try:
                with open(r'D:\LLM\API key.txt', encoding=enc) as f:
                    for line in f:
                        if 'TAVILY' in line.upper():
                            tavily_key = line.split('=')[-1].strip().strip('"\'')
                            break
                if tavily_key:
                    break
            except Exception:
                continue
    except Exception:
        pass

    if not tavily_key:
        return {'success': False, 'error': 'Tavily key not found'}

    # Tavily 搜索
    try:
        resp = req.post('https://api.tavily.com/search', json={
            'api_key': tavily_key,
            'query': query,
            'max_results': max_results,
            'search_depth': 'advanced',
            'include_raw_content': True,
        }, timeout=30)
        results = resp.json().get('results', [])
    except Exception as e:
        return {'success': False, 'error': f'Tavily failed: {e}'}

    # 抓取每個結果
    scraped = []
    for r in results[:max_results]:
        url   = r.get('url', '')
        title = r.get('title', '')
        raw   = r.get('raw_content', '') or ''

        if len(raw) < 300:
            sr = execute_scrape_url(url, max_chars=4000)
            content = sr.get('content', '') if sr['success'] else raw
        else:
            content = raw[:4000]

        scraped.append({
            'url': url,
            'title': title,
            'content': content
        })

    return {
        'success': True,
        'query': query,
        'results': scraped
    }

TOOL_HANDLERS = {
    'scrape_url':          lambda p: execute_scrape_url(
                               p['url'], p.get('mode','fast'), p.get('max_chars',5000)),
    'scrape_price_page':   lambda p: execute_scrape_price_page(
                               p['url'], p['species']),
    'search_and_scrape':   lambda p: execute_search_and_scrape(
                               p['query'], p.get('max_results',3)),
}

# ── MCP HTTP Server ────────────────────────────────────
class MCPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logging.info(f'MCP {self.address_string()} {format % args}')

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/health':
            self.send_json({'status': 'ok', 'server': 'scrapling-mcp'})
        elif path == '/tools':
            self.send_json({'tools': TOOLS})
        else:
            self.send_json({'error': 'Not found'}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        try:
            req = json.loads(body)
        except Exception:
            self.send_json({'error': 'Invalid JSON'}, 400)
            return

        # MCP 標準端點
        if path == '/':
            self._handle_mcp(req)
        elif path == '/call':
            self._handle_call(req)
        else:
            self.send_json({'error': 'Not found'}, 404)

    def _handle_mcp(self, req):
        """標準 MCP JSON-RPC 2.0"""
        method = req.get('method', '')
        req_id = req.get('id')

        if method == 'initialize':
            self.send_json({
                'jsonrpc': '2.0', 'id': req_id,
                'result': {
                    'protocolVersion': '2024-11-05',
                    'capabilities': {'tools': {}},
                    'serverInfo': {
                        'name': 'scrapling-mcp',
                        'version': '1.0.0'
                    }
                }
            })

        elif method == 'tools/list':
            self.send_json({
                'jsonrpc': '2.0', 'id': req_id,
                'result': {'tools': TOOLS}
            })

        elif method == 'tools/call':
            params     = req.get('params', {})
            tool_name  = params.get('name', '')
            tool_input = params.get('arguments', {})

            handler = TOOL_HANDLERS.get(tool_name)
            if not handler:
                self.send_json({
                    'jsonrpc': '2.0', 'id': req_id,
                    'error': {'code': -32601, 'message': f'Tool {tool_name} not found'}
                })
                return

            logging.info(f'Tool call: {tool_name} {json.dumps(tool_input)[:100]}')
            try:
                result = handler(tool_input)
                self.send_json({
                    'jsonrpc': '2.0', 'id': req_id,
                    'result': {
                        'content': [{
                            'type': 'text',
                            'text': json.dumps(result, ensure_ascii=False)
                        }]
                    }
                })
            except Exception as e:
                logging.error(f'Tool error: {e}')
                self.send_json({
                    'jsonrpc': '2.0', 'id': req_id,
                    'error': {'code': -32000, 'message': str(e)}
                })

        elif method == 'notifications/initialized':
            self.send_json({'jsonrpc': '2.0', 'id': req_id, 'result': {}})

        else:
            self.send_json({
                'jsonrpc': '2.0', 'id': req_id,
                'error': {'code': -32601, 'message': f'Method {method} not found'}
            })

    def _handle_call(self, req):
        """簡化呼叫端點（非標準MCP，方便測試）"""
        tool_name  = req.get('tool', '')
        tool_input = req.get('params', {})
        handler = TOOL_HANDLERS.get(tool_name)
        if not handler:
            self.send_json({'error': f'Tool {tool_name} not found'}, 404)
            return
        try:
            result = handler(tool_input)
            self.send_json(result)
        except Exception as e:
            self.send_json({'error': str(e)}, 500)


def run_server(port=8765):
    server = HTTPServer(('localhost', port), MCPHandler)
    logging.info(f'Scrapling MCP Server running on http://localhost:{port}')
    logging.info(f'Tools: {[t["name"] for t in TOOLS]}')
    logging.info('QClaw config: add to openclaw.json mcpServers section')
    server.serve_forever()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--test', action='store_true', help='測試模式')
    args = parser.parse_args()

    if args.test:
        # 快速測試
        print('Testing scrape_url...')
        r = execute_scrape_url('https://httpbin.org/json', max_chars=500)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        run_server(args.port)
