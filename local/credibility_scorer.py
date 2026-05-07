"""
credibility_scorer.py  v2.0
讀取 /tmp/raw_papers_collected.json → 每筆打 L1-L5 信心度 → 輸出 scored.json
不需要 LLM，純規則評分

升級 v2.0：
- 加入動物營養 / 飼料添加劑 / AB試驗特定規則
- 區分 RCT 田間試驗 vs 體外試驗
- 品種公司手冊 = L5
- 加入 MG/AGP-free 主題識別
- 加入中文期刊識別
- 加入 LCFA/policosanol 研究特定關鍵字加權
"""

import json
import argparse
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")


# ── L5：最高可信度 ─────────────────────────────────────────────────────────────
# 品種公司官方手冊、FAO、EFSA、meta-analysis、systematic review
L5_TITLE_KEYWORDS = [
    "meta-analysis", "systematic review", "meta analysis",
    "efsa opinion", "fao report", "breed standard",
    # 品種公司
    "aviagen", "cobb", "hy-line", "isa brown", "lohmann", "ross 308",
    "pic sow", "topigs", "genus pic", "cherry valley",
    # 高等級機構報告
    "cochrane", "who technical report", "ipcc",
]
L5_SOURCE_DOMAINS = [
    "efsa.europa.eu", "fao.org", "apps.who.int",
    "aviagen.com", "cobb-vantress.com", "hyline.com",
    "pic.com", "topigsnorsvin.com",
]

# ── L4：高可信度 ───────────────────────────────────────────────────────────────
# 同行評審主流期刊、高引用論文
L4_JOURNALS = [
    # 家禽
    "poultry science", "world's poultry science", "british poultry science",
    # 豬
    "journal of animal science", "livestock science", "animal",
    "journal of swine health", "theriogenology",
    # 牛羊
    "journal of dairy science", "small ruminant research", "meat science",
    # 飼料營養
    "animal feed science and technology", "animal nutrition",
    "british journal of nutrition", "journal of nutrition",
    # 水產
    "aquaculture", "reviews in aquaculture", "aquaculture reports",
    "aquaculture nutrition", "journal of the world aquaculture society",
    "fish and shellfish immunology",
    # 獸醫
    "frontiers in veterinary science", "preventive veterinary medicine",
    "veterinary microbiology", "research in veterinary science",
    # 綜合
    "scientific reports", "plos one", "animals",
    # 中文核心
    "中國水產科學", "水產學報", "畜牧獸醫學報", "動物營養學報",
    "中國農業科學", "飼料工業", "中國畜牧雜誌",
]

L4_SUPPLIERS = [
    "dsm", "kemin", "novozymes", "novonesis", "basf", "evonik",
    "adisseo", "alltech", "biomin", "trouw", "cargill animal",
    "elanco", "zoetis", "merck animal",
]

# ── AB試驗 / 田間試驗加分關鍵字 ──────────────────────────────────────────────
# 這些表示是真實對照試驗，優先級提升
RCT_FIELD_TRIAL_KEYWORDS = [
    # 試驗設計
    "randomized controlled", "field trial", "feeding trial",
    "treatment group", "control group", "ab trial", "a/b trial",
    "experimental group", "replicate", "replication",
    "double blind", "blinded trial",
    # 統計
    "p < 0.05", "p<0.05", "p = 0.0", "statistically significant",
    "significantly improved", "significantly reduced",
    "one-way anova", "two-way anova", "tukey", "duncan",
    # 動物試驗規模
    "broiler trial", "layer trial", "swine trial", "shrimp trial",
    "pond trial", "commercial farm", "commercial flock",
    "in vivo", "in vitro",  # in vitro 降級，in vivo 升級
]

# ── 機制研究 / 非田間試驗（降一級）────────────────────────────────────────────
MECHANISM_ONLY_KEYWORDS = [
    "in vitro", "cell culture", "cell line", "microorganism",
    "bacteria culture", "rat model", "mouse model",
    "in silico", "molecular docking", "computational",
]

