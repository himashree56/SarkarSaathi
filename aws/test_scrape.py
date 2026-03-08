import urllib.request
import re

urls = [
    "https://sevasindhu.karnataka.gov.in/Sevasindhu/DepartmentServices",
    "https://www.karnataka.gov.in/english/services/schemes",
    "https://wcd.nic.in/schemes"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

for url in urls:
    try:
        print(f"\\n--- Testing {url} ---")
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode('utf-8')
            print(f"SUCCESS: Fetched {len(html)} bytes")
            if "captcha" in html.lower() or "cloudflare" in html.lower():
                print("WARNING: Captcha or anti-bot detected!")
    except Exception as e:
        print(f"FAILED: {e}")
