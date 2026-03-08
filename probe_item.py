"""
Probe the v4 API item structure and write the real scraper.
"""
import urllib.request, json

headers = {
    "x-api-key": "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc",
    "Accept": "application/json",
    "Origin": "https://www.myscheme.gov.in",
    "Referer": "https://www.myscheme.gov.in/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

url = "https://api.myscheme.gov.in/schemes/v4/public/schemes?lang=en&page=1&limit=3"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=15) as r:
    data = json.loads(r.read().decode())

items = data["data"]
print(f"Total items in response: {len(items)}")
print(f"\nFirst item full structure:")
print(json.dumps(items[0], indent=2, ensure_ascii=False)[:3000])
