"""
market_collector.py
市場情報爬蟲 — 獨立於 github_collector.py 之後執行
蒐集：農業部統計 / 行業媒體 / 競品白皮書 / 學術背景數據
輸出：/tmp/market_data_collected.json
"""

import os
import json
import time
import hashlib
import logging
import asyncio
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

OUTPUT_PATH    = Path("/tmp/market_data_collected.json")
METRICS_PATH   = Path("configs/species_metrics.yaml")
INGREDIENTS_P  = Path("configs/ingredients.yaml")

FORCE_FULL     = os.environ.get("FORCE_FULL", "false").lower() == "true"
LOOKBACK_DAYS  = 180 if FORCE_FULL else 35
SINCE_DATE_ISO = (datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")

# ── 載入設定 ──────────────────────────────────────────────────────────────────

def load_config():
    with open(METRICS_PATH, encoding="utf-8") as f:
        metrics = yaml.safe_load(f)
    with open(INGREDIENTS_P, encoding="utf-8") as f:
        ingredients = yaml.safe_load(f)
    return metrics, ingredients


def record_id(*args):
    key = "|".join(str(a) for a in args).lower()
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# ── 關鍵字建構 ────────────────────────────────────────────────────────────────

def build_market_queries(metrics: dict) -> list[dict]:
    """從 species_metrics.yaml 的 search_keywords 建立查詢清單"""
    kw = metrics.get("search_keywords", {})
    queries = []
    for lang, terms in kw.items():
        for term in terms:
            queries.append({"term": term, "lang": lang})

    # 額外補充市場價格關鍵字（動態補全年份）
    year = datetime.utcnow().year
    extra = [
        f"layer hen production performance benchmark {year}",
        f"broiler FCR China Southeast Asia {year}",
        f"pig price China market {year}",
        f"egg price China {year}",
        f"aquaculture FCR shrimp benchmark Asia {year}",
        f"poultry industry report {year}",
        f"livestock production cost China {year}",
    ]
    for term in extra:
        queries.append({"term": term, "lang": "en"})

    log.info(f"Market queries: {len(queries)}")
    return queries


# ── 地區 / 物種 / KPI 判斷 ───────────────────────────────────────────────────

REGION_KEYWORDS = {
    "CN_north":    ["华北","东北","河北","山东","辽宁","吉林","黑龙江","北方"],
    "CN_south":    ["华南","西南","广东","广西","福建","海南","云南","四川","重庆","南方"],
    "CN_central":  ["华中","华东","湖南","湖北","江苏","浙江","安徽","上海","中部"],
    "CN_northwest":["西北","新疆","甘肃","陕西","宁夏"],
    "TW_all":      ["台湾","臺灣","taiwan","TW"],
    "SEA_vietnam": ["越南","vietnam","viet"],
    "SEA_thailand":["泰国","泰國","thailand","thai"],
    "SEA_indonesia":["印尼","indonesia"],
    "SEA_malaysia":["马来西亚","馬來西亞","malaysia"],
    "SEA_philippines":["菲律宾","菲律賓","philippines"],
}

SPECIES_KEYWORDS = {
    "layer_hen":   ["蛋鸡","蛋雞","layer hen","laying hen","layer"],
    "broiler":     ["肉鸡","肉雞","broiler","native chicken","土鸡","土雞"],
    "finisher_pig":["育肥猪","育肥豬","finisher pig","肥猪","出栏","出欄"],
    "pregnant_sow":["怀孕母猪","懷孕母豬","pregnant sow","妊娠"],
    "lactating_sow":["哺乳母猪","哺乳母豬","lactating sow","泌乳"],
    "boar":        ["公猪","公豬","boar","种公猪"],
    "shrimp":      ["对虾","對蝦","shrimp","白虾","白蝦","南美白对虾"],
    "tilapia":     ["罗非鱼","羅非魚","tilapia","吴郭鱼","吳郭魚"],
    "livestock":   ["肉牛","奶牛","肉羊","cattle","beef cattle","dairy","sheep"],
}

KPI_KEYWORDS = {
    "laying_rate":         ["产蛋率","產蛋率","laying rate","hen-day production"],
    "egg_feed_ratio":      ["蛋料比","料蛋比","feed conversion egg","FCR egg"],
    "mortality_rate":      ["死淘率","死亡率","mortality","cull rate"],
    "peak_duration_weeks": ["产蛋高峰","產蛋高峰","peak production","peak duration"],
    "egg_price_per_500g":  ["鸡蛋价格","雞蛋價格","egg price","蛋价","蛋價"],
    "FCR":                 ["饲料转化率","飼料轉化率","FCR","feed conversion ratio"],
    "live_price_per_500g": ["毛鸡价格","毛雞價格","live chicken price","收购价","收購價"],
    "slaughter_price_per_kg":["猪价","豬價","pig price","出栏价","出欄價","pork price"],
    "rearing_cost_per_head":["养殖成本","養殖成本","rearing cost","production cost"],
    "slaughter_weight_kg": ["出栏体重","出欄體重","slaughter weight","market weight"],
    "milk_yield_kg_per_day":["产奶量","產奶量","milk yield","milk production"],
    "survival_rate":       ["育成率","成活率","survival rate"],
    "harvest_cycle_days":  ["养殖周期","養殖週期","收成周期","harvest cycle","grow-out period"],
    "ADG":                 ["日增重","average daily gain","ADG"],
}


def detect_region(text: str) -> str:
    text_lower = text.lower()
    for region, keywords in REGION_KEYWORDS.items():
        if any(k.lower() in text_lower for k in keywords):
            return region
    if any(k in text_lower for k in ["china","中国","中國","cn"]):
        return "CN_all"
    return "GLOBAL"


def detect_species(text: str) -> str:
    text_lower = text.lower()
    for species, keywords in SPECIES_KEYWORDS.items():
        if any(k.lower() in text_lower for k in keywords):
            return species
    return "unknown"


def detect_kpis(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for kpi_id, keywords in KPI_KEYWORDS.items():
        if any(k.lower() in text_lower for k in keywords):
            found.append(kpi_id)
    return found


# ── RSS 行業媒體（市場數據版）────────────────────────────────────────────────

MARKET_RSS_FEEDS = [
    # 英文行業媒體
    {"url": "https://www.wattagnet.com/rss.xml",          "name": "WATTPoultry",    "lang": "en"},
    {"url": "https://www.pigprogress.net/rss",             "name": "PigProgress",    "lang": "en"},
    {"url": "https://thepoultrysite.com/rss",              "name": "ThePoultrysite", "lang": "en"},
    {"url": "https://www.thepigsite.com/rss",              "name": "ThePigSite",     "lang": "en"},
    {"url": "https://www.globalseafood.org/feed",          "name": "GSAA",           "lang": "en"},
    {"url": "https://www.feednavigator.com/rss/feed",      "name": "FeedNavigator",  "lang": "en"},
    {"url": "https://www.undercurrentnews.com/feed",       "name": "UndercurrentNews","lang": "en"},
    # 中文媒體（RSS 若可用）
    {"url": "https://www.soozhu.com/rss.xml",              "name": "搜猪网",         "lang": "zh"},
    {"url": "https://www.poultryworld.net/rss",            "name": "PoultryWorld",   "lang": "en"},
]

# 市場關鍵字（用於 RSS 過濾）
MARKET_FILTER_KEYWORDS = [
    "FCR","feed conversion","laying rate","production performance",
    "egg price","pig price","live weight","mortality","benchmark",
    "production cost","market price","industry average",
    "产蛋率","蛋料比","死淘率","猪价","鸡蛋价格","养殖成本",
    "出栏","育成率","产量","行情","基准",
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=8))
async def fetch_market_rss(client: httpx.AsyncClient) -> list[dict]:
    results = []
    filter_lower = {k.lower() for k in MARKET_FILTER_KEYWORDS}

    for feed_info in MARKET_RSS_FEEDS:
        try:
            r = await client.get(feed_info["url"], timeout=20, follow_redirects=True)
            feed = feedparser.parse(r.text)
        except Exception as e:
            log.warning(f"RSS {feed_info['name']}: {e}")
            continue

        for entry in feed.entries[:60]:
            title   = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            content = (title + " " + summary).lower()

            if not any(k in content for k in filter_lower):
                continue

            species = detect_species(content)
            region  = detect_region(content)
            kpis    = detect_kpis(content)

            if not kpis:
                continue

            pub_date = entry.get("published", "")
            year = int(pub_date[:4]) if pub_date and pub_date[:4].isdigit() else datetime.utcnow().year

            for kpi_id in kpis:
                results.append({
                    "id":           record_id(region, species, kpi_id, entry.get("link","")),
                    "region":       region,
                    "species":      species,
                    "kpi_id":       kpi_id,
                    "value":        None,        # Qwen 本地分析再抽取數值
                    "unit":         None,
                    "year":         year,
                    "credibility":  4 if feed_info["lang"] == "en" else 3,
                    "source_type":  "industry_media",
                    "source_url":   entry.get("link", ""),
                    "source_title": title,
                    "raw_text":     summary[:1500],
                    "language":     feed_info["lang"],
                    "confirmed":    0,
                    "collected_at": datetime.utcnow().isoformat(),
                })

    log.info(f"Market RSS: {len(results)} records")
    return results


# ── 政府統計來源 ──────────────────────────────────────────────────────────────

GOV_SOURCES = [
    # 中國農業農村部
    {
        "url":    "http://www.moa.gov.cn/govpublic/XMYS/",
        "name":   "農業農村部畜牧業",
        "region": "CN_all",
        "lang":   "zh",
        "credibility": 5,
    },
    # FAO FAOSTAT（全球基準）
    {
        "url":    "https://www.fao.org/faostat/en/#data/QCL",
        "name":   "FAO FAOSTAT",
        "region": "GLOBAL",
        "lang":   "en",
        "credibility": 5,
    },
    # 台灣農業部
    {
        "url":    "https://www.coa.gov.tw/ws.php?id=2505076",
        "name":   "台灣農業部統計",
        "region": "TW_all",
        "lang":   "zh",
        "credibility": 5,
    },
    # 泰國農業部
    {
        "url":    "https://www.dld.go.th/th/index.php/th/",
        "name":   "泰國畜牧局",
        "region": "SEA_thailand",
        "lang":   "th",
        "credibility": 5,
    },
]


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=3, max=10))
async def fetch_gov_stats(client: httpx.AsyncClient) -> list[dict]:
    results = []
    filter_lower = {k.lower() for k in MARKET_FILTER_KEYWORDS}

    for src in GOV_SOURCES:
        try:
            r = await client.get(src["url"], timeout=25, follow_redirects=True)
            soup = BeautifulSoup(r.text, "lxml")

            for tag in soup.find_all(["p","td","li","div"], limit=300):
                text = tag.get_text(" ", strip=True)
                if len(text) < 30 or len(text) > 1000:
                    continue
                content_lower = text.lower()
                if not any(k in content_lower for k in filter_lower):
                    continue

                species = detect_species(text)
                kpis    = detect_kpis(text)
                if not kpis or species == "unknown":
                    continue

                for kpi_id in kpis:
                    results.append({
                        "id":           record_id(src["region"], species, kpi_id, text[:80]),
                        "region":       src["region"],
                        "species":      species,
                        "kpi_id":       kpi_id,
                        "value":        None,
                        "unit":         None,
                        "year":         datetime.utcnow().year,
                        "credibility":  src["credibility"],
                        "source_type":  "gov_stats",
                        "source_url":   src["url"],
                        "source_title": src["name"],
                        "raw_text":     text[:1500],
                        "language":     src["lang"],
                        "confirmed":    0,
                        "collected_at": datetime.utcnow().isoformat(),
                    })
            await asyncio.sleep(3)
        except Exception as e:
            log.warning(f"Gov stats {src['name']}: {e}")

    log.info(f"Gov stats: {len(results)} records")
    return results


