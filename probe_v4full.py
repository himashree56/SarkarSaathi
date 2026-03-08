"""Test what's inside v4 API full response for a single page item."""
import urllib.request, json

HEADERS = {
    "x-api-key": "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc",
    "Accept": "application/json",
    "Origin": "https://www.myscheme.gov.in",
    "Referer": "https://www.myscheme.gov.in/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
def api_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

# Get page 1 with limit=5 — print full JSON of first item
url = "https://api.myscheme.gov.in/schemes/v4/public/schemes?lang=en&page=1&limit=100"
data = api_get(url)
items = data["data"]

# Find first item that has more than 3 keys in 'en'
for item in items:
    en = item.get("en", {})
    if len(en) > 1:
        print(f"SLUG: {item['slug']}")
        print(f"en keys: {list(en.keys())}")
        print(json.dumps(en, ensure_ascii=False, indent=2)[:2000])
        break
else:
    # Print all en key counts
    for item in items[:20]:
        en = item.get("en", {})
        print(f"{item['slug']}: en keys = {list(en.keys())}")
