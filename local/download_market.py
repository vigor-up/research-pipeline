"""
download_market.py
從 R2 同步最新 market_data.db 到本機
用法：python local/download_market.py
"""
import boto3, shutil
from pathlib import Path

R2_ENDPOINT  = "https://adb1040c847f4ae4a7d6bfedcccd7b77.r2.cloudflarestorage.com"
R2_KEY_ID    = "f443b2e5acc77dd1af6a83a5d548b35b"
R2_SECRET    = "da1c377ffbc03b865504e292480e0e2806ddb84a61bf87b7e6a2066632a4a357"
R2_BUCKET    = "richtrong-collect"
R2_KEY       = "market_data/market_data.db"
LOCAL_DB     = Path(r"D:\LLM\knowledge\market\market_data.db")

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_KEY_ID,
    aws_secret_access_key=R2_SECRET,
    region_name="auto",
)

tmp = LOCAL_DB.with_suffix(".tmp")
try:
    s3.download_file(R2_BUCKET, R2_KEY, str(tmp))
    shutil.move(str(tmp), str(LOCAL_DB))
    import sqlite3
    count = sqlite3.connect(LOCAL_DB).execute("SELECT COUNT(*) FROM market_kpi").fetchone()[0]
    print(f"✅ Synced: {count} rows → {LOCAL_DB}")
except Exception as e:
    print(f"❌ Sync failed: {e}")
    tmp.unlink(missing_ok=True)