# ── 競品市場動向 ──────────────────────────────────────────────────────────────

COMPETITOR_URLS = [
    {"url": "https://www.kemin.com/en/animal-nutrition-and-health/solutions",
     "name": "Kemin", "id": "phytogenic"},
    {"url": "https://www.novonesis.com/en/animal-health-nutrition",
     "name": "Novonesis", "id": "enzyme_protease"},
    {"url": "https://www.dsm.com/animal-nutrition/en/products.html",
     "name": "DSM-Firmenich", "id": "astaxanthin"},
    {"url": "https://www.evonik.com/en/products/animal-nutrition",
     "name": "Evonik", "id": "enzyme_protease"},
    {"url": "https://www.adisseo.com/en/solutions/poultry",
     "name": "Adisseo", "id": "phytogenic"},
    {"url": "https://www.alltech.com/animal-nutrition",
     "name": "Alltech", "id": "probiotics_feed"},
]


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=3, max=10))
async def fetch_competitor_claims(client: httpx.AsyncClient) -> list[dict]:
    results = []
    perf_keywords = {
        "FCR","feed conversion","laying rate","performance","improvement",
        "reduction","survival","mortality","ADG","growth",
        "产蛋率","FCR改善","饲料转化","育成率",
    }
    perf_lower = {k.lower() for k in perf_keywords}

    for src in COMPETITOR_URLS:
        try:
            r = await client.get(src["url"], timeout=20, follow_redirects=True)
            soup = BeautifulSoup(r.text, "lxml")

            for tag in soup.find_all(["p","li","td"], limit=200):
                text = tag.get_text(" ", strip=True)
                if len(text) < 40 or len(text) > 1500:
                    continue
                content_lower = text.lower()
                if not any(k in content_lower for k in perf_lower):
                    continue

                species = detect_species(text)
                kpis    = detect_kpis(text)

                results.append({
                    "id":              record_id(src["id"], species, text[:80]),
                    "competitor_id":   src["id"],
                    "competitor_name": src["name"],
                    "region":          "GLOBAL",
                    "market_claim":    text[:1500],
                    "claim_metric":    kpis[0] if kpis else None,
                    "claim_value":     None,
                    "claim_unit":      None,
                    "species":         species,
                    "price_per_kg":    None,
                    "source_url":      src["url"],
                    "source_type":     "vendor_whitepaper",
                    "credibility":     3,
                    "year":            datetime.utcnow().year,
                    "raw_text":        text[:1500],
                    "confirmed":       0,
                    "collected_at":    datetime.utcnow().isoformat(),
                })
            await asyncio.sleep(2)
        except Exception as e:
            log.warning(f"Competitor {src['name']}: {e}")

    log.info(f"Competitor claims: {len(results)} records")
    return results


