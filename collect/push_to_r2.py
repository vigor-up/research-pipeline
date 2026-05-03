"""
push_to_r2.py
Upload scored raw_papers.json (gzipped) to Cloudflare R2 via S3-compatible API.

Required environment variables:
  CF_R2_ACCOUNT_ID
  CF_R2_ACCESS_KEY_ID
  CF_R2_SECRET_ACCESS_KEY
  CF_R2_BUCKET_NAME
"""

import os
import sys
import gzip
import json
import argparse
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                    format="%(asctime)s [push_r2] %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def get_r2_client():
    account_id = os.environ["CF_R2_ACCOUNT_ID"]
    access_key = os.environ["CF_R2_ACCESS_KEY_ID"]
    secret_key = os.environ["CF_R2_SECRET_ACCESS_KEY"]

    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )


def push(input_path: str = "raw_papers.json", dry_run: bool = False) -> bool:
    bucket = os.environ["CF_R2_BUCKET_NAME"]
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    r2_key = f"raw_papers/{date_str}/raw_papers.json.gz"

    with open(input_path, "rb") as f:
        raw = f.read()

    compressed = gzip.compress(raw)
    size_kb = len(compressed) / 1024
    log.info("File: %s | Original: %.1f KB | Compressed: %.1f KB | R2 key: %s",
             input_path, len(raw) / 1024, size_kb, r2_key)

    if dry_run:
        log.info("[dry-run] Skipping upload.")
        return True

    try:
        client = get_r2_client()
        client.put_object(
            Bucket=bucket,
            Key=r2_key,
            Body=compressed,
            ContentType="application/json",
            ContentEncoding="gzip",
            Metadata={"collected_date": date_str},
        )
        log.info("Upload successful: s3://%s/%s (%.1f KB)", bucket, r2_key, size_kb)
        return True
    except ClientError as e:
        log.error("Upload failed: %s", e)
        return False


def main():
    parser = argparse.ArgumentParser(description="Push raw_papers.json to Cloudflare R2")
    parser.add_argument("--input", default="raw_papers.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    success = push(args.input, args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