# ── 我們的核心成分關鍵字（加分：相關性高）────────────────────────────────────
CORE_INGREDIENT_KEYWORDS = [
    # LCFA / policosanol 族
    "octacosanol", "triacontanol", "policosanol", "polycosanol",
    "long-chain fatty alcohol", "very long chain fatty alcohol", "vlcfa",
    "wax alcohol", "1-octacosanol", "1-triacontanol",
    "hexacosanol", "dotriacontanol", "tetracosanol",
    # 蝦青素
    "astaxanthin", "haematococcus",
    # ch-OSA
    "orthosilicic acid", "ch-osa", "silicon",
    # 枯草菌源蛋白酶
    "bacillus subtilis protease", "subtilisin", "bacillus protease",
    "serine protease feed",
    # MG / AGP-free
    "mycoplasma gallisepticum", "agp-free", "antibiotic-free",
    "antibiotic growth promoter alternative", "non-antibiotic",
    "tylosin alternative", "enrofloxacin alternative",
    "membrane disruption", "cell membrane intervention",
]

# ── L1：雜訊域名 ──────────────────────────────────────────────────────────────
L1_DOMAINS = [
    "blogspot", "wordpress", "medium.com", "reddit", "quora",
    "zhihu", "weibo", "douban", "tieba.baidu",
    "ask.com", "yahoo.answers", "forum",
]

L1_NOISE_PATTERNS = [
    r"buy \w+ online", r"cheap \w+", r"discount",
    r"advertisement", r"sponsored",
]


def score(paper: dict) -> tuple[int, list[str]]:
    """
    Returns (score 1-5, list of reasons)
    """
    title  = (paper.get("title",  "") or "").lower()
    ab     = (paper.get("abstract","") or "").lower()
    url    = (paper.get("source_url","") or "").lower()
    stype  = paper.get("source_type", "")
    cites  = paper.get("citation_count") or 0
    year   = paper.get("year") or 0
    full   = title + " " + ab

    reasons = []

    # ── L1：雜訊（直接返回）──────────────────────────────────────────────────
    if any(d in url for d in L1_DOMAINS):
        return 1, ["noise domain"]
    if stype == "social":
        return 1, ["social media"]
    if len(ab) < 80:
        return 1, ["abstract too short"]
    if any(re.search(p, full) for p in L1_NOISE_PATTERNS):
        return 1, ["noise pattern"]

    # ── 初始分數 ──────────────────────────────────────────────────────────────
    base_score = 2

    # ── L5 觸發（直接返回）───────────────────────────────────────────────────
    for kw in L5_TITLE_KEYWORDS:
        if kw in title:
            return 5, [f"L5 title keyword: {kw}"]
    for domain in L5_SOURCE_DOMAINS:
        if domain in url:
            return 5, [f"L5 source domain: {domain}"]

    # ── 來源類型基礎分 ────────────────────────────────────────────────────────
    if stype == "paper":
        base_score = 3
        reasons.append("peer-reviewed paper")
    elif stype in ("vendor_whitepaper", "whitepaper"):
        base_score = 3
        reasons.append("technical whitepaper")
    elif stype == "patent":
        base_score = 3
        reasons.append("patent")
    elif stype == "industry_media":
        base_score = 3
        reasons.append("industry media")
    elif stype == "vendor_claim":
        base_score = 2
        reasons.append("vendor claim")

    # ── L4 期刊匹配（+1）────────────────────────────────────────────────────
    for j in L4_JOURNALS:
        if j in full:
            base_score = max(base_score, 4)
            reasons.append(f"L4 journal: {j}")
            break

    # ── 高引用（+1）──────────────────────────────────────────────────────────
    if stype == "paper" and cites >= 50:
        base_score = max(base_score, 4)
        reasons.append(f"high citations: {cites}")

    # ── 近年高品質廠商（維持4）───────────────────────────────────────────────
    for s in L4_SUPPLIERS:
        if s in url or s in ab:
            base_score = max(base_score, 4)
            reasons.append(f"L4 supplier: {s}")
            break

    # ── AB試驗 / 田間試驗加分 ─────────────────────────────────────────────────
    rct_hits = [k for k in RCT_FIELD_TRIAL_KEYWORDS if k in full]
    if rct_hits:
        # in vitro 降分，in vivo 升分
        if "in vitro" in full and "in vivo" not in full:
            base_score = max(2, base_score - 1)
            reasons.append("in vitro only (-1)")
        elif "in vivo" in full or "field trial" in full or "commercial farm" in full:
            base_score = min(5, base_score + 1)
            reasons.append(f"field trial/in vivo (+1): {rct_hits[0]}")
        elif any(k in full for k in ("p < 0.05", "p<0.05", "statistically significant")):
            base_score = min(5, base_score + 1)
            reasons.append("statistically significant (+1)")

    # ── 純機制研究（降分）────────────────────────────────────────────────────
    mech_hits = [k for k in MECHANISM_ONLY_KEYWORDS if k in full]
    if mech_hits and not any(k in full for k in ("in vivo", "field", "commercial")):
        base_score = max(2, base_score - 1)
        reasons.append(f"mechanism only (-1): {mech_hits[0]}")

    # ── 核心成分相關性（標記，不加分，但 ingredient_hint 更新）────────────────
    core_hits = [k for k in CORE_INGREDIENT_KEYWORDS if k in full]
    if core_hits:
        reasons.append(f"core ingredient: {', '.join(core_hits[:3])}")

    return min(5, max(1, base_score)), reasons


