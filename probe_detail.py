"""Probe what v6 detail returns for a known slug."""
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

# Get a few slugs
data = api_get("https://api.myscheme.gov.in/schemes/v4/public/schemes?lang=en&page=1&limit=5")
items = data["data"]

for item in items[:3]:
    slug = item["slug"]
    sid  = item["_id"]
    print(f"\nSlug: {slug}, ID: {sid}")
    # Try v6 with slug
    d1 = api_get(f"https://api.myscheme.gov.in/schemes/v6/public/schemes?slug={slug}&lang=en")
    print(f"  v6 slug response: {list(d1.get('data',{}).keys()) if d1 else None}")
    if d1 and d1.get("data"):
        print(f"  data keys: {list(d1['data'].keys())[:10]}")
        scheme = d1["data"].get("scheme") or d1["data"]
        print(f"  scheme type: {type(scheme)}")
        if isinstance(scheme, dict):
            print(f"  scheme keys: {list(scheme.keys())[:15]}")

    # Try search to get the right slug format
    s2 = api_get(f"https://api.myscheme.gov.in/search/v6/schemes?lang=en&keyword={slug}&from=0&size=3")
    hits = s2.get("data", {}).get("hits", {}).get("items", []) if s2 else []
    print(f"  search hits: {len(hits)}")
    if hits:
        print(f"  hit keys: {list(hits[0].keys())}")
        fields = hits[0].get("fields", {})
        print(f"  fields keys: {list(fields.keys())[:10]}")
