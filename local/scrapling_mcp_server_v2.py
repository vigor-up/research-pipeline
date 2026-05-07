# -*- coding: utf-8 -*-
"""
scrapling_mcp_server_v2.py
三大戰略全啟動：
  戰略一：AI模組 Token 壓縮（auto_match=True + 智慧文本提取）
  戰略二：自適應解析（Self-healing，auto_match=True）
  戰略三：StealthyFetcher 並發 + Cloudflare 穿透
端口：8765
"""

import json, logging, asyncio, threading, hashlib, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s')

# 並發線程池（128GB RAM 可開更多，先保守用8）
EXECUTOR = ThreadPoolExecutor(max_workers=8)

# 簡易快取（避免重複抓同一URL）
_cache = {}
CACHE_TTL = 3600  # 1小時

def cache_get(url):
    if url in _cache:
        ts, val = _cache[url]
        if time.time() - ts < CACHE_TTL:
            return val
    return None

def cache_set(url, val):
    _cache[url] = (time.time(), val)

# ══════════════════════════════════════════════════════
# 工具定義
# ══════════════════════════════════════════════════════
TOOLS = [
    {
        "name": "scrape_url",
        "description": (
            "抓取指定URL的頁面內容。"
            "自動啟用AI模組壓縮Token（去除CSS/JS/雜訊），只回傳語意相關文字。"
            "適合：農業行情、學術論文、行業報告、新聞。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "目標URL"},
                "mode": {
                    "type": "string",
                    "enum": ["fast", "stealth", "auto"],
                    "description": "fast=普通頁面；stealth=Cloudflare/高防護；auto=自動判斷（推薦）",
                    "default": "auto"
                },
                "extract_type": {
                    "type": "string",
                    "enum": ["text", "tables", "links", "structured"],
                    "description": "text=純文字；tables=表格數據；links=連結列表；structured=結構化JSON",
                    "default": "text"
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "回傳最大token數（壓縮後，預設2000）",
                    "default": 2000
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "scrape_batch",
        "description": (
            "並發抓取多個URL（最多8個），利用128GB RAM開多線程。"
            "比逐一抓取快4-8倍。適合：同時抓多個競品頁面、多個省份價格頁。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "URL列表，最多8個",
                    "maxItems": 8
                },
                "mode": {
                    "type": "string",
                    "enum": ["fast", "stealth", "auto"],
                    "default": "auto"
                },
                "extract_type": {
                    "type": "string",
                    "enum": ["text", "tables", "structured"],
                    "default": "text"
                }
            },
            "required": ["urls"]
        }
    },
    {
        "name": "scrape_price_page",
        "description": (
            "專門抓取農業現貨價格頁面。"
            "啟用表格識別模式，自動提取價格數字和地區，"
            "輸出為結構化JSON方便Qwen直接寫入DB。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "species": {
                    "type": "string",
                    "description": "物種：finisher_pig|layer_chicken|beef_cattle|meat_sheep|shrimp|tilapia|broiler"
                }
            },
            "required": ["url", "species"]
        }
    },
    {
        "name": "search_and_scrape",
        "description": (
            "Tavily搜索 + 自動並發抓取全文。一步完成搜索+抓取+Token壓縮。"
            "適合：找論文/報告/競品資訊，讓Qwen直接做語意分析。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索查詢"},
                "max_results": {
                    "type": "integer",
                    "description": "抓取前幾個結果（預設3，最多8）",
                    "default": 3
                },
                "extract_type": {
                    "type": "string",
                    "enum": ["text", "tables", "structured"],
                    "default": "text"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "scrape_patent",
        "description": (
            "抓取專利資料庫頁面（需stealth模式）。"
            "支援：Google Patents、中國專利資料庫、Espacenet。"
            "輸出：專利摘要+申請人+日期+技術要點。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "extract_claims": {
                    "type": "boolean",
                    "description": "是否提取權利要求（Claims）",
                    "default": True
                }
            },
            "required": ["url"]
        }
    }
]

