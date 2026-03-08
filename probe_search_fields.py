"""Probe search API fields object for full scheme metadata."""
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

# No keyword = get all, use large size
d = api_get("https://api.myscheme.gov.in/search/v6/schemes?lang=en&from=0&size=3")
items = d.get("data", {}).get("hits", {}).get("items", [])
print(f"Items: {len(items)}")
if items:
    first = items[0]
    print("Keys:", list(first.keys()))
    fields = first.get("fields", {})
    print("\nFields keys:", list(fields.keys()))
    print("\nFull fields:")
    print(json.dumps(fields, ensure_ascii=False, indent=2)[:3000])
