"""
market_collector.py v2 — Scrapling 升級版
替換 httpx + BeautifulSoup → Scrapling（反爬蟲 + JS渲染）
輸出：/tmp/market_data_collected.json（本機）或 MARKET_DB_PATH（CI）
"""
import os
import json
import time
import hashlib
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = r"D:\playwright-browsers"

import yaml
import feedparser
from tenacity import retry, stop_after_attempt, wait_exponential

from scrapling import Fetcher
from scrapling.fetchers import StealthyFetcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── 路徑設定 ──────────────────────────────────────────────────────────────────
# 本機執行 → Windows 路徑；CI 執行 → /tmp/
IS_LOCAL = os.name == "nt"
OUTPUT_PATH  = Path(r"D:\LLM\knowledge\market\market_collected.json") if IS_LOCAL \
               else Path("/tmp/market_data_collected.json")
METRICS_PATH = Path("configs/species_metrics.yaml")
INGREDIENTS_P = Path("configs/ingredients.yaml")

FORCE_FULL    = os.environ.get("FORCE_FULL", "false").lower() == "true"
LOOKBACK_DAYS = 180 if FORCE_FULL else 35
SINCE_DATE    = (datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")


# ── 工具函數 ──────────────────────────────────────────────────────────────────

def record_id(*args):
    key = "|".join(str(a) for a in args).lower()
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def load_config():
    try:
        with open(METRICS_PATH, encoding="utf-8") as f:
            metrics = yaml.safe_load(f)
        with open(INGREDIENTS_P, encoding="utf-8") as f:
            ingredients = yaml.safe_load(f)
        return metrics, ingredients
    except Exception as e:
        log.warning(f"Config load failed: {e}, using defaults")
        return {}, {}


# ── 關鍵字（從原版複製，保持一致）────────────────────────────────────────────

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
    "layer_hen":    ["蛋鸡","蛋雞","layer hen","laying hen","layer"],
    "broiler":      ["肉鸡","肉雞","broiler","native chicken","土鸡","土雞"],
    "finisher_pig": ["育肥猪","育肥豬","finisher pig","肥猪","出栏","出欄"],
    "pregnant_sow": ["怀孕母猪","懷孕母豬","pregnant sow","妊娠"],
    "lactating_sow":["哺乳母猪","哺乳母豬","lactating sow","泌乳"],
    "dairy_cow":    ["奶牛","乳牛","dairy cow","milk cow"],
    "beef_cattle":  ["肉牛","beef cattle","feedlot"],
    "shrimp":       ["对虾","對蝦","shrimp","白虾","白蝦","南美白对虾"],
    "tilapia":      ["罗非鱼","羅非魚","tilapia","吴郭鱼"],
    "meat_sheep":   ["肉羊","sheep","lamb"],
}

KPI_KEYWORDS = {
    "laying_rate":     ["产蛋率","產蛋率","laying rate","hen-day production"],
    "egg_feed_ratio":  ["蛋料比","料蛋比","feed conversion egg","FCR egg"],
    "mortality_rate":  ["死淘率","死亡率","mortality","cull rate"],
    "FCR":             ["饲料转化率","飼料轉化率","FCR","feed conversion ratio","料肉比"],
    "ADG":             ["日增重","average daily gain","ADG"],
    "milk_yield":      ["产奶量","產奶量","milk yield","milk production"],
    "survival_rate":   ["育成率","成活率","survival rate"],
    "egg_price":       ["鸡蛋价格","雞蛋價格","egg price","蛋价","蛋價"],
    "pig_price":       ["猪价","豬價","pig price","出栏价","pork price"],
}

MARKET_FILTER_KEYWORDS = [
    "FCR","feed conversion","laying rate","production performance",
    "egg price","pig price","live weight","mortality","benchmark",
    "production cost","market price","industry average",
    "产蛋率","蛋料比","死淘率","猪价","鸡蛋价格","养殖成本",
    "出栏","育成率","产量","行情","基准",
]

