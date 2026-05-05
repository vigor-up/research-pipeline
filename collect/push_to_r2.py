"""
push_to_r2.py
把 scored JSON 推送到 Cloudflare R2
Key 格式：raw_papers/YYYY-WW.json（週次）+ raw_papers/latest.json
"""

import os
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone

import boto3
from botocore.config import Config

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")


def get_r2_client():
    account_id = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(retries={"max_attempts": 3}),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="/tmp/raw_papers_scored.json")
    args = parser.parse_args()

    bucket = os.environ["R2_BUCKET"]
    data   = Path(args.input).read_text(encoding="utf-8")
    now    = datetime.now(timezone.utc)
    week   = now.strftime("%Y-W%W")

    s3 = get_r2_client()

    # 週次存檔（可回溯）
    week_key = f"raw_papers/{week}.json"
    s3.put_object(Bucket=bucket, Key=week_key,
                  Body=data.encode("utf-8"),
                  ContentType="application/json")
    log.info(f"Uploaded → {week_key}")

    # latest（EVO-X2 下載用）
    s3.put_object(Bucket=bucket, Key="raw_papers/latest.json",
                  Body=data.encode("utf-8"),
                  ContentType="application/json")
    log.info("Uploaded → raw_papers/latest.json")

    # 統計
    parsed = json.loads(data)
    total  = parsed.get("total", 0)
    dist   = parsed.get("credibility_dist", {})
    log.info(f"Total: {total} | L5:{dist.get('5',0)} L4:{dist.get('4',0)} "
             f"L3:{dist.get('3',0)} L2:{dist.get('2',0)} L1:{dist.get('1',0)}")


if __name__ == "__main__":
    main()
