# -*- coding: utf-8 -*-
"""
cnki_wrapper.py v4
HTTP bridge for CNKI search, port 8767
使用 cloudscraper + requests，不依賴 Selenium/Chrome
"""

import json, logging, threading, time, random, os, traceback, re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import quote

PORT     = 8767
LOG_PATH = r'D:\LLM\workflows\research-pipeline-v2\logs\cnki_wrapper.log'

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
]

def get_session():
    import requests, urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    s = requests.Session()
    s.headers.update({'User-Agent': random.choice(USER_AGENTS)})
    s.verify = False
    return s

def search_cnki(query, search_type='SU', max_results=5):
    """
    搜尋知網，回傳論文列表
    使用 CNKI 搜尋 API endpoint
    """
    papers = []
    try:
        logging.info(f'CNKI search: "{query[:50]}" type={search_type} max={max_results}')
        session = get_session()

        # CNKI 搜尋 API
        search_url = 'https://kns.cnki.net/kns8s/search/grid'
        params = {
            'dbcode': 'SCDB',
            'dbprefix': 'CJFD',
            'searchType': 'MulityTermsSearch',
            'QueryJson': json.dumps({
                'Platform': '',
                'Resource': 'CROSSDB',
                'Criteria': f'SU%3D%27{quote(query)}%27+AND+DBCODE%3D%3DCJFD',
                'DBCodes': 'CJFD',
                'KuaKuCode': 'CJFD,CDFD,CMFD,CPFD,IPFD,CCND,CCJD',
            }),
            'pageNum': 1,
            'pageSize': max_results,
            'sortField': 'RT',
            'sortType': 'DESC',
        }

        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Referer': 'https://kns.cnki.net/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

        resp = session.get(search_url, params=params, headers=headers, timeout=20, verify=False)
        logging.info(f'CNKI API status: {resp.status_code}')

        if resp.status_code == 200:
            try:
                data = resp.json()
                items = data.get('data', {}).get('rows', []) or data.get('rows', [])
                for item in items[:max_results]:
                    paper = {
                        'title':   item.get('Title', '') or item.get('title', ''),
                        'authors': [item.get('Author', '')] if item.get('Author') else [],
                        'source':  item.get('Source', '') or item.get('source', ''),
                        'date':    str(item.get('Year', '') or item.get('year', '')),
                        'url':     item.get('Url', '') or item.get('url', ''),
                        'abstract': item.get('Abstract', '') or item.get('abstract', ''),
                    }
                    if paper['title']:
                        papers.append(paper)
                logging.info(f'CNKI JSON parsed: {len(papers)} papers')
            except Exception as e:
                logging.warning(f'JSON parse failed: {e}, trying HTML parse')
                papers = _parse_html(resp.text, max_results)
        else:
            # fallback: 直接搜尋頁面
            logging.warning(f'API failed ({resp.status_code}), trying direct search')
            papers = _search_direct(session, query, max_results)

    except Exception as e:
        logging.error(f'CNKI error: {e}\n{traceback.format_exc()}')

    logging.info(f'CNKI done: {len(papers)} papers')
    return papers


def _search_direct(session, query, max_results):
    """備用：直接請求搜尋頁面並解析 HTML"""
    papers = []
    try:
        from bs4 import BeautifulSoup
        url = f'https://kns.cnki.net/kns8/defaultresult/index?dbcode=SCDB&kw={quote(query)}&korder=SU'
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Referer': 'https://www.cnki.net/',
        }
        resp = session.get(url, headers=headers, timeout=20, verify=False)
        logging.info(f'Direct search status: {resp.status_code}')
        if resp.status_code == 200:
            papers = _parse_html(resp.text, max_results)
    except Exception as e:
        logging.error(f'Direct search error: {e}')
    return papers


def _parse_html(html, max_results):
    """解析 CNKI 搜尋結果 HTML"""
    papers = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.select('tr.odd, tr.even') or soup.select('.result-table-list tbody tr')
        for row in rows[:max_results]:
            paper = {}
            title_el = row.select_one('a.fz14') or row.select_one('td.name a')
            if not title_el:
                continue
            paper['title']  = title_el.get_text(strip=True)
            paper['url']    = title_el.get('href', '')
            author_el = row.select_one('td.author')
            paper['authors'] = [author_el.get_text(strip=True)] if author_el else []
            source_el = row.select_one('td.source')
            paper['source'] = source_el.get_text(strip=True) if source_el else ''
            date_el = row.select_one('td.date')
            paper['date'] = date_el.get_text(strip=True) if date_el else ''
            paper['abstract'] = ''
            if paper['title']:
                papers.append(paper)
        logging.info(f'HTML parsed: {len(papers)} papers')
    except ImportError:
        logging.warning('BeautifulSoup not installed, skipping HTML parse')
    except Exception as e:
        logging.error(f'HTML parse error: {e}')
    return papers


class CnkiHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logging.debug(f'HTTP {format % args}')

    def send_json(self, data, status=200):
        try:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
        except Exception as e:
            logging.warning(f'send_json error: {e}')

    def do_GET(self):
        if self.path == '/health':
            self.send_json({'status': 'ok', 'service': 'cnki-wrapper', 'port': PORT, 'version': 'v4'})
        else:
            self.send_json({'error': 'not found'}, 404)

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body   = self.rfile.read(length)
            data   = json.loads(body)
        except Exception as e:
            self.send_json({'error': f'invalid request: {e}'}, 400)
            return

        if self.path != '/call':
            self.send_json({'error': 'unknown path'}, 404)
            return

        tool   = data.get('tool', '')
        params = data.get('params', {})

        if tool != 'search_cnki':
            self.send_json({'error': f'unknown tool: {tool}'}, 400)
            return

        query       = params.get('query', '').strip()
        search_type = params.get('search_type', 'SU')
        max_results = int(params.get('max_results', 5))

        if not query:
            self.send_json({'error': 'query required'}, 400)
            return

        try:
            papers = search_cnki(query, search_type, max_results)
            self.send_json({'papers': papers, 'total': len(papers)})
        except Exception as e:
            logging.error(f'POST /call error: {e}\n{traceback.format_exc()}')
            self.send_json({'papers': [], 'total': 0, 'error': str(e)})


class ThreadedHTTPServer(HTTPServer):
    def process_request(self, request, client_address):
        t = threading.Thread(
            target=self.process_request_thread,
            args=(request, client_address),
            daemon=True
        )
        t.start()

    def process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            pass
        finally:
            self.shutdown_request(request)


if __name__ == '__main__':
    server = ThreadedHTTPServer(('0.0.0.0', PORT), CnkiHandler)
    logging.info(f'CNKI Wrapper v4 啟動 port {PORT}')
    logging.info(f'健康檢查: http://localhost:{PORT}/health')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info('CNKI Wrapper 停止')
        server.server_close()
