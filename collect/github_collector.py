"""
github_collector.py
Collects animal nutrition papers from PubMed, EuropePMC, and Lens.org (placeholder).
Outputs raw_papers.json for downstream scoring and analysis.
"""

import os
import sys
import json
import time
import hashlib
import argparse
import logging
from datetime import datetime, timezone

import requests
import yaml

logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                    format="%(asctime)s [collector] %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "configs", "species_metrics.yaml")

SPECIES_HINT_MAP = {
    "broiler": "broiler", "poultry": "broiler", "chicken": "broiler",
    "layer": "layer_hen", "eggshell": "layer_hen",
    "swine": "finisher_pig", "pig": "nursery_pig", "sow": "pregnant_sow",
    "shrimp": "shrimp", "prawn": "shrimp",
    "tilapia": "tilapia", "fish": "tilapia",
    "cattle": "livestock", "beef": "livestock", "dairy": "livestock",
    "sheep": "livestock", "lamb": "livestock",
    "aquaculture": "shrimp",
}


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def make_id(source: str, uid: str) -> str:
    return f"{source}_{uid}"


def infer_species(text: str) -> str:
    text_lower = text.lower()
    for kw, species in SPECIES_HINT_MAP.items():
        if kw in text_lower:
            return species
    return "unknown"


# ── PubMed ────────────────────────────────────────────────────────────────────