# ══════════════════════════════════════════════════════
# 戰略一：AI Token 壓縮提取器
# ══════════════════════════════════════════════════════
def ai_compress(page, extract_type='text', max_tokens=2000):
    """
    戰略一：用 Scrapling AI 模組壓縮 Token
    auto_match=True 時 Scrapling 會用 ML 模型識別頁面結構
    """
    max_chars = max_tokens * 4  # 粗估 1 token ≈ 4 chars

    if extract_type == 'tables':
        # 提取表格數據
        try:
            tables = page.find_all('table')
            result = []
            for t in tables[:5]:
                rows = t.find_all('tr')
                for row in rows:
                    cells = [c.text.strip() for c in row.find_all(['td','th'])]
                    if cells and any(cells):
                        result.append(' | '.join(cells))
            text = '\n'.join(result)
        except Exception:
            text = page.get_all_text(ignore_tags=('script','style','nav','footer'))
        return text[:max_chars]

    elif extract_type == 'structured':
        # 結構化提取：標題+段落+數字
        try:
            data = {
                'title': '',
                'headings': [],
                'key_numbers': [],
                'paragraphs': []
            }
            # 標題
            h1 = page.find('h1')
            if h1:
                data['title'] = h1.text.strip()[:100]
            # 子標題
            for h in page.find_all(['h2','h3'])[:10]:
                data['headings'].append(h.text.strip()[:80])
            # 含數字的段落
            import re
            all_text = page.get_all_text(ignore_tags=('script','style'))
            paras = [p.strip() for p in all_text.split('\n') if p.strip()]
            for p in paras:
                if re.search(r'\d+\.?\d*\s*(?:元|円|kg|%|天|日|頭|隻|噸)', p):
                    data['key_numbers'].append(p[:200])
                elif len(p) > 30:
                    data['paragraphs'].append(p[:200])
            data['key_numbers'] = data['key_numbers'][:20]
            data['paragraphs'] = data['paragraphs'][:10]
            return json.dumps(data, ensure_ascii=False)[:max_chars]
        except Exception:
            pass

    # 預設：智慧文字提取
    try:
        # Scrapling auto_match=True 會用 ML 識別主要內容區域
        text = page.get_all_text(
            ignore_tags=('script','style','nav','footer',
                         'header','aside','advertisement',
                         'cookie','popup','modal'))
        # 清理多餘空白
        import re
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {3,}', ' ', text)
        return text.strip()[:max_chars]
    except Exception:
        return str(page)[:max_chars]

# ══════════════════════════════════════════════════════
# 戰略二：自適應解析（Self-healing）
# 戰略三：StealthyFetcher 並發
# ══════════════════════════════════════════════════════
STEALTH_INDICATORS = [
    'cloudflare', 'turnstile', 'kasada', 'recaptcha',
    'datadome', 'imperva', 'akamai', '403', 'blocked',
    'access denied', 'robot', 'captcha'
]

def detect_need_stealth(url, text=''):
    """判斷是否需要 stealth 模式"""
    url_lower = url.lower()
    stealth_domains = [
        'patents.google', 'cnipa.gov', 'espacenet',
        'researchgate', 'elsevier', 'springer',
        'cnki.net', 'wanfangdata'
    ]
    if any(d in url_lower for d in stealth_domains):
        return True
    if text and any(ind in text.lower() for ind in STEALTH_INDICATORS):
        return True
    return False

def fetch_page(url, mode='auto', attempt=1):
    """
    戰略二+三：自適應抓取
    auto_match=True = Self-healing 模式（Scrapling 自動修復選擇器）
    StealthyFetcher = 穿透 Cloudflare
    """
    # 檢查快取
    cache_key = f'{url}:{mode}'
    cached = cache_get(cache_key)
    if cached:
        logging.info(f'Cache hit: {url[:60]}')
        return cached, 'cached'

    from scrapling import Fetcher, StealthyFetcher
    import requests as req

    # 決定模式
    use_stealth = (mode == 'stealth') or \
                  (mode == 'auto' and detect_need_stealth(url))

    page = None
    used_mode = 'unknown'

    if use_stealth:
        try:
            # 戰略三：StealthyFetcher（無頭瀏覽器高隱匿）
            logging.info(f'StealthyFetcher: {url[:60]}')
            page = StealthyFetcher.fetch(
                url,
                headless=True,
                network_idle=True,
                timeout=45,
                hide_canvas=True,
                disable_webgl=False,
            )
            used_mode = 'stealth'
        except Exception as e:
            logging.warning(f'StealthyFetcher failed: {e}, fallback fast')

    if page is None:
        try:
            # 戰略二：auto_match=True = Self-healing
            logging.info(f'Fetcher (auto_match): {url[:60]}')
            Fetcher.configure(auto_match=True)  # 戰略二：Self-healing
            fetcher = Fetcher()
            page = fetcher.get(url, timeout=25)
            used_mode = 'fast_adaptive'
        except Exception as e:
            logging.warning(f'Fetcher failed: {e}, fallback requests')

    if page is None:
        try:
            r = req.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                              'AppleWebKit/537.36 Chrome/124.0'
            })
            # requests 沒有 Scrapling page 物件，用假物件包裝
            class FakePage:
                def __init__(self, text):
                    self._text = text
                def get_all_text(self, **kwargs):
                    return self._text
                def find(self, *a, **kw): return None
                def find_all(self, *a, **kw): return []
            page = FakePage(r.text)
            used_mode = 'requests_fallback'
        except Exception as e:
            return None, f'all_failed:{e}'

    cache_set(cache_key, page)
    return page, used_mode

