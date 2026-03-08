import urllib.request, json

headers = {
    "x-api-key": "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc",
    "Accept": "application/json",
    "Origin": "https://www.myscheme.gov.in",
    "Referer": "https://www.myscheme.gov.in/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

urls = [
    "https://api.myscheme.gov.in/search/v6/schemes?lang=en&from=0&size=5",
    "https://api.myscheme.gov.in/search/v6/schemes?lang=en&q=%5B%5D&keyword=farmer&sort=&from=0&size=5",
    "https://api.myscheme.gov.in/schemes/v6/public/schemes?lang=en&page=1&limit=5",
    "https://api.myscheme.gov.in/schemes/v4/public/schemes?lang=en&page=1&limit=5",
]

for url in urls:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            print(f"URL: {url[:80]}")
            print(f"  top-level keys: {list(data.keys())}")
            # Try to find the list
            def find_list(d, depth=0):
                if depth > 4:
                    return
                if isinstance(d, list) and len(d) > 0:
                    print(f"  Found list of {len(d)} at depth {depth}")
                    print(f"  First item keys: {list(d[0].keys()) if isinstance(d[0], dict) else type(d[0])}")
                    return
                if isinstance(d, dict):
                    for k, v in d.items():
                        if isinstance(v, (list, dict)):
                            print(f"    key={k}")
                            find_list(v, depth+1)
            find_list(data)
            print()
    except Exception as e:
        print(f"FAIL {url[:70]}: {e}")
        print()
