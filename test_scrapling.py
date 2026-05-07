import os
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = r"D:\playwright-browsers"
from scrapling.fetchers import StealthyFetcher
from scrapling import Fetcher

print("Test 1: Fetcher (static)...")
page = Fetcher.get("https://httpbin.org/get")
print(f"  OK - {len(page.html_content)} chars, status={page.status}")

print("Test 2: StealthyFetcher...")
page2 = StealthyFetcher.fetch("https://httpbin.org/headers", headless=True, network_idle=True)
print(f"  OK - {len(page2.html_content)} chars, status={page2.status}")

print("Test 3: 農業農村部...")
page3 = Fetcher.get("http://www.moa.gov.cn/gk/tzgg_1/index.htm")
links = page3.css("a::text").getall()
print(f"  OK - {len(links)} links found")

print("\n✅ Scrapling 可用")
