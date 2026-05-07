"""
credibility_scorer.py
讀取 /tmp/raw_papers_collected.json → 每筆打 L1-L5 信心度 → 輸出 scored.json
不需要 LLM，純規則評分
"""

import json
import argparse
import logging
from pathlib import Path

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

# L5 關鍵字
L5_TITLE_KEYWORDS = [
    "meta-analysis","systematic review","meta analysis",
    "efsa opinion","fao report","breed standard","aviagen","cobb","hy-line","isa brown",
]
L5_SOURCE_DOMAINS = ["efsa.europa.eu","fao.org","apps.who.int"]

# L4 高引用期刊（部分 journal 名）
L4_JOURNALS = [
    "poultry science","journal of animal science","animal feed science",
    "aquaculture","journal of nutrition","british journal of nutrition",
    "livestock science","meat science","animal","frontiers in veterinary",
]
L4_SUPPLIERS = ["dsm","kemin","novozymes","novonesis","basf","evonik","adisseo","alltech"]

# L1 雜訊域名
L1_DOMAINS = ["blogspot","wordpress","medium.com","reddit","quora","zhihu"]


def score(paper: dict) -> int:
    title  = (paper.get("title","") or "").lower()
    ab     = (paper.get("abstract","") or "").lower()
    url    = (paper.get("source_url","") or "").lower()
    stype  = paper.get("source_type","")
    cites  = paper.get("citation_count") or 0
    year   = paper.get("year") or 0

    # L1：雜訊
    if any(d in url for d in L1_DOMAINS):
        return 1
    if stype == "social":
        return 1
    if len(ab) < 80:
        return 1

    # L5：最高可信
    if any(k in title for k in L5_TITLE_KEYWORDS):
        return 5
    if any(d in url for d in L5_SOURCE_DOMAINS):
        return 5

    # L4：高可信
    if stype == "paper":
        if cites >= 50 and year <= 2015:
            return 4
        if any(j in ab or j in title for j in L4_JOURNALS):
            return 4
    if stype == "whitepaper":
        if any(s in url or s in ab for s in L4_SUPPLIERS):
            return 4

    # L3：中可信
    if stype == "paper":
        return 3
    if stype == "patent":
        return 3
    if stype == "industry_media":
        return 3

    # L2：低可信（廠商宣稱）
    if stype == "vendor_claim":
        return 2

    return 2  # 預設


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default="/tmp/raw_papers_collected.json")
    parser.add_argument("--output", default="/tmp/raw_papers_scored.json")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    papers = data.get("papers", [])

    dist = {1:0, 2:0, 3:0, 4:0, 5:0}
    for p in papers:
        lvl = score(p)
        p["credibility"] = lvl
        dist[lvl] += 1

    # L1 標記為 category E（skip embedding）
    for p in papers:
        if p["credibility"] == 1:
            p["skip"] = True

    data["papers"] = papers
    data["credibility_dist"] = dist
    Path(args.output).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log.info(f"Scored {len(papers)} papers")
    for lvl in range(5,0,-1):
        log.info(f"  L{lvl}: {dist[lvl]}")


if __name__ == "__main__":
    main()