# ── 去重 ──────────────────────────────────────────────────────────────────────

def dedupe_market(records: list[dict]) -> list[dict]:
    seen = {}
    for r in records:
        rid = r["id"]
        if rid not in seen:
            seen[rid] = r
        else:
            # 保留可信度較高的
            if r.get("credibility", 0) > seen[rid].get("credibility", 0):
                seen[rid] = r
    log.info(f"Market dedupe: {len(records)} → {len(seen)}")
    return list(seen.values())


# ── 主程式 ────────────────────────────────────────────────────────────────────

async def main():
    metrics, ingredients = load_config()

    all_market: list[dict] = []
    all_competitor: list[dict] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": "research-pipeline/3.0 (market-data-collector)"},
        follow_redirects=True,
    ) as client:

        log.info("=== RSS market feeds ===")
        rss = await fetch_market_rss(client)
        all_market.extend(rss)

        log.info("=== Gov stats ===")
        gov = await fetch_gov_stats(client)
        all_market.extend(gov)

        log.info("=== Competitor claims ===")
        comp = await fetch_competitor_claims(client)
        all_competitor.extend(comp)

    market_final     = dedupe_market(all_market)
    competitor_final = dedupe_market(all_competitor)

    output = {
        "collected_at":       datetime.utcnow().isoformat(),
        "lookback_days":      LOOKBACK_DAYS,
        "market_kpi_total":   len(market_final),
        "competitor_total":   len(competitor_final),
        "market_kpi":         market_final,
        "competitor_market":  competitor_final,
    }

    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    log.info(f"Done. market_kpi={len(market_final)} competitor={len(competitor_final)}")


if __name__ == "__main__":
    asyncio.run(main())