MARKET_RSS_FEEDS = [
    {"url": "https://www.wattagnet.com/rss.xml",     "name": "WATTPoultry",    "lang": "en"},
    {"url": "https://www.pigprogress.net/rss",        "name": "PigProgress",    "lang": "en"},
    {"url": "https://thepoultrysite.com/rss",         "name": "ThePoultrysite", "lang": "en"},
    {"url": "https://www.thepigsite.com/rss",         "name": "ThePigSite",     "lang": "en"},
    {"url": "https://www.globalseafood.org/feed",     "name": "GSAA",           "lang": "en"},
    {"url": "https://www.feednavigator.com/rss/feed", "name": "FeedNavigator",  "lang": "en"},
    {"url": "https://www.undercurrentnews.com/feed",  "name": "UndercurrentNews","lang":"en"},
    {"url": "https://www.poultryworld.net/rss",       "name": "PoultryWorld",   "lang": "en"},
]

GOV_SOURCES = [
    {"url": "https://www.moa.gov.cn/govpublic/XMYS/",
     "name": "農業農村部畜牧業", "region": "CN_all", "lang": "zh", "credibility": 5,
     "mode": "stealth"},   # 需要 JS
    {"url": "https://www.fao.org/faostat/en/#data/QCL",
     "name": "FAO FAOSTAT", "region": "GLOBAL", "lang": "en", "credibility": 5,
     "mode": "stealth"},
    {"url": "https://www.coa.gov.tw/ws.php?id=2505076",
     "name": "台灣農業部統計", "region": "TW_all", "lang": "zh", "credibility": 5,
     "mode": "fast"},
    {"url": "http://www.moa.gov.cn/gk/tzgg_1/index.htm",
     "name": "農業農村部通知公告", "region": "CN_all", "lang": "zh", "credibility": 5,
     "mode": "fast"},
]

COMPETITOR_URLS = [
    {"url": "https://www.kemin.com/en/animal-nutrition-and-health/solutions",
     "name": "Kemin", "id": "phytogenic", "mode": "stealth"},
    {"url": "https://www.novonesis.com/en/animal-health-nutrition",
     "name": "Novonesis", "id": "enzyme_protease", "mode": "stealth"},
    {"url": "https://www.dsm.com/animal-nutrition/en/products.html",
     "name": "DSM-Firmenich", "id": "astaxanthin", "mode": "stealth"},
    {"url": "https://www.evonik.com/en/products/animal-nutrition",
     "name": "Evonik", "id": "enzyme_protease", "mode": "stealth"},
    {"url": "https://www.alltech.com/animal-nutrition",
     "name": "Alltech", "id": "probiotics_feed", "mode": "stealth"},
]


# ── Scrapling 抓取器 ──────────────────────────────────────────────────────────

def scrapling_get(url: str, mode: str = "fast", timeout: int = 25) -> str:
    """統一抓取介面，回傳 html_content 字串"""
    try:
        if mode == "stealth":
            page = StealthyFetcher.fetch(url, headless=True,
                                         network_idle=True, timeout=timeout * 1000)
        else:
            page = Fetcher.get(url)
        if page.status >= 400:
            log.warning(f"HTTP {page.status}: {url}")
            return ""
        return page.html_content
    except Exception as e:
        log.warning(f"Fetch failed [{mode}] {url}: {e}")
        # auto fallback to stealth
        if mode == "fast":
            try:
                page = StealthyFetcher.fetch(url, headless=True, network_idle=True)
                return page.html_content
            except Exception as e2:
                log.warning(f"Stealth fallback also failed: {e2}")
        return ""


def extract_texts(html: str, min_len: int = 30, max_len: int = 1500) -> list[str]:
    """從 html 提取有意義的文字段落（用 Scrapling lxml 解析）"""
    from scrapling import Fetcher
    # 用 Fetcher 解析已有的 html
    try:
        from lxml import etree
        from lxml.html import fromstring
        doc = fromstring(html)
        texts = []
        for tag in doc.iter("p", "td", "li", "h2", "h3", "div"):
            t = (tag.text_content() or "").strip()
            if min_len <= len(t) <= max_len:
                texts.append(t)
        return texts
    except Exception:
        return []


def detect_region(text: str) -> str:
    t = text.lower()
    for region, kws in REGION_KEYWORDS.items():
        if any(k.lower() in t for k in kws):
            return region
    if any(k in t for k in ["china", "中国", "中國", "cn"]):
        return "CN_all"
    return "GLOBAL"


def detect_species(text: str) -> str:
    t = text.lower()
    for sp, kws in SPECIES_KEYWORDS.items():
        if any(k.lower() in t for k in kws):
            return sp
    return "unknown"


def detect_kpis(text: str) -> list:
    t = text.lower()
    return [kpi for kpi, kws in KPI_KEYWORDS.items()
            if any(k.lower() in t for k in kws)]


