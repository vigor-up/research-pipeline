"""
download_and_analyze.py
1. Download latest raw_papers.json.gz from Cloudflare R2
2. Dedupe against existing ChromaDB
3. Batch analyze with local Qwen (5 papers/batch)
4. Upsert results into ChromaDB

Required environment variables:
  CF_R2_ACCOUNT_ID, CF_R2_ACCESS_KEY_ID, CF_R2_SECRET_ACCESS_KEY, CF_R2_BUCKET_NAME
"""

import os
import sys
import gzip
import json
import time
import argparse
import logging

import boto3
import requests
import chromadb
import yaml
from sentence_transformers import SentenceTransformer

logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                    format="%(asctime)s [analyze] %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "configs", "species_metrics.yaml")

ANALYZE_PROMPT = """Analyze these {n} animal nutrition papers. Return a JSON array only, no explanation.

Papers:
{papers_json}

For each paper return:
{{
  "paper_id": "<id from input>",
  "category": "A|B|C|D|E",
  "species": ["broiler","layer_hen","finisher_pig","nursery_pig","pregnant_sow","lactating_sow","boar","breeder_chicken","shrimp","tilapia","livestock"],
  "metrics": {{
    "FCR": {{"value": 2.3, "unit": "ratio", "change_pct": -18}},
    "ADG": {{"value": 850, "unit": "g/day", "change_pct": 6}}
  }},
  "strategic_tags": ["competitive_intel","defense_ammo","mechanism_support","opportunity_scan","self_validation"],
  "quality_score": 3,
  "key_finding": "one sentence summary in English",
  "is_b_group": true
}}

Category: A=field trial with performance data, B=mechanism study, C=adjacent species, D=review/meta, E=noise/irrelevant
is_b_group=true means paper contains quantitative market claim numbers usable for competitor comparison.
metrics: only include metrics actually mentioned with numbers in abstract.
Output only the JSON array, nothing else."""


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── R2 Download ───────────────────────────────────────────────────────────────

