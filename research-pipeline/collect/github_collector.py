"""
github_collector.py
多源爬蟲：PubMed / Semantic Scholar / EuropePMC / Lens.org / RSS / Vendor scraper
從 configs/ingredients.yaml 讀取原料清單 → 產出 /tmp/raw_papers_collected.json
只抓 Abstract + Metadata，不下載 PDF
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import yaml
import feedparser
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)

# ── 設定 ──────────────────────────────────────────────────────────────────────
OUTPUT_PATH   = Path("/tmp/raw_papers_collected.json")
INGREDIENTS_P = Path("configs/ingredients.yaml")

S2_API_KEY    = os.environ.get("SEMANTIC_SCHOLAR_KEY", "")
LENS_TOKEN    = os.environ.get("LENS_API_TOKEN", "")
FORCE_FULL    = os.environ.get("FORCE_FULL", "false").lower() == "true"
TOPICS_FILTER = os.environ.get("TOPICS_FILTER", "").strip()

# 增量：只爬近 N 天（full run 爬 365 天）
INCREMENTAL_DAYS = 8
LOOKBACK_DAYS    = 365 if FORCE_FULL else INCREMENTAL_DAYS
SINCE_DATE       = (datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y/%m/%d")
SINCE_DATE_ISO   = (datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")

# 每個 source 最大筆數限制（防止 Actions 超時）
MAX_PER_QUERY = 100 if FORCE_FULL else 30

# ── 載入 ingredients.yaml ────────────────────────────────────────────────────
def load_ingredients():
    with open(INGREDIENTS_P, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    items = cfg.get("ingredients", [])
    log.info(f"Loaded {len(items)} ingredients")
    return items

def build_search_queries(ingredients: list) -> list[dict]:
    """每個 ingredient 的 EN 別名展開成搜尋關鍵字組"""
    queries = []
    seen_ids = set()
    for ing in ingredients:
        if ing["id"] in seen_ids:
            continue
        seen_ids.add(ing["id"])

        # 只用 role=core/adjacent 的原料主動搜尋
        # role=competitor 只在 vendor scraper 被動捕捉
        if ing.get("role") == "competitor" and ing.get("strategy") == "b_group_only":
            # 競品原料只加入 alias 表，不主動搜尋
            continue

        aliases_en = ing.get("aliases", {}).get("en", [])
        if not aliases_en:
            continue

        # 主要關鍵字：取前 3 個最具代表性的 alias
        primary = aliases_en[:3]
        # 動物應用限縮詞（讓搜尋更精準）
        animal_terms = ["broiler", "poultry", "swine", "pig", "shrimp",
                        "fish", "aquaculture", "livestock", "cattle",
                        "layer", "feed additive", "animal nutrition"]

        queries.append({
            "ingredient_id": ing["id"],
            "display": ing["display"],
            "primary_aliases": primary,
            "all_aliases_en": aliases_en,
            "animal_terms": animal_terms,
            "role": ing.get("role"),
            "strategy": ing.get("strategy"),
        })

    if TOPICS_FILTER:
        ids = [t.strip() for t in TOPICS_FILTER.split(",")]
        queries = [q for q in queries if q["ingredient_id"] in ids]
        log.info(f"Filtered to topics: {ids}")

    log.info(f"Search queries: {len(queries)} ingredients")
    return queries


# ── 去重 hash ─────────────────────────────────────────────────────────────────
def paper_id(title: str, doi: str = "") -> str:
    key = (doi or title or "").lower().strip()
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# ── PubMed ────────────────────────────────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def fetch_pubmed(client: httpx.AsyncClient, query: dict) -> list[dict]:
    results = []
    aliases = query["primary_aliases"]
    animal  = query["animal_terms"]

    # 建立 PubMed 搜尋式
    alias_clause  = " OR ".join(f'"{a}"[tiab]' for a in aliases)
    animal_clause = " OR ".join(f'"{t}"[tiab]' for t in animal[:6])
    search_term   = f"({alias_clause}) AND ({animal_clause})"
    if not FORCE_FULL:
        search_term += f" AND (\"{SINCE_DATE}\"[PDAT]:\"3000\"[PDAT])"

    # Step 1: esearch
    r = await client.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params={"db": "pubmed", "term": search_term,
                "retmax": MAX_PER_QUERY, "retmode": "json"},
        timeout=30
    )
    ids = r.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    # Step 2: efetch abstracts
    r2 = await client.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        params={"db": "pubmed", "id": ",".join(ids),
                "rettype": "abstract", "retmode": "xml"},
        timeout=60
    )
    soup = BeautifulSoup(r2.text, "lxml-xml")
    for article in soup.find_all("PubmedArticle"):
        try:
            pmid  = article.find("PMID").text if article.find("PMID") else ""
            title = article.find("ArticleTitle").text if article.find("ArticleTitle") else ""
            ab    = article.find("AbstractText")
            abstract = ab.text if ab else ""
            if not abstract:
                continue
            year_tag = article.find("PubDate")
            year = int(year_tag.find("Year").text) if year_tag and year_tag.find("Year") else 0
            authors = [
                f"{a.find('LastName').text if a.find('LastName') else ''} "
                f"{a.find('Initials').text if a.find('Initials') else ''}".strip()
                for a in article.find_all("Author")[:5]
            ]
            doi_tag = article.find("ArticleId", IdType="doi")
            doi = doi_tag.text if doi_tag else ""

            results.append({
                "id":            paper_id(title, doi),
                "title":         title,
                "abstract":      abstract[:2000],
                "authors":       "; ".join(authors),
                "year":          year,
                "doi":           doi,
                "source_url":    f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "source_type":   "paper",
                "source_db":     "pubmed",
                "language":      "en",
                "ingredient_hint": query["ingredient_id"],
                "collected_at":  datetime.utcnow().isoformat(),
            })
        except Exception as e:
            log.debug(f"PubMed parse error: {e}")

    log.info(f"PubMed [{query['ingredient_id']}]: {len(results)} papers")
    return results


# ── Semantic Scholar ──────────────────────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def fetch_s2(client: httpx.AsyncClient, query: dict) -> list[dict]:
    results = []
    headers = {"x-api-key": S2_API_KEY} if S2_API_KEY else {}
    aliases = query["primary_aliases"]

    for alias in aliases[:2]:  # 最多 2 個 alias 避免超 quota
        search_q = f"{alias} animal feed"
        params = {
            "query": search_q,
            "limit": MAX_PER_QUERY,
            "fields": "title,abstract,authors,year,externalIds,citationCount,publicationDate",
        }
        if not FORCE_FULL:
            params["publicationDateOrYear"] = f"{SINCE_DATE_ISO}:"

        try:
            r = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params=params, headers=headers, timeout=30
            )
            data = r.json()
        except Exception as e:
            log.warning(f"S2 error: {e}")
            continue

        for p in data.get("data", []):
            abstract = p.get("abstract") or ""
            if not abstract or len(abstract) < 50:
                continue
            doi = (p.get("externalIds") or {}).get("DOI", "")
            authors = [
                a.get("name", "") for a in (p.get("authors") or [])[:5]
            ]
            results.append({
                "id":             paper_id(p.get("title",""), doi),
                "title":          p.get("title", ""),
                "abstract":       abstract[:2000],
                "authors":        "; ".join(authors),
                "year":           p.get("year") or 0,
                "doi":            doi,
                "citation_count": p.get("citationCount") or 0,
                "source_url":     f"https://www.semanticscholar.org/paper/{p.get('paperId','')}",
                "source_type":    "paper",
                "source_db":      "semantic_scholar",
                "language":       "en",
                "ingredient_hint": query["ingredient_id"],
                "collected_at":   datetime.utcnow().isoformat(),
            })
        await asyncio.sleep(1)  # S2 rate limit

    log.info(f"S2 [{query['ingredient_id']}]: {len(results)} papers")
    return results


# ── EuropePMC ─────────────────────────────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def fetch_europepmc(client: httpx.AsyncClient, query: dict) -> list[dict]:
    results = []
    alias = query["primary_aliases"][0]
    search_q = f'("{alias}") AND (broiler OR poultry OR swine OR shrimp OR fish OR livestock)'
    if not FORCE_FULL:
        search_q += f" AND FIRST_PDATE:[{SINCE_DATE_ISO} TO *]"

    r = await client.get(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        params={
            "query": search_q,
            "resultType": "core",
            "pageSize": MAX_PER_QUERY,
            "format": "json",
        },
        timeout=30
    )
    for p in r.json().get("resultList", {}).get("result", []):
        abstract = p.get("abstractText") or ""
        if not abstract:
            continue
        results.append({
            "id":            paper_id(p.get("title",""), p.get("doi","")),
            "title":         p.get("title", ""),
            "abstract":      abstract[:2000],
            "authors":       p.get("authorString", ""),
            "year":          int(p.get("pubYear") or 0),
            "doi":           p.get("doi", ""),
            "citation_count": int(p.get("citedByCount") or 0),
            "source_url":    f"https://europepmc.org/article/{p.get('source','')}/{p.get('id','')}",
            "source_type":   "paper",
            "source_db":     "europepmc",
            "language":      "en",
            "ingredient_hint": query["ingredient_id"],
            "collected_at":  datetime.utcnow().isoformat(),
        })

    log.info(f"EuropePMC [{query['ingredient_id']}]: {len(results)} papers")
    return results


# ── Lens.org 專利 ─────────────────────────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def fetch_lens_patents(client: httpx.AsyncClient, query: dict) -> list[dict]:
    if not LENS_TOKEN:
        return []
    results = []
    aliases = query["primary_aliases"][:3]

    payload = {
        "query": {
            "bool": {
                "must": [
                    {"terms": {"claims.text": aliases}},
                    {"terms": {"abstract.text": [
                        "broiler","poultry","swine","shrimp","aquaculture",
                        "animal feed","livestock","feed additive"
                    ]}}
                ]
            }
        },
        "include": ["lens_id","title","abstract","inventor","owner",
                    "publication_date","jurisdiction","doc_number"],
        "size": min(MAX_PER_QUERY, 50),
        "sort": [{"publication_date": "desc"}],
    }
    if not FORCE_FULL:
        payload["query"]["bool"]["filter"] = [
            {"range": {"publication_date": {"gte": SINCE_DATE_ISO}}}
        ]

    r = await client.post(
        "https://api.lens.org/patent/search",
        json=payload,
        headers={"Authorization": f"Bearer {LENS_TOKEN}",
                 "Content-Type": "application/json"},
        timeout=30
    )
    for p in r.json().get("data", []):
        abstract = (p.get("abstract") or [{}])[0].get("text", "")
        if not abstract:
            continue
        title = (p.get("title") or [{}])[0].get("text", "")
        results.append({
            "id":            paper_id(title, p.get("doc_number","")),
            "title":         title,
            "abstract":      abstract[:2000],
            "authors":       "; ".join(
                [i.get("name","") for i in (p.get("inventor") or [])[:5]]
            ),
            "year":          int((p.get("publication_date") or "0")[:4]),
            "doi":           "",
            "patent_number": p.get("doc_number",""),
            "jurisdiction":  p.get("jurisdiction",""),
            "source_url":    f"https://www.lens.org/lens/patent/{p.get('lens_id','')}",
            "source_type":   "patent",
            "source_db":     "lens",
            "language":      "en",
            "ingredient_hint": query["ingredient_id"],
            "collected_at":  datetime.utcnow().isoformat(),
        })

    log.info(f"Lens.org [{query['ingredient_id']}]: {len(results)} patents")
    return results


# ── RSS 行業媒體 ──────────────────────────────────────────────────────────────
RSS_FEEDS = [
    {"url": "https://www.feednavigator.com/rss/feed",        "name": "FeedNavigator"},
    {"url": "https://www.wattagnet.com/rss.xml",             "name": "WATTPoultry"},
    {"url": "https://www.pigprogress.net/rss",               "name": "PigProgress"},
    {"url": "https://www.aquaculturenorth.com/feed",         "name": "AquacultureNorth"},
    {"url": "https://www.globalseafood.org/feed",            "name": "GSAA"},
    {"url": "https://www.allaboutfeed.net/rss",              "name": "AllAboutFeed"},
    {"url": "https://www.thepigsite.com/rss",                "name": "ThePigSite"},
    {"url": "https://thepoultrysite.com/rss",                "name": "ThePoultrysite"},
]

async def fetch_rss(client: httpx.AsyncClient,
                    all_aliases: set[str]) -> list[dict]:
    results = []
    alias_lower = {a.lower() for a in all_aliases}

    for feed_info in RSS_FEEDS:
        try:
            r = await client.get(feed_info["url"], timeout=20,
                                 follow_redirects=True)
            feed = feedparser.parse(r.text)
        except Exception as e:
            log.warning(f"RSS {feed_info['name']}: {e}")
            continue

        for entry in feed.entries[:50]:
            title   = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description","")
            content = (title + " " + summary).lower()

            # 只收錄包含 alias 的文章
            matched = [a for a in alias_lower if a in content]
            if not matched:
                continue

            pub_date = entry.get("published", "")
            results.append({
                "id":            paper_id(title, entry.get("link","")),
                "title":         title,
                "abstract":      summary[:2000],
                "authors":       entry.get("author",""),
                "year":          int(pub_date[:4]) if pub_date and pub_date[:4].isdigit() else 0,
                "doi":           "",
                "source_url":    entry.get("link",""),
                "source_type":   "industry_media",
                "source_db":     feed_info["name"],
                "language":      "en",
                "ingredient_hint": matched[0],
                "collected_at":  datetime.utcnow().isoformat(),
            })

    log.info(f"RSS total: {len(results)} articles")
    return results


# ── Vendor Scraper（東南亞廠商 + 競品）────────────────────────────────────────
# 用 Google Custom Search 自動找有技術文件的廠商頁面
VENDOR_SEARCH_QUERIES = [
    "site:*.th feed additive octacosanol OR triacontanol OR astaxanthin",
    "site:*.id pakan ternak feed additive long chain alcohol",
    "site:*.my feed additive aquaculture astaxanthin policosanol",
    "site:*.ph feed supplement poultry aquaculture performance",
    "site:*.vn thuc an chan nuoi astaxanthin feed additive",
    "CP Group technical brochure feed additive performance",
    "Japfa Comfeed feed additive technical data",
    "Charoen Pokphand feed supplement trial results",
]

async def scrape_vendor_pages(client: httpx.AsyncClient,
                              all_aliases: set[str]) -> list[dict]:
    """
    簡化版：直接爬已知廠商技術頁面
    完整版需要 Google Custom Search API key（可選）
    """
    results = []
    # 固定已知高價值頁面清單（可持續補充）
    KNOWN_VENDOR_URLS = [
        "https://www.dsm.com/animal-nutrition/en/products.html",
        "https://www.kemin.com/en/animal-nutrition-and-health/solutions",
        "https://www.novonesis.com/en/animal-health-nutrition",
        "https://www.adisseo.com/en/solutions/poultry",
        "https://www.evonik.com/en/products/animal-nutrition",
    ]
    alias_lower = {a.lower() for a in all_aliases}

    for url in KNOWN_VENDOR_URLS:
        try:
            r = await client.get(url, timeout=20, follow_redirects=True)
            soup = BeautifulSoup(r.text, "lxml")
            # 找包含 alias 的段落
            for tag in soup.find_all(["p", "li", "div"], limit=200):
                text = tag.get_text(" ", strip=True)
                if len(text) < 50 or len(text) > 2000:
                    continue
                matched = [a for a in alias_lower if a in text.lower()]
                if not matched:
                    continue
                results.append({
                    "id":            paper_id(text[:100], url),
                    "title":         soup.find("title").text if soup.find("title") else url,
                    "abstract":      text[:2000],
                    "authors":       "",
                    "year":          datetime.utcnow().year,
                    "doi":           "",
                    "source_url":    url,
                    "source_type":   "vendor_claim",
                    "source_db":     "vendor_scraper",
                    "language":      "en",
                    "ingredient_hint": matched[0],
                    "collected_at":  datetime.utcnow().isoformat(),
                })
            await asyncio.sleep(2)
        except Exception as e:
            log.warning(f"Vendor scrape {url}: {e}")

    log.info(f"Vendor scraper: {len(results)} claims")
    return results


# ── 去重合併 ──────────────────────────────────────────────────────────────────
def dedupe(papers: list[dict]) -> list[dict]:
    seen = {}
    for p in papers:
        pid = p["id"]
        if pid not in seen:
            seen[pid] = p
        else:
            # 保留 citation_count 較高的版本
            if p.get("citation_count",0) > seen[pid].get("citation_count",0):
                seen[pid] = p
    log.info(f"Dedupe: {len(papers)} → {len(seen)}")
    return list(seen.values())


# ── 主程式 ────────────────────────────────────────────────────────────────────
import asyncio

async def main():
    ingredients = load_ingredients()
    queries     = build_search_queries(ingredients)

    # 所有 alias 集合（供 RSS + Vendor 使用）
    all_aliases: set[str] = set()
    for ing in ingredients:
        all_aliases.update(ing.get("aliases", {}).get("en", []))

    all_papers: list[dict] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": "research-pipeline/3.0 (academic use)"},
        follow_redirects=True,
    ) as client:

        # 學術來源：每個 ingredient 並發爬取
        for q in queries:
            log.info(f"=== {q['ingredient_id']} ===")
            tasks = [
                fetch_pubmed(client, q),
                fetch_s2(client, q),
                fetch_europepmc(client, q),
                fetch_lens_patents(client, q),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    all_papers.extend(r)
                elif isinstance(r, Exception):
                    log.warning(f"Source error: {r}")
            await asyncio.sleep(2)  # 避免 rate limit

        # RSS（一次性，不按 ingredient 分）
        rss_papers = await fetch_rss(client, all_aliases)
        all_papers.extend(rss_papers)

        # Vendor scraper
        vendor_papers = await scrape_vendor_pages(client, all_aliases)
        all_papers.extend(vendor_papers)

    # 去重
    final_papers = dedupe(all_papers)

    # 輸出
    output = {
        "collected_at": datetime.utcnow().isoformat(),
        "lookback_days": LOOKBACK_DAYS,
        "total": len(final_papers),
        "papers": final_papers,
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    log.info(f"Done. Total: {len(final_papers)} → {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
