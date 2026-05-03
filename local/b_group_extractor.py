"""
b_group_extractor.py
Query ChromaDB for B-group market claim data by species and metric.
"""

import os
import sys
import json
import argparse
import logging

import chromadb
import yaml

logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                    format="%(asctime)s [b_group] %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "configs", "species_metrics.yaml")


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_collection(cfg: dict):
    settings = cfg["settings"]
    client = chromadb.PersistentClient(path=settings["chromadb_path"])
    return client.get_or_create_collection(settings["chromadb_collection"])


def extract_b_group_metrics(species: str, metric: str,
                             min_credibility: int = 3,
                             collection=None, cfg: dict = None) -> list:
    """
    Query ChromaDB for B-group papers matching species + metric.
    Returns list of market claim records sorted by credibility descending.
    """
    if cfg is None:
        cfg = load_config()
    if collection is None:
        collection = get_collection(cfg)

    # Query with species as semantic search term
    query_text = f"{species} {metric} performance feed additive"
    results = collection.query(
        query_texts=[query_text],
        n_results=50,
        where={"is_b_group": True},
        include=["metadatas", "documents"],
    )

    claims = []
    metadatas = results.get("metadatas", [[]])[0]

    for meta in metadatas:
        if meta.get("credibility_level", 0) < min_credibility:
            continue

        # Check if species matches
        paper_species = json.loads(meta.get("species", "[]"))
        if species not in paper_species and meta.get("species_hint", "") != species:
            # Still include if metric found in metrics field
            pass

        # Parse metrics
        raw_metrics = json.loads(meta.get("metrics", "{}"))
        if metric not in raw_metrics:
            continue

        m = raw_metrics[metric]
        claims.append({
            "value": m.get("value"),
            "change_pct": m.get("change_pct"),
            "unit": m.get("unit", ""),
            "source": f"{meta.get('title', 'Unknown')[:60]} ({meta.get('journal', '')} {meta.get('year', '')})",
            "credibility_level": meta.get("credibility_level", 0),
            "credibility_weight": meta.get("credibility_weight", 0.0),
            "year": meta.get("year", 0),
            "doi": meta.get("doi", ""),
            "url": meta.get("url", ""),
        })

    # Sort by credibility desc, then year desc
    claims.sort(key=lambda x: (x["credibility_level"], x["year"]), reverse=True)
    log.info("Found %d B-group claims for %s / %s (min_credibility=%d)",
             len(claims), species, metric, min_credibility)
    return claims


def main():
    parser = argparse.ArgumentParser(description="Extract B-group market claims from ChromaDB")
    parser.add_argument("--species", required=True, help="e.g. finisher_pig")
    parser.add_argument("--metric", required=True, help="e.g. FCR")
    parser.add_argument("--min-credibility", type=int, default=3)
    parser.add_argument("--output", choices=["json", "text"], default="text")
    args = parser.parse_args()

    cfg = load_config()

    # Validate species
    valid_species = list(cfg["species"].keys())
    if args.species not in valid_species:
        log.error("Unknown species '%s'. Valid: %s", args.species, valid_species)
        sys.exit(1)

    # Validate metric
    valid_metrics = cfg["species"][args.species]["metrics"]
    if args.metric not in valid_metrics:
        log.warning("Metric '%s' not in species config. Proceeding anyway.", args.metric)

    collection = get_collection(cfg)
    claims = extract_b_group_metrics(
        args.species, args.metric, args.min_credibility, collection, cfg
    )

    if args.output == "json":
        print(json.dumps(claims, ensure_ascii=False, indent=2))
    else:
        if not claims:
            print(f"No B-group claims found for {args.species} / {args.metric}")
        else:
            print(f"\nB-group claims: {args.species} / {args.metric}")
            print("-" * 60)
            for c in claims:
                bar = "█" * c["credibility_level"] + "░" * (5 - c["credibility_level"])
                change = f"{c['change_pct']:+.1f}%" if c.get("change_pct") is not None else "N/A"
                print(f"[L{c['credibility_level']} {bar}] {c['value']} {c['unit']} "
                      f"({change}) | {c['year']} | {c['source'][:50]}")


if __name__ == "__main__":
    main()