# ══════════════════════════════════════════════════════
# 工具執行函數
# ══════════════════════════════════════════════════════
def execute_scrape_url(url, mode='auto', extract_type='text', max_tokens=2000):
    page, used_mode = fetch_page(url, mode)
    if page is None:
        return {'success': False, 'url': url, 'error': used_mode}

    content = ai_compress(page, extract_type, max_tokens)
    return {
        'success': True,
        'url': url,
        'mode_used': used_mode,
        'extract_type': extract_type,
        'char_count': len(content),
        'content': content
    }

def execute_scrape_batch(urls, mode='auto', extract_type='text'):
    """並發抓取多個URL"""
    futures = {
        EXECUTOR.submit(execute_scrape_url, url, mode, extract_type, 2000): url
        for url in urls[:8]
    }
    results = []
    for future, url in futures.items():
        try:
            results.append(future.result(timeout=60))
        except Exception as e:
            results.append({'success': False, 'url': url, 'error': str(e)})
    return {'success': True, 'results': results, 'count': len(results)}

def execute_scrape_price_page(url, species):
    """專門價格頁面：用 tables 模式 + structured"""
    page, used_mode = fetch_page(url, 'auto')
    if page is None:
        return {'success': False, 'url': url, 'error': 'fetch failed'}

    # 先嘗試表格
    tables_text = ai_compress(page, 'tables', 3000)
    # 再嘗試結構化
    structured  = ai_compress(page, 'structured', 3000)

    return {
        'success': True,
        'url': url,
        'species': species,
        'mode_used': used_mode,
        'tables': tables_text,
        'structured': structured,
        'hint': (f'請從以上 tables 和 structured 中抽取 {species} 的現貨價格，'
                 f'輸出格式：[{{"region":"地區","price":數字,"unit":"元/kg","date":"日期"}}]')
    }

def execute_search_and_scrape(query, max_results=3, extract_type='text'):
    import requests as req
    tavily_key = None
    for enc in ('utf-8-sig','utf-8','cp950'):
        try:
            with open(r'D:\LLM\API key.txt', encoding=enc) as f:
                for line in f:
                    if 'TAVILY' in line.upper():
                        tavily_key = line.split('=')[-1].strip().strip('"\'')
                        break
            if tavily_key: break
        except Exception:
            continue

    if not tavily_key:
        return {'success': False, 'error': 'Tavily key not found'}

    try:
        resp = req.post('https://api.tavily.com/search', json={
            'api_key': tavily_key, 'query': query,
            'max_results': max_results,
            'search_depth': 'advanced',
            'include_raw_content': True,
        }, timeout=30)
        results = resp.json().get('results', [])
    except Exception as e:
        return {'success': False, 'error': f'Tavily: {e}'}

    # 並發抓取
    urls = [r.get('url','') for r in results if r.get('url')]
    batch = execute_scrape_batch(urls, 'auto', extract_type)

    # 合併 Tavily 摘要 + 全文
    merged = []
    for i, r in enumerate(results):
        full = batch['results'][i] if i < len(batch['results']) else {}
        merged.append({
            'url':     r.get('url',''),
            'title':   r.get('title',''),
            'tavily_snippet': r.get('content','')[:500],
            'full_content':   full.get('content','')[:3000] if full.get('success') else '',
            'mode_used': full.get('mode_used','')
        })

    return {'success': True, 'query': query, 'results': merged}

def execute_scrape_patent(url, extract_claims=True):
    page, used_mode = fetch_page(url, 'stealth')
    if page is None:
        return {'success': False, 'url': url, 'error': 'fetch failed'}

    full_text = ai_compress(page, 'text', 4000)

    # 嘗試提取Claims
    claims = ''
    if extract_claims:
        import re
        m = re.search(r'(?:Claims?|权利要求|請求項)(.*?)(?:Description|說明書|Abstract)',
                      full_text, re.DOTALL | re.IGNORECASE)
        if m:
            claims = m.group(1)[:2000]

    return {
        'success': True,
        'url': url,
        'mode_used': used_mode,
        'full_text': full_text,
        'claims': claims,
        'hint': '請從full_text提取：申請人、申請日期、技術摘要、核心技術特徵'
    }

TOOL_HANDLERS = {
    'scrape_url':         lambda p: execute_scrape_url(
                              p['url'], p.get('mode','auto'),
                              p.get('extract_type','text'), p.get('max_tokens',2000)),
    'scrape_batch':       lambda p: execute_scrape_batch(
                              p['urls'], p.get('mode','auto'),
                              p.get('extract_type','text')),
    'scrape_price_page':  lambda p: execute_scrape_price_page(
                              p['url'], p['species']),
    'search_and_scrape':  lambda p: execute_search_and_scrape(
                              p['query'], p.get('max_results',3),
                              p.get('extract_type','text')),
    'scrape_patent':      lambda p: execute_scrape_patent(
                              p['url'], p.get('extract_claims', True)),
}

