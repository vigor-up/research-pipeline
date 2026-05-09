# -*- coding: utf-8 -*-
import os, logging, tarfile, tempfile, hashlib
from datetime import datetime
from pathlib import Path

SQLITE_PATH = r'D:\LLM\knowledge\market\market_data.db'
CHROMA_PATH = r'D:\LLM\knowledge\biotech\db'
LOG_PATH    = r'D:\LLM\workflows\research-pipeline-v2\logs\db_push_r2.log'
R2_ENDPOINT = 'https://adb1040c847f4ae4a7d6bfedcccd7b77.r2.cloudflarestorage.com'
R2_ACCESS   = os.environ.get('R2_ACCESS_KEY_ID',     'f443b2e5acc77dd1af6a83a5d548b35b')
R2_SECRET   = os.environ.get('R2_SECRET_ACCESS_KEY', 'da1c377ffbc03b865504e292480e0e2806ddb84a61bf87b7e6a2066632a4a357')
R2_BUCKET   = 'richtrong-collect'
TELEGRAM_TOKEN = '8703702788:AAFKEiGmLYTAuFVG9GX-gRtVTUUyi-f_5mM'
TELEGRAM_CHAT  = 897274134

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_PATH, encoding='utf-8'), logging.StreamHandler()])

def tg(msg):
    try:
        import requests
        requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id': TELEGRAM_CHAT, 'text': msg, 'parse_mode': 'HTML'}, timeout=10)
    except: pass

def get_s3():
    import boto3
    from botocore.config import Config
    return boto3.client('s3', endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS, aws_secret_access_key=R2_SECRET,
        region_name='auto', config=Config(retries={'max_attempts': 3}))

def push_sqlite(s3):
    src = Path(SQLITE_PATH)
    if not src.exists():
        logging.error(f'SQLite not found: {src}'); return False, 0
    size_mb = src.stat().st_size / 1024 / 1024
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    with open(src, 'rb') as f: data = f.read()
    s3.put_object(Bucket=R2_BUCKET, Key='sync/market_data.db', Body=data,
        ContentType='application/x-sqlite3', Metadata={'pushed_at': ts})
    s3.put_object(Bucket=R2_BUCKET, Key=f'backup/sqlite/{datetime.now().strftime("%Y-%m-%d")}/market_data.db',
        Body=data, ContentType='application/x-sqlite3')
    logging.info(f'SQLite pushed: {size_mb:.1f}MB'); return True, size_mb

def push_chroma(s3):
    src = Path(CHROMA_PATH)
    if not src.exists():
        logging.error(f'ChromaDB not found: {src}'); return False, 0
    with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp:
        tmp_path = tmp.name
    try:
        with tarfile.open(tmp_path, 'w:gz') as tar: tar.add(src, arcname='chromadb')
        size_mb = os.path.getsize(tmp_path) / 1024 / 1024
        ts = datetime.now().strftime('%Y%m%d_%H%M')
        with open(tmp_path, 'rb') as f: data = f.read()
        s3.put_object(Bucket=R2_BUCKET, Key='sync/chromadb.tar.gz', Body=data,
            ContentType='application/gzip', Metadata={'pushed_at': ts})
        s3.put_object(Bucket=R2_BUCKET, Key=f'backup/chroma/{datetime.now().strftime("%Y-%m-%d")}/chromadb.tar.gz',
            Body=data, ContentType='application/gzip')
        logging.info(f'ChromaDB pushed: {size_mb:.1f}MB'); return True, size_mb
    finally:
        os.unlink(tmp_path)

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--only', choices=['sqlite','chroma'])
    args = p.parse_args()
    start = datetime.now()
    logging.info('db_push_r2 開始')
    s3 = get_s3()
    results = []
    if args.only != 'chroma':
        ok, mb = push_sqlite(s3)
        results.append(f'SQLite: {"OK" if ok else "FAIL"} {mb:.1f}MB')
    if args.only != 'sqlite':
        ok, mb = push_chroma(s3)
        results.append(f'ChromaDB: {"OK" if ok else "FAIL"} {mb:.1f}MB')
    elapsed = int((datetime.now()-start).total_seconds())
    summary = "\n".join(results)
    logging.info(f'完成 {elapsed}s\n{summary}')
    tg(f'<b>DB同步推送完成</b>\n{summary}\n耗時:{elapsed}s')