def fetch_pubmed(keywords: list, min_year: int, max_results: int, delay: float) -> list:
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    papers = []

    for kw in keywords:
        log.info("PubMed query: %s", kw)
        try:
            search_url = f"{base}esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": f"{kw} AND {min_year}:3000[pdat]",
                "retmax": max_results,
                "usehistory": "y",
                "retmode": "json",
                "sort": "relevance",
            }
            r = requests.get(search_url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            ids = data.get("esearchresult", {}).get("idlist", [])
            webenv = data["esearchresult"].get("webenv", "")
            query_key = data["esearchresult"].get("querykey", "")
            log.info("  Found %d PMIDs", len(ids))
            time.sleep(delay)

            if not ids:
                continue

            fetch_url = f"{base}efetch.fcgi"
            fetch_params = {
                "db": "pubmed",
                "query_key": query_key,
                "WebEnv": webenv,
                "rettype": "abstract",
                "retmode": "xml",
                "retmax": max_results,
            }
            fr = requests.get(fetch_url, params=fetch_params, timeout=60)
            fr.raise_for_status()
            time.sleep(delay)

            # Parse XML minimally
            import xml.etree.ElementTree as ET
            root = ET.fromstring(fr.content)
            for article in root.findall(".//PubmedArticle"):
                try:
                    pmid_el = article.find(".//PMID")
                    pmid = pmid_el.text if pmid_el is not None else "unknown"
                    title_el = article.find(".//ArticleTitle")
                    title = "".join(title_el.itertext()) if title_el is not None else ""
                    abstract_el = article.find(".//AbstractText")
                    abstract = "".join(abstract_el.itertext()) if abstract_el is not None else ""
                    journal_el = article.find(".//Journal/Title")
                    journal = journal_el.text if journal_el is not None else ""
                    year_el = article.find(".//PubDate/Year")
                    year_str = year_el.text if year_el is not None else "0"
                    try:
                        year = int(year_str)
                    except ValueError:
                        year = 0
                    author_els = article.findall(".//Author")
                    authors = []
                    for a in author_els[:5]:
                        ln = a.find("LastName")
                        fn = a.find("ForeName")
                        if ln is not None:
                            authors.append(f"{ln.text} {fn.text if fn is not None else ''}".strip())
                    doi_el = article.find(".//ArticleId[@IdType='doi']")
                    doi = doi_el.text if doi_el is not None else ""

                    if year < min_year:
                        continue

                    papers.append({
                        "id": make_id("pubmed", pmid),
                        "source": "pubmed",
                        "title": title,
                        "abstract": abstract,
                        "authors": authors,
                        "journal": journal,
                        "year": year,
                        "citation_count": 0,
                        "doi": doi,
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        "species_hint": infer_species(f"{kw} {title}"),
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception as e:
                    log.warning("  Parse error for article: %s", e)

        except Exception as e:
            log.error("PubMed error for query '%s': %s", kw, e)

    return papers


# ── EuropePMC ─────────────────────────────────────────────────────────────────

def fetch_europepmc(keywords: list, min_year: int, max_results: int, delay: float) -> list:
    base = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    papers = []

    for kw in keywords:
        log.info("EuropePMC query: %s", kw)
        try:
            params = {
                "query": f"{kw} AND FIRST_PDATE:[{min_year}-01-01 TO 9999-12-31]",
                "format": "json",
                "pageSize": max_results,
                "resultType": "core",
                "sort": "CITED desc",
            }
            r = requests.get(base, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            results = data.get("resultList", {}).get("result", [])
            log.info("  Found %d results", len(results))
            time.sleep(delay)

            for item in results:
                try:
                    year = int(item.get("pubYear", 0))
                    if year < min_year:
                        continue
                    uid = item.get("pmid") or item.get("id") or hashlib.md5(
                        item.get("title", "").encode()).hexdigest()[:8]
                    papers.append({
                        "id": make_id("europepmc", str(uid)),
                        "source": "europepmc",
                        "title": item.get("title", ""),
                        "abstract": item.get("abstractText", ""),
                        "authors": [a.get("fullName", "") for a in
                                    item.get("authorList", {}).get("author", [])[:5]],
                        "journal": item.get("journalTitle", ""),
                        "year": year,
                        "citation_count": item.get("citedByCount", 0),
                        "doi": item.get("doi", ""),
                        "url": f"https://europepmc.org/article/{item.get('source','MED')}/{uid}",
                        "species_hint": infer_species(f"{kw} {item.get('title','')}"),
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception as e:
                    log.warning("  Parse error: %s", e)

        except Exception as e:
            log.error("EuropePMC error for query '%s': %s", kw, e)

    return papers


# ── Lens.org Placeholder ───────────────────────────────────────────────────────

def fetch_lens_scholarly(keywords: list, min_year: int, max_results: int) -> list:
    token = os.environ.get("LENS_API_TOKEN", "")
    if not token:
        log.warning("LENS_API_TOKEN not set — skipping Lens Scholarly.")
        return []

    base = "https://api.lens.org/scholarly/search"
    papers = []
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    for kw in keywords:
        log.info("Lens Scholarly query: %s", kw)
        try:
            payload = {
                "query": {"match": {"abstract": kw}},
                "filter": {"range": {"year_published": {"gte": min_year}}},
                "sort": [{"_score": "desc"}],
                "size": max_results,
                "include": ["lens_id", "title", "abstract", "authors",
                            "publication", "year_published", "scholarly_citations_count", "doi"],
            }
            r = requests.post(base, json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            for item in r.json().get("data", []):
                try:
                    papers.append({
                        "id": make_id("lens_scholarly", item.get("lens_id", "")),
                        "source": "lens_scholarly",
                        "title": item.get("title", ""),
                        "abstract": item.get("abstract", ""),
                        "authors": [a.get("display_name", "") for a in item.get("authors", [])[:5]],
                        "journal": item.get("publication", {}).get("title", ""),
                        "year": item.get("year_published", 0),
                        "citation_count": item.get("scholarly_citations_count", 0),
                        "doi": item.get("doi", ""),
                        "url": f"https://www.lens.org/lens/scholar/article/{item.get('lens_id','')}",
                        "species_hint": infer_species(f"{kw} {item.get('title','')}"),
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception as e:
                    log.warning("  Lens parse error: %s", e)
        except Exception as e:
            log.error("Lens Scholarly error for '%s': %s", kw, e)

    return papers


def fetch_lens_patent(keywords: list, min_year: int, max_results: int) -> list:
    token = os.environ.get("LENS_API_TOKEN", "")
    if not token:
        log.warning("LENS_API_TOKEN not set — skipping Lens Patent.")
        return []

    base = "https://api.lens.org/patent/search"
    papers = []
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    for kw in keywords:
        log.info("Lens Patent query: %s", kw)
        try:
            payload = {
                "query": {
                    "bool": {
                        "must": [{"match": {"description": kw}}],
                        "filter": [{"term": {"classifications_ipcr.symbol": "A23K"}}],
                    }
                },
                "size": max_results,
                "include": ["lens_id", "title", "abstract", "applicants",
                            "date_published", "doc_number", "jurisdiction"],
            }
            r = requests.post(base, json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            for item in r.json().get("data", []):
                try:
                    year_str = (item.get("date_published") or "0000")[:4]
                    year = int(year_str) if year_str.isdigit() else 0
                    papers.append({
                        "id": make_id("lens_patent", item.get("lens_id", "")),
                        "source": "lens_patent",
                        "title": item.get("title", ""),
                        "abstract": item.get("abstract", ""),
                        "authors": [a.get("display_name", "")
                                    for a in item.get("applicants", [])[:5]],
                        "journal": f"Patent {item.get('jurisdiction','')} {item.get('doc_number','')}",
                        "year": year,
                        "citation_count": 0,
                        "doi": "",
                        "url": f"https://www.lens.org/lens/patent/{item.get('lens_id','')}",
                        "species_hint": infer_species(f"{kw} {item.get('title','')}"),
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception as e:
                    log.warning("  Lens patent parse error: %s", e)
        except Exception as e:
            log.error("Lens Patent error for '%s': %s", kw, e)

    return papers


# ── Dedup ─────────────────────────────────────────────────────────────────────

def dedupe(papers: list) -> list:
    seen_ids = set()
    seen_titles = set()
    result = []
    for p in papers:
        pid = p.get("id", "")
        title_key = p.get("title", "").lower().strip()[:80]
        if pid in seen_ids or title_key in seen_titles:
            continue
        seen_ids.add(pid)
        if title_key:
            seen_titles.add(title_key)
        result.append(p)
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Collect animal nutrition papers")
    parser.add_argument("--output", default="raw_papers.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run collection but do not write output file")
    args = parser.parse_args()

    cfg = load_config()
    keywords = cfg["search_keywords"]["en"]
    min_year = cfg["settings"]["min_year"]
    max_results = cfg["settings"]["max_results_per_query"]
    delay = cfg["settings"]["request_delay_sec"]

    all_papers = []
    all_papers += fetch_pubmed(keywords, min_year, max_results, delay)
    all_papers += fetch_europepmc(keywords, min_year, max_results, delay)
    all_papers += fetch_lens_scholarly(keywords, min_year, max_results)
    all_papers += fetch_lens_patent(keywords[:3], min_year, max_results)

    deduped = dedupe(all_papers)
    log.info("Total collected: %d | After dedupe: %d", len(all_papers), len(deduped))

    if args.dry_run:
        log.info("[dry-run] Skipping file write. Sample:\n%s",
                 json.dumps(deduped[:2], ensure_ascii=False, indent=2))
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(deduped, f, ensure_ascii=False, indent=2)
        log.info("Written %d papers to %s", len(deduped), args.output)


if __name__ == "__main__":
    main()
