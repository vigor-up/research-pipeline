"""
Research Pipeline v1.1 - Animal Nutrition
EVO-X2 / Qwen3.6-35B + ChromaDB

Usage:
    python pipeline.py --topic octacosanol
    python pipeline.py --topic all
    python pipeline.py --topic octacosanol --stages 1,2,3
    python pipeline.py --dry-run

API Key 優先順序：
    1. 環境變數 S2_API_KEY（建議）
    2. topics.yaml 的 settings.api.semantic_scholar_key（fallback）
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Stage modules
sys.path.insert(0, str(Path(__file__).parent / "stages"))
import importlib

ROOT = Path(r"D:\LLM\workflows\research")
KNOWLEDGE = Path(r"D:\LLM\knowledge\biotech")

STAGE_MAP = {
    1: ("01_discover",   "discover"),
    2: ("02_dedupe",     "dedupe"),
    3: ("03_fetch_pdf",  "fetch_pdf"),
    4: ("04_parse",      "parse"),
    5: ("05_summarize",  "summarize"),
    6: ("06_embed",      "embed"),
}


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def load_config():
    """載入 topics.yaml，回傳完整 config dict（含 settings）"""
    import yaml
    cfg_path = ROOT / "configs" / "topics.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # S2 API key：環境變數優先，fallback 到 yaml
    s2_key = os.environ.get("S2_API_KEY") or data["settings"]["api"].get("semantic_scholar_key", "")
    data["settings"]["api"]["semantic_scholar_key"] = s2_key

    if s2_key:
        log(f"S2 API key loaded (source: {'env' if os.environ.get('S2_API_KEY') else 'yaml'})")
    else:
        log("WARNING: No S2 API key found, Semantic Scholar disabled", "WARN")

    return data


def load_topics(topic_filter, config):
    topics = config["topics"]
    if topic_filter == "all":
        return topics
    if topic_filter not in topics:
        log(f"Unknown topic: {topic_filter}. Available: {list(topics.keys())}", "ERROR")
        sys.exit(1)
    return {topic_filter: topics[topic_filter]}


def run_stage(stage_id, topic_name, topic_cfg, global_cfg, dry_run=False):
    mod_name, func_name = STAGE_MAP[stage_id]
    log(f"--- Stage {stage_id}: {mod_name} ({topic_name}) ---")
    if dry_run:
        log(f"DRY RUN: would call {mod_name}.{func_name}()")
        return {"ok": True, "dry_run": True}

    mod = importlib.import_module(mod_name)
    fn = getattr(mod, func_name)
    t0 = time.time()
    try:
        # global_cfg 傳入讓各 stage 取用 API key、路徑等全域設定
        result = fn(topic_name, topic_cfg, global_cfg)
        elapsed = time.time() - t0
        log(f"Stage {stage_id} done in {elapsed:.1f}s | {result}")
        return result
    except TypeError:
        # 舊版 stage 只接受 2 個參數，向下相容
        result = fn(topic_name, topic_cfg)
        elapsed = time.time() - t0
        log(f"Stage {stage_id} done in {elapsed:.1f}s | {result}")
        return result
    except Exception as e:
        log(f"Stage {stage_id} FAILED: {e}", "ERROR")
        return {"ok": False, "error": str(e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="all", help="topic key or 'all'")
    ap.add_argument("--stages", default="1,2,5,6",
                    help="comma-separated stage IDs (1-6)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    stage_ids = [int(s) for s in args.stages.split(",")]

    config = load_config()
    topics = load_topics(args.topic, config)
    global_cfg = config["settings"]

    log(f"Pipeline start | topics={list(topics.keys())} | stages={stage_ids}")

    summary = {}
    for tname, tcfg in topics.items():
        log(f"=== Topic: {tname} ===")
        summary[tname] = {}
        for sid in stage_ids:
            result = run_stage(sid, tname, tcfg, global_cfg, args.dry_run)
            summary[tname][sid] = result
            if not result.get("ok", True):
                log(f"Stopping topic {tname} due to failure", "WARN")
                break

    # Run log
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"run_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    log(f"Run log: {log_path}")
    log("Pipeline complete.")


if __name__ == "__main__":
    main()
