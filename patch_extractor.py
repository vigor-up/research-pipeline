content = open('local/market_report_extractor.py', encoding='utf-8').read()

ragflow_const = """
RAGFLOW_API_KEY = 'ragflow-fcCq8K0sVcefhVHboEmBOOzt5S2cQ7jCcHT5cCwhWRM'
RAGFLOW_BASE_URL = 'http://localhost'
RAGFLOW_DATASET_ID = '5a68aa6e49ba11f190c657ee8852d812'
"""

ragflow_func = """
def upload_to_ragflow(text, doc_name):
    import tempfile, os, requests, logging
    headers = {'Authorization': f'Bearer {RAGFLOW_API_KEY}'}
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    tmp.write(text); tmp.close()
    try:
        with open(tmp.name, 'rb') as f:
            resp = requests.post(
                f'{RAGFLOW_BASE_URL}/api/v1/datasets/{RAGFLOW_DATASET_ID}/documents',
                headers=headers,
                files={'file': (doc_name, f, 'text/plain')}
            )
        if resp.status_code == 200 and resp.json().get('code') == 0:
            doc_id = resp.json()['data'][0]['id']
            requests.post(
                f'{RAGFLOW_BASE_URL}/api/v1/datasets/{RAGFLOW_DATASET_ID}/chunks',
                headers=headers,
                json={'document_ids': [doc_id]}
            )
            logging.info(f'[RAGFlow] 上傳成功: {doc_name}')
            return True
    except Exception as e:
        logging.error(f'[RAGFlow] 上傳失敗: {e}')
    finally:
        os.unlink(tmp.name)
    return False

"""

content = content.replace(
    "MCP_URL        = 'http://localhost:8765/call'",
    "MCP_URL        = 'http://localhost:8765/call'" + ragflow_const
)
content = content.replace('def tg(msg):', ragflow_func + 'def tg(msg):')
content = content.replace(
    '    return n, report',
    "    doc_name = f\"market_{extracted.get('report_date','unknown')}_{extracted.get('species','unknown')}.txt\"\n    upload_to_ragflow(text, doc_name)\n    return n, report"
)
open('local/market_report_extractor.py', 'w', encoding='utf-8').write(content)
print('done')
