"""
upload_ingredients_to_r2.py
把本地 ingredients.yaml 上傳到 Cloudflare R2
EVO-X2 本地執行，或由 tg_commander.py 的「部署 ingredients.yaml」按鈕呼叫

用法：
  python upload_ingredients_to_r2.py
  python upload_ingredients_to_r2.py --file D:\\LLM\\workflows\\research-pipeline-v2\\configs\\ingredients.yaml
"""

import os
import sys
import argparse
import logging
from pathlib import Path

import boto3
import yaml
from botocore.config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

DEFAULT_PATH = Path(r"D:\LLM\workflows\research-pipeline-v2\configs\ingredients.yaml")


def get_r2():
    acct = os.environ.get("CF_R2_ACCOUNT_ID") or os.environ.get("R2_ACCOUNT_ID")
    key  = os.environ.get("CF_R2_ACCESS_KEY_ID") or os.environ.get("R2_ACCESS_KEY_ID")
    sec  = os.environ.get("CF_R2_SECRET_ACCESS_KEY") or os.environ.get("R2_SECRET_ACCESS_KEY")
    bkt  = os.environ.get("CF_R2_BUCKET_NAME") or os.environ.get("R2_BUCKET", "richtrong-collect")
    if not all([acct, key, sec]):
        sys.exit("❌ 未設定 R2 環境變數 (CF_R2_ACCOUNT_ID / CF_R2_ACCESS_KEY_ID / CF_R2_SECRET_ACCESS_KEY)")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{acct}.r2.cloudflarestorage.com",
        aws_access_key_id=key,
        aws_secret_access_key=sec,
        region_name="auto",
        config=Config(retries={"max_attempts": 3}),
    ), bkt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=str(DEFAULT_PATH))
    args = parser.parse_args()

    src = Path(args.file)
    if not src.exists():
        sys.exit(f"❌ 找不到 {src}")

    # 驗證 YAML
    try:
        with open(src, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        count = len(cfg.get("ingredients", []))
        moat  = sum(1 for i in cfg["ingredients"] if i.get("strategy") == "moat")
        log.info(f"YAML OK：{count} 個原料（{moat} 個 moat 核心）")
    except Exception as e:
        sys.exit(f"❌ YAML 解析錯誤：{e}")

    s3, bucket = get_r2()
    r2_key = "configs/ingredients.yaml"

    with open(src, "rb") as f:
        s3.put_object(
            Bucket=bucket,
            Key=r2_key,
            Body=f.read(),
            ContentType="application/yaml",
        )

    log.info(f"✅ 上傳完成 → R2:{bucket}/{r2_key}")
    log.info(f"   GitHub Actions 下次執行時自動讀取新設定")


if __name__ == "__main__":
    main()