# ── RSS（用 feedparser，保持輕量）────────────────────────────────────────────

def fetch_market_rss() -> list:
    results = []
    filter_lower = {k.lower() for k in MARKET_FILTER_KEYWORDS}

    for feed_info in MARKET_RSS_FEEDS:
        try:
            # RSS 用 Scrapling Fetcher 抓原始 XML
            html = scrapling_get(feed_info["url"], mode="fast")
            feed = feedparser.parse(html or feed_info["url"])
        except Exception as e:
            log.warning(f"RSS {feed_info['name']}: {e}")
            continue

        for entry in feed.entries[:60]:
            title   = entry.get("title", "")
            summary = entry.get("summary", "") or ""
            content = (title + " " + summary).lower()
            if not any(k in content for k in filter_lower):
                continue

            species = detect_species(content)
            region  = detect_region(content)
            kpis    = detect_kpis(content)
            if not kpis:
                continue

            pub_date = entry.get("published", "")
            year = int(pub_date[:4]) if pub_date and pub_date[:4].isdigit() \
                   else datetime.utcnow().year

            for kpi_id in kpis:
                results.append({
                    "id":           record_id(region, species, kpi_id, entry.get("link","")),
                    "region":       region,
                    "species":      species,
                    "kpi_id":       kpi_id,
                    "value":        None,
                    "unit":         None,
                    "year":         year,
                    "credibility":  3,
                    "source_type":  "industry_media",
                    "source_url":   entry.get("link", feed_info["url"]),
                    "source_title": feed_info["name"],
                    "raw_text":     (title + " " + summary)[:1500],
                    "language":     feed_info["lang"],
                    "confirmed":    0,
                    "collected_at": datetime.utcnow().isoformat(),
                })
        time.sleep(1)

    log.info(f"RSS: {len(results)} records")
    return results


# ── 政府統計（Scrapling StealthyFetcher）────────────────────────────────────

def fetch_gov_stats() -> list:
    results = []
    filter_lower = {k.lower() for k in MARKET_FILTER_KEYWORDS}

    for src in GOV_SOURCES:
        html = scrapling_get(src["url"], mode=src.get("mode", "fast"))
        if not html:
            continue

        texts = extract_texts(html)
        for text in texts:
            t_lower = text.lower()
            if not any(k in t_lower for k in filter_lower):
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
        time.sleep(3)

    log.info(f"Gov stats: {len(results)} records")
    return results


# ── 競品（Scrapling StealthyFetcher，繞過反爬蟲）────────────────────────────

def fetch_competitor_claims() -> list:
    results = []
    perf_lower = {k.lower() for k in [
        "FCR","feed conversion","laying rate","performance","improvement",
        "reduction","survival","mortality","ADG","growth",
        "产蛋率","FCR改善","饲料转化","育成率",
    ]}

    for src in COMPETITOR_URLS:
        html = scrapling_get(src["url"], mode=src.get("mode", "stealth"))
        if not html:
            continue

        texts = extract_texts(html)
        for text in texts:
            t_lower = text.lower()
            if not any(k in t_lower for k in perf_lower):
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
        time.sleep(2)

    log.info(f"Competitor: {len(results)} records")
    return results


# ── 去重 ──────────────────────────────────────────────────────────────────────

def dedupe(records: list) -> list:
    seen = {}
    for r in records:
        rid = r["id"]
        if rid not in seen or r.get("credibility", 0) > seen[rid].get("credibility", 0):
            seen[rid] = r
    log.info(f"Dedupe: {len(records)} → {len(seen)}")
    return list(seen.values())


# ── 主程式 ────────────────────────────────────────────────────────────────────

def main():
    load_config()

    log.info("=== RSS ===")
    rss = fetch_market_rss()

    log.info("=== Gov stats ===")
    gov = fetch_gov_stats()

    log.info("=== Competitor ===")
    comp = fetch_competitor_claims()

    market_final = dedupe(rss + gov)
    comp_final   = dedupe(comp)

    output = {
        "collected_at":      datetime.utcnow().isoformat(),
        "lookback_days":     LOOKBACK_DAYS,
        "market_kpi_total":  len(market_final),
        "competitor_total":  len(comp_final),
        "market_kpi":        market_final,
        "competitor_market": comp_final,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    log.info(f"Done → {OUTPUT_PATH}")
    log.info(f"market_kpi={len(market_final)} competitor={len(comp_final)}")


if __name__ == "__main__":
    main()