def get_r2_client():
    account_id = os.environ["CF_R2_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["CF_R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["CF_R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def download_latest(bucket: str) -> list:
    client = get_r2_client()
    response = client.list_objects_v2(Bucket=bucket, Prefix="raw_papers/")
    objects = response.get("Contents", [])
    if not objects:
        log.error("No raw_papers found in R2 bucket.")
        return []

    latest = sorted(objects, key=lambda x: x["LastModified"], reverse=True)[0]
    key = latest["Key"]
    log.info("Downloading: %s (%.1f KB)", key, latest["Size"] / 1024)

    obj = client.get_object(Bucket=bucket, Key=key)
    compressed = obj["Body"].read()
    raw = gzip.decompress(compressed)
    papers = json.loads(raw)
    log.info("Downloaded %d papers", len(papers))
    return papers


# ── ChromaDB ──────────────────────────────────────────────────────────────────

def get_collection(db_path: str, collection_name: str):
    client = chromadb.PersistentClient(path=db_path)
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def get_existing_ids(collection) -> set:
    result = collection.get(include=[])
    return set(result["ids"])


# ── Qwen Analysis ─────────────────────────────────────────────────────────────

def analyze_batch(papers: list, endpoint: str, timeout: int = 120) -> list:
    papers_for_prompt = [
        {"id": p["id"], "title": p["title"], "abstract": p["abstract"][:800],
         "year": p["year"], "citation_count": p.get("citation_count", 0)}
        for p in papers
    ]

    prompt = ANALYZE_PROMPT.format(
        n=len(papers),
        papers_json=json.dumps(papers_for_prompt, ensure_ascii=False),
    )

    payload = {
        "model": "local-model",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 2048,
    }

    try:
        r = requests.post(endpoint, json=payload, timeout=timeout)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()

        # Strip markdown fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        return json.loads(content)
    except json.JSONDecodeError as e:
        log.error("JSON parse error from Qwen: %s", e)
        return []
    except Exception as e:
        log.error("Qwen request failed: %s", e)
        return []


# ── Embedding + Upsert ────────────────────────────────────────────────────────

def upsert_papers(collection, papers: list, analyses: list, model: SentenceTransformer):
    analysis_map = {a["paper_id"]: a for a in analyses if "paper_id" in a}

    ids, embeddings, metadatas, documents = [], [], [], []

    for p in papers:
        analysis = analysis_map.get(p["id"], {})
        category = analysis.get("category", "E")
        if category == "E":
            continue  # Skip noise

        doc_text = f"{p['title']} {p['abstract'][:500]}"
        embedding = model.encode(doc_text).tolist()

        metadata = {
            "source": p.get("source", ""),
            "title": p.get("title", "")[:500],
            "journal": p.get("journal", ""),
            "year": p.get("year", 0),
            "citation_count": p.get("citation_count", 0),
            "doi": p.get("doi", ""),
            "url": p.get("url", ""),
            "species_hint": p.get("species_hint", ""),
            "credibility_level": p.get("credibility_level", 3),
            "credibility_weight": p.get("credibility_weight", 0.6),
            "category": category,
            "species": json.dumps(analysis.get("species", [])),
            "strategic_tags": json.dumps(analysis.get("strategic_tags", [])),
            "quality_score": analysis.get("quality_score", 3),
            "key_finding": analysis.get("key_finding", ""),
            "is_b_group": analysis.get("is_b_group", False),
            "metrics": json.dumps(analysis.get("metrics", {})),
        }

        ids.append(p["id"])
        embeddings.append(embedding)
        metadatas.append(metadata)
        documents.append(doc_text)

    if ids:
        collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
        log.info("Upserted %d papers to ChromaDB", len(ids))
    else:
        log.info("No papers to upsert (all noise or empty).")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Download from R2 and analyze with Qwen")
    parser.add_argument("--dry-run", action="store_true",
                        help="Download and analyze but do not write to ChromaDB")
    parser.add_argument("--local", metavar="FILE",
                        help="Use local JSON file instead of downloading from R2")
    args = parser.parse_args()

    cfg = load_config()
    settings = cfg["settings"]
    bucket = os.environ.get("CF_R2_BUCKET_NAME", "")
    db_path = settings["chromadb_path"]
    collection_name = settings["chromadb_collection"]
    endpoint = settings["qwen_endpoint"]
    batch_size = settings["batch_size"]
    batch_delay = settings["batch_delay_sec"]

    # Step 1: Load papers
    if args.local:
        with open(args.local, "r", encoding="utf-8") as f:
            papers = json.load(f)
        log.info("Loaded %d papers from local file: %s", len(papers), args.local)
    else:
        if not bucket:
            log.error("CF_R2_BUCKET_NAME not set and no --local file specified.")
            sys.exit(1)
        papers = download_latest(bucket)

    if not papers:
        log.info("No papers to process.")
        return

    # Step 2: Dedupe against ChromaDB
    if not args.dry_run:
        collection = get_collection(db_path, collection_name)
        existing_ids = get_existing_ids(collection)
        new_papers = [p for p in papers if p["id"] not in existing_ids]
        log.info("New papers after dedupe: %d / %d", len(new_papers), len(papers))
    else:
        collection = None
        new_papers = papers
        log.info("[dry-run] Skipping dedupe, processing all %d papers", len(new_papers))

    if not new_papers:
        log.info("Nothing new to process.")
        return

    # Step 3: Filter by credibility
    storable = [p for p in new_papers if p.get("credibility_level", 3) >= settings["store_threshold"]]
    log.info("Papers above store threshold (%d): %d", settings["store_threshold"], len(storable))

    # Step 4: Batch analyze with Qwen
    all_analyses = []
    total_batches = (len(storable) + batch_size - 1) // batch_size

    for i in range(0, len(storable), batch_size):
        batch = storable[i:i + batch_size]
        batch_num = i // batch_size + 1
        log.info("Analyzing batch %d/%d (%d papers)", batch_num, total_batches, len(batch))
        analyses = analyze_batch(batch, endpoint)
        log.info("  Got %d analysis results", len(analyses))
        all_analyses.extend(analyses)
        if i + batch_size < len(storable):
            time.sleep(batch_delay)

    # Step 5: Embed and upsert
    if not args.dry_run and collection is not None:
        log.info("Loading embedding model BAAI/bge-m3...")
        embed_model = SentenceTransformer("BAAI/bge-m3")
        upsert_papers(collection, storable, all_analyses, embed_model)
        log.info("Done. Total in collection: %d", collection.count())
    else:
        log.info("[dry-run] Sample analysis output:\n%s",
                 json.dumps(all_analyses[:2], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