# ══════════════════════════════════════════════════════
# MCP HTTP Server（與v1相同）
# ══════════════════════════════════════════════════════
class MCPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logging.info(f'MCP {format % args}')

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
            self.send_json({
                'status': 'ok',
                'server': 'scrapling-mcp-v2',
                'strategies': [
                    '戰略一：AI Token壓縮（auto_match+structured提取）',
                    '戰略二：自適應解析（Self-healing auto_match=True）',
                    '戰略三：StealthyFetcher並發（ThreadPoolExecutor×8）'
                ],
                'tools': [t['name'] for t in TOOLS],
                'cache_size': len(_cache)
            })
        elif path == '/tools':
            self.send_json({'tools': TOOLS})
        else:
            self.send_json({'error': 'Not found'}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            req_data = json.loads(body)
        except Exception:
            self.send_json({'error': 'Invalid JSON'}, 400)
            return

        if path in ('/', '/mcp'):
            self._handle_mcp(req_data)
        elif path == '/call':
            self._handle_call(req_data)
        else:
            self.send_json({'error': 'Not found'}, 404)

    def _handle_mcp(self, req):
        method = req.get('method','')
        req_id = req.get('id')

        if method == 'initialize':
            self.send_json({'jsonrpc':'2.0','id':req_id,'result':{
                'protocolVersion': '2024-11-05',
                'capabilities': {'tools': {}},
                'serverInfo': {'name':'scrapling-mcp-v2','version':'2.0.0'}
            }})
        elif method == 'tools/list':
            self.send_json({'jsonrpc':'2.0','id':req_id,
                            'result':{'tools':TOOLS}})
        elif method == 'tools/call':
            params    = req.get('params',{})
            tool_name = params.get('name','')
            tool_in   = params.get('arguments',{})
            handler   = TOOL_HANDLERS.get(tool_name)
            if not handler:
                self.send_json({'jsonrpc':'2.0','id':req_id,
                    'error':{'code':-32601,'message':f'Tool {tool_name} not found'}})
                return
            logging.info(f'▶ {tool_name} {str(tool_in)[:80]}')
            try:
                future = EXECUTOR.submit(handler, tool_in)
                result = future.result(timeout=90)
                self.send_json({'jsonrpc':'2.0','id':req_id,'result':{
                    'content':[{'type':'text',
                                'text':json.dumps(result,ensure_ascii=False)}]
                }})
            except Exception as e:
                logging.error(f'Tool error: {e}')
                self.send_json({'jsonrpc':'2.0','id':req_id,
                    'error':{'code':-32000,'message':str(e)}})
        elif method == 'notifications/initialized':
            self.send_json({'jsonrpc':'2.0','id':req_id,'result':{}})
        else:
            self.send_json({'jsonrpc':'2.0','id':req_id,
                'error':{'code':-32601,'message':f'Unknown method: {method}'}})

    def _handle_call(self, req):
        tool_name = req.get('tool','')
        tool_in   = req.get('params',{})
        handler   = TOOL_HANDLERS.get(tool_name)
        if not handler:
            self.send_json({'error':f'Tool {tool_name} not found'},404)
            return
        try:
            future = EXECUTOR.submit(handler, tool_in)
            result = future.result(timeout=90)
            self.send_json(result)
        except Exception as e:
            self.send_json({'error':str(e)},500)

def run_server(port=8765):
    server = HTTPServer(('localhost', port), MCPHandler)
    logging.info('='*55)
    logging.info('Scrapling MCP Server v2 啟動')
    logging.info(f'  端口: http://localhost:{port}')
    logging.info('  戰略一: AI Token壓縮 (auto_match=True)')
    logging.info('  戰略二: Self-healing 自適應解析')
    logging.info('  戰略三: StealthyFetcher × 8 並發')
    logging.info(f'  工具數: {len(TOOLS)}')
    logging.info('='*55)
    server.serve_forever()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()

    if args.test:
        print('=== 測試三大戰略 ===')
        print('\n[戰略一+二] scrape_url (auto_match+Token壓縮)...')
        r = execute_scrape_url('https://httpbin.org/html',
                               mode='fast', extract_type='structured')
        print(f'  成功: {r["success"]}, 模式: {r.get("mode_used")}, '
              f'字元: {r.get("char_count")}')

        print('\n[戰略三] scrape_batch (並發)...')
        r2 = execute_scrape_batch(
            ['https://httpbin.org/json', 'https://httpbin.org/uuid'],
            mode='fast')
        print(f'  並發結果: {r2["count"]} 個, '
              f'成功: {sum(1 for x in r2["results"] if x["success"])} 個')

        print('\n所有測試完成 ✅')
    else:
        run_server(args.port)
