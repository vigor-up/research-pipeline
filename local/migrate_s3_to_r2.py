#!/usr/bin/env python3
"""
AWS S3 → Cloudflare R2 一次性遷移腳本
在 EVO-X2 上執行一次即可

使用方式：
  python migrate_s3_to_r2.py

需要先設定環境變數（或直接在下方填入）：
  $env:AWS_ACCESS_KEY_ID    = "你的 AWS key"
  $env:AWS_SECRET_ACCESS_KEY = "你的 AWS secret"
  $env:R2_ACCESS_KEY_ID     = "你的 R2 key"
  $env:R2_SECRET_ACCESS_KEY = "你的 R2 secret"
"""

import boto3, json, os
from datetime import datetime

# ── 設定 ──────────────────────────────────────────────
AWS_BUCKET   = 'gld-mms-data-richtrong'
AWS_REGION   = 'ap-northeast-1'

R2_BUCKET    = 'richtrong-collect'
R2_ENDPOINT  = 'https://adb1040c847f4ae4a7d6bfedcccd7b77.r2.cloudflarestorage.com'

AWS_KEY      = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET   = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
R2_KEY       = os.environ.get('R2_ACCESS_KEY_ID', '')
R2_SECRET    = os.environ.get('R2_SECRET_ACCESS_KEY', '')

BACKUP_DIR   = r'D:\LLM\backups\s3-migration-' + datetime.now().strftime('%Y%m%d')

# 要遷移的所有 key（有幾個算幾個）
KEYS = [
    'signal_state.json',
    'signal_history.json',
    'data.json',
]
# ────────────────────────────────────────────────────────

def main():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    print(f"\n=== S3 → R2 Migration ===")
    print(f"AWS: s3://{AWS_BUCKET}")
    print(f"R2:  {R2_ENDPOINT}/{R2_BUCKET}")
    print(f"備份目錄: {BACKUP_DIR}\n")

    if not all([AWS_KEY, AWS_SECRET, R2_KEY, R2_SECRET]):
        print("❌ 缺少環境變數，請設定：")
        print("   $env:AWS_ACCESS_KEY_ID     = '...'")
        print("   $env:AWS_SECRET_ACCESS_KEY = '...'")
        print("   $env:R2_ACCESS_KEY_ID      = '...'")
        print("   $env:R2_SECRET_ACCESS_KEY  = '...'")
        return

    # 建立 clients
    s3_aws = boto3.client('s3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET)

    s3_r2 = boto3.client('s3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_KEY,
        aws_secret_access_key=R2_SECRET,
        region_name='auto')

    # 1. 列出 AWS S3 全部 key
    print("📋 列出 AWS S3 全部物件...")
    try:
        resp = s3_aws.list_objects_v2(Bucket=AWS_BUCKET)
        all_keys = [obj['Key'] for obj in resp.get('Contents', [])]
        print(f"  找到 {len(all_keys)} 個物件：{all_keys}")
    except Exception as e:
        print(f"  ❌ 無法列出 AWS S3：{e}")
        all_keys = KEYS  # fallback 用預設清單

    # 2. 逐一複製
    success, fail = 0, 0
    for key in all_keys:
        try:
            # 從 AWS 下載
            obj = s3_aws.get_object(Bucket=AWS_BUCKET, Key=key)
            data = obj['Body'].read()

            # 本地備份
            bak_path = os.path.join(BACKUP_DIR, key.replace('/', '_'))
            with open(bak_path, 'wb') as f:
                f.write(data)

            # 上傳到 R2
            s3_r2.put_object(
                Bucket=R2_BUCKET,
                Key=key,
                Body=data,
                ContentType='application/json'
            )

            size = len(data)
            print(f"  ✅ {key} ({size} bytes) → R2 + 本地備份")
            success += 1

        except Exception as e:
            print(f"  ❌ {key}: {e}")
            fail += 1

    # 3. 驗證 R2
    print(f"\n📋 驗證 R2 bucket...")
    try:
        resp = s3_r2.list_objects_v2(Bucket=R2_BUCKET)
        r2_keys = [obj['Key'] for obj in resp.get('Contents', [])]
        print(f"  R2 中的物件：{r2_keys}")
    except Exception as e:
        print(f"  ❌ 無法列出 R2：{e}")

    print(f"\n=== 完成 ===")
    print(f"  成功：{success}  失敗：{fail}")
    print(f"  本地備份：{BACKUP_DIR}")
    print(f"\n下一步：")
    print(f"  1. 確認 R2 資料正確後，上傳新版 update_gld_data.py 到 GitHub")
    print(f"  2. 確認網站正常後，再取消 AWS S3 bucket 訂閱")

if __name__ == '__main__':
    main()
