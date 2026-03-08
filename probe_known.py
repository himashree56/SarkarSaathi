"""Print the full 'en' content from v6 detail API to see real field names."""
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

# Look at known schemes that appear on the website
known_slugs = ["pm-kisan", "pmay-g", "pmjay", "nsp-sc", "pmegp", "pmuy", "sukanya-samriddhi-yojana"]
for slug in known_slugs:
    d = api_get(f"https://api.myscheme.gov.in/schemes/v6/public/schemes?slug={slug}&lang=en")
    if not d:
        print(f"{slug}: NO RESPONSE")
        continue
    data = d.get("data", {})
    if not data:
        print(f"{slug}: EMPTY DATA")
        continue
    en = data.get("en", {})
    print(f"\n{slug}: data keys={list(data.keys())}, en keys={list(en.keys())[:10]}")
    # Print a snippet
    print(json.dumps(data, ensure_ascii=False)[:500])
    break
