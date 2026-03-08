"""Probe the 'en' structure inside each scheme item."""
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

# Paginated detail: fetch page with full en content
url = "https://api.myscheme.gov.in/schemes/v4/public/schemes?lang=en&page=1&limit=2"
data = api_get(url)
items = data["data"]
first = items[0]
print("TOP-LEVEL KEYS:", list(first.keys()))
print("\n'en' KEYS:", list(first.get("en", {}).keys()))
en = first["en"]
for k, v in en.items():
    if isinstance(v, (dict, list)):
        if isinstance(v, dict):
            print(f"\n  en.{k} (dict):", list(v.keys())[:8])
        elif isinstance(v, list) and v:
            print(f"\n  en.{k} (list[{len(v)}]):", v[:2] if isinstance(v[0], str) else list(v[0].keys())[:5])
    else:
        print(f"\n  en.{k}:", str(v)[:100])
