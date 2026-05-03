"""
credibility_scorer.py
Scores papers 1-5 based on source credibility for B-group comparison database.
Level 1 = noise (not stored), Level 5 = gold standard.
"""

import sys
import json
import argparse
import logging

logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                    format="%(asctime)s [scorer] %(levelname)s %(message)s")
log = logging.getLogger(__name__)

STORE_THRESHOLD = 2
QUERY_DEFAULT_MIN = 3
HIGHLIGHT_THRESHOLD = 4

LEVEL_WEIGHTS = {5: 1.0, 4: 0.8, 3: 0.6, 2: 0.3, 1: 0.1}

HIGH_IF_JOURNALS = {
    "journal of animal science",
    "poultry science",
    "animal feed science and technology",
    "aquaculture",
    "livestock science",
    "animal",
    "british journal of nutrition",
    "journal of nutrition",
    "frontiers in veterinary science",
    "veterinary microbiology",
}

TRUSTED_COMPANIES = {
    "dsm", "kemin", "novozymes", "basf", "dupont", "evonik",
    "adm", "cargill", "AB vista", "alltech",
}

BREED_STANDARD_SOURCES = {
    "aviagen", "cobb", "pic", "hendrix", "hy-line", "lohmann",
}

OFFICIAL_SOURCES = {
    "efsa", "fao", "who", "usda", "coa", "council of agriculture",
}

TRADE_MEDIA = {
    "feednavigator", "wattagnet", "wattpoultry", "pigprogress",
    "aquaculturemag", "the fish site", "global aquaculture advocate",
    "poultry world", "feedstuffs",
}

NOISE_INDICATORS = {
    "blog", "forum", "reddit", "facebook", "twitter", "instagram",
    "linkedin post", "wechat", "weibo",
}


def score_paper(paper: dict) -> int:
    """
    Score a single paper 1-5.
    Returns credibility level integer.
    """
    title = (paper.get("title") or "").lower()
    abstract = (paper.get("abstract") or "").lower()
    journal = (paper.get("journal") or "").lower()
    source = (paper.get("source") or "").lower()
    citation_count = paper.get("citation_count") or 0
    year = paper.get("year") or 9999
    authors = " ".join(paper.get("authors") or []).lower()
    url = (paper.get("url") or "").lower()

    combined_text = f"{title} {abstract} {journal} {source} {authors} {url}"

    # Level 5: meta-analysis or official body
    if "meta-analysis" in combined_text or "systematic review" in combined_text:
        return 5
    for src in OFFICIAL_SOURCES:
        if src in combined_text:
            return 5
    for src in BREED_STANDARD_SOURCES:
        if src in combined_text:
            return 5

    # Level 4: highly cited classic OR high-IF journal OR trusted company
    if citation_count >= 50 and year <= 2015:
        return 4
    for j in HIGH_IF_JOURNALS:
        if j in journal:
            return 4
    for company in TRUSTED_COMPANIES:
        if company in combined_text:
            return 4

    # Level 1: noise
    for noise in NOISE_INDICATORS:
        if noise in combined_text:
            return 1

    # Level 3: trade media or academic source (pubmed/europepmc default)
    for media in TRADE_MEDIA:
        if media in combined_text:
            return 3
    if source in ("pubmed", "europepmc", "lens_scholarly"):
        return 3

    # Level 2: everything else (company claims, press releases)
    return 2


def score_batch(papers: list) -> list:
    """Add credibility_level and credibility_weight fields to each paper."""
    results = []
    for p in papers:
        level = score_paper(p)
        p["credibility_level"] = level
        p["credibility_weight"] = LEVEL_WEIGHTS[level]
        results.append(p)
    log.info("Scored %d papers. Distribution: %s", len(results),
             {lvl: sum(1 for p in results if p["credibility_level"] == lvl)
              for lvl in range(1, 6)})
    return results


def filter_by_level(papers: list, min_level: int = QUERY_DEFAULT_MIN) -> list:
    """Filter papers to only those at or above min_level."""
    return [p for p in papers if p.get("credibility_level", 0) >= min_level]


def main():
    parser = argparse.ArgumentParser(description="Score paper credibility")
    parser.add_argument("--input", default="raw_papers.json")
    parser.add_argument("--output", default="raw_papers.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        papers = json.load(f)

    log.info("Loaded %d papers from %s", len(papers), args.input)
    scored = score_batch(papers)
    storable = [p for p in scored if p["credibility_level"] >= STORE_THRESHOLD]
    log.info("Storable (level >= %d): %d / %d", STORE_THRESHOLD, len(storable), len(scored))

    if not args.dry_run:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(scored, f, ensure_ascii=False, indent=2)
        log.info("Written scored papers to %s", args.output)
    else:
        log.info("[dry-run] Skipped writing output.")


if __name__ == "__main__":
    main()
