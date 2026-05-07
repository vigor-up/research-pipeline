import boto3, os, json
from pathlib import Path

# 讀 R2 credentials
import sys
sys.path.insert(0, r"D:\LLM\workflows\research-pipeline-v2")

# 直接用 API key 檔
keys = {}
for line in open(r"D:\API key.txt", encoding="utf-8"):
    if "R2" in line and "=" in line:
        k, v = line.strip().split("=", 1)
        keys[k.strip()] = v.strip()
print("Keys found:", list(keys.keys()))