def classify_category(paper: dict, score_val: int) -> str:
    """
    A=田間試驗 B=機制 C=鄰近物種 D=綜述 E=雜訊
    """
    if score_val <= 1:
        return "E"

    title = (paper.get("title", "") or "").lower()
    ab    = (paper.get("abstract","") or "").lower()
    full  = title + " " + ab

    if any(k in title for k in ("review", "meta-analysis", "systematic")):
        return "D"
    if any(k in full for k in ("field trial", "commercial farm", "commercial flock",
                                "broiler trial", "layer trial", "feeding trial",
                                "in vivo", "animal experiment", "pond trial")):
        return "A"
    if any(k in full for k in ("mechanism", "signaling pathway", "gene expression",
                                "molecular", "in vitro", "cell culture",
                                "metabolomics", "proteomics")):
        return "B"
    if any(k in full for k in ("rat", "mouse", "mice", "rodent", "human",
                                "clinical", "in silico")):
        return "C"

    return "A" if score_val >= 4 else "B"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",   default="/tmp/raw_papers_collected.json")
    parser.add_argument("--output",  default="/tmp/raw_papers_scored.json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    data   = json.loads(Path(args.input).read_text(encoding="utf-8"))
    papers = data.get("papers", [])

    dist     = {1:0, 2:0, 3:0, 4:0, 5:0}
    cat_dist = {"A":0, "B":0, "C":0, "D":0, "E":0}
    core_ingredient_count = 0

    for p in papers:
        lvl, reasons = score(p)
        cat = classify_category(p, lvl)

        p["credibility"] = lvl
        p["category"]    = cat
        p["score_reasons"] = reasons if args.verbose else reasons[:2]

        # 核心成分標記
        full = ((p.get("title","") or "") + " " + (p.get("abstract","") or "")).lower()
        core_hits = [k for k in CORE_INGREDIENT_KEYWORDS if k in full]
        if core_hits:
            p["core_ingredient_match"] = core_hits[:5]
            core_ingredient_count += 1

        # L1 跳過 embedding
        if lvl <= 1:
            p["skip"] = True

        dist[lvl]     += 1
        cat_dist[cat] += 1

    data["papers"]            = papers
    data["credibility_dist"]  = dist
    data["category_dist"]     = cat_dist
    data["core_ingredient_papers"] = core_ingredient_count

    Path(args.output).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log.info(f"Scored {len(papers)} papers")
    log.info("Credibility:")
    for lvl in range(5, 0, -1):
        log.info(f"  L{lvl}: {dist[lvl]}")
    log.info("Categories:")
    for c in ("A","B","C","D","E"):
        log.info(f"  {c}: {cat_dist[c]}")
    log.info(f"Core ingredient papers: {core_ingredient_count}")


if __name__ == "__main__":
    main()
