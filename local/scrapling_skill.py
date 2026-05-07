"""
scrapling_skill.py — QClaw Skill
讓 Qwen3.6 可以直接指令式呼叫 Scrapling 抓取任意 URL
安裝路徑：C:\Users\Richtrong\.qclaw\skills\scrapling_skill.py
"""
import os
import json
import argparse
import sys
from pathlib import Path

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = r"D:\playwright-browsers"

from scrapling import Fetcher
from scrapling.fetchers import StealthyFetcher


def scrape(url: str, mode: str = "auto", css: str = None,
           max_chars: int = 4000) -> dict:
    """
    mode:
      auto    — 先用 Fetcher，若失敗自動升級 StealthyFetcher
      fast    — 只用 Fetcher（靜態，無 JS）
      stealth — 強制 StealthyFetcher（JS渲染 + Cloudflare bypass）
    """
    page = None
    used_mode = mode

    try:
        if mode in ("auto", "fast"):
            page = Fetcher.get(url)
            if page.status >= 400:
                raise Exception(f"status {page.status}")
            used_mode = "fast"
        if mode == "stealth":
            page = StealthyFetcher.fetch(url, headless=True, network_idle=True)
            used_mode = "stealth"
    except Exception as e:
        if mode == "auto":
            try:
                page = StealthyFetcher.fetch(url, headless=True, network_idle=True)
                used_mode = "stealth_fallback"
            except Exception as e2:
                return {"ok": False, "error": str(e2), "url": url}
        else:
            return {"ok": False, "error": str(e), "url": url}

    # 提取內容
    if css:
        texts = page.css(css).getall()
        content = "\n".join(texts)
    else:
        # 智能提取：優先正文段落
        paragraphs = page.css("p, td, li, h1, h2, h3").getall()
        content = "\n".join(paragraphs) if paragraphs else page.html_content

    # 截斷
    if len(content) > max_chars:
        content = content[:max_chars] + f"\n...[truncated, total {len(content)} chars]"

    return {
        "ok":      True,
        "url":     url,
        "status":  page.status,
        "mode":    used_mode,
        "chars":   len(content),
        "content": content,
    }


def batch_scrape(urls: list, mode: str = "fast", css: str = None) -> list:
    """批量抓取（用於 market_collector 替代 httpx）"""
    results = []
    for url in urls:
        result = scrape(url, mode=mode, css=css)
        results.append(result)
    return results


# ── CLI 介面（QClaw 透過 subprocess 呼叫）────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scrapling skill for QClaw")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--mode", default="auto",
                        choices=["auto", "fast", "stealth"],
                        help="Fetch mode")
    parser.add_argument("--css", default=None,
                        help="CSS selector to extract (optional)")
    parser.add_argument("--max-chars", type=int, default=4000,
                        help="Max content chars to return")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    result = scrape(args.url, mode=args.mode,
                    css=args.css, max_chars=args.max_chars)

    if args.json or not sys.stdout.isatty():
        print(json.dumps(result, ensure_ascii=False))
    else:
        if result["ok"]:
            print(f"✅ {result['url']} [{result['mode']}] {result['chars']} chars")
            print("-" * 60)
            print(result["content"])
        else:
            print(f"❌ {result['error']}")


if __name__ == "__main__":
    main()
