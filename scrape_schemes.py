"""
SarkarSaathi — Final Scheme Scraper using Search API
Uses the search v6 API 'fields' which contains all needed metadata.
Paginates with from=0..400 in steps of 50 to collect 100 unique schemes.
Run: python scrape_schemes.py
"""
import json, time, re, os, urllib.request

OUT_DIR  = os.path.join(os.path.dirname(__file__), "backend", "data")
OUT_FILE = os.path.join(OUT_DIR, "schemes.json")
os.makedirs(OUT_DIR, exist_ok=True)

HEADERS = {
    "x-api-key": "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc",
    "Accept": "application/json",
    "Origin": "https://www.myscheme.gov.in",
    "Referer": "https://www.myscheme.gov.in/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

def api_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  WARN {url[-60:]}: {e}")
        return None

CAT_MAP = {
    "agriculture": "agriculture", "farmer": "agriculture", "kisan": "agriculture",
    "education": "education", "scholarship": "education", "learning": "education",
    "housing": "housing", "awas": "housing",
    "health": "health", "medical": "health", "maternity": "health",
    "employment": "employment", "labour": "employment",
    "skill": "skill", "training": "skill",
    "pension": "pension",
    "disability": "disability", "divyang": "disability",
    "women": "women", "girl": "women",
    "food": "food", "nutrition": "food",
    "social": "social_welfare", "welfare": "social_welfare",
    "business": "business", "entrepreneur": "business", "financial": "business",
    "banking": "business", "insurance": "business",
}

def normalize_cat(cats):
    if not cats:
        return "social_welfare"
    text = " ".join(str(c) for c in (cats if isinstance(cats, list) else [cats])).lower()
    for k, v in CAT_MAP.items():
        if k in text:
            return v
    return "social_welfare"

def extract_income(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*lakh", text, re.I)
    if m: return int(float(m.group(1)) * 100000)
    m = re.search(r"(?:rs\.?|₹|inr)\s*(\d[\d,]+)", text, re.I)
    if m: return int(m.group(1).replace(",", ""))
    return None

def extract_age_range(text):
    m = re.search(r"(\d{1,2})\s*(?:to|-)\s*(\d{2,3})\s*year", text, re.I)
    if m: return int(m.group(1)), int(m.group(2))
    mn = re.search(r"(?:above|minimum|at least)\s*(\d{2})\s*year", text, re.I)
    mx = re.search(r"(?:below|maximum|up to|upto)\s*(\d{2,3})\s*year", text, re.I)
    return (int(mn.group(1)) if mn else None), (int(mx.group(1)) if mx else None)

def build_rules(fields, brief):
    """Build eligibility rules from search fields + brief description."""
    rules = {}
    text = (brief or "").lower()
    scheme_for = fields.get("schemeFor", "")
    tags = " ".join(fields.get("tags") or []).lower()
    combined = f"{text} {scheme_for} {tags}".lower()

    income = extract_income(combined)
    if income: rules["income_max"] = income

    age_min, age_max = extract_age_range(combined)
    if age_min: rules["age_min"] = age_min
    if age_max: rules["age_max"] = age_max

    if any(w in combined for w in ["women", "girl", "female", "widow", "mahila", "beti"]):
        rules["gender"] = "female"

    if "widow" in combined:
        rules["marital_status"] = ["widowed"]

    occ = []
    if any(w in combined for w in ["farmer", "kisan", "agricultur"]): occ.append("farmer")
    if "student" in combined: occ.append("student")
    if any(w in combined for w in ["labourer", "daily wage", "mazdoor", "worker"]): occ.append("daily_wage")
    if "artisan" in combined or "weaver" in combined: occ.append("artisan")
    if "fisherm" in combined: occ.append("fisherman")
    if "self employed" in combined or "entrepreneur" in combined: occ.append("self_employed")
    if occ: rules["occupation"] = occ

    caste = []
    if any(w in combined for w in ["scheduled caste", "dalit", " sc "]): caste.append("sc")
    if any(w in combined for w in ["scheduled tribe", "tribal", "adivasi", " st "]): caste.append("st")
    if any(w in combined for w in ["other backward", " obc "]): caste.append("obc")
    if caste: rules["caste"] = caste

    if "rural" in combined and "urban" not in combined: rules["location_type"] = "rural"
    elif "urban" in combined and "rural" not in combined: rules["location_type"] = "urban"

    return rules

def parse_benefit_amount(brief):
    if not brief: return None
    m = re.search(r"(?:rs\.?|₹|inr)\s*(\d[\d,]+)", brief, re.I)
    if m: return int(m.group(1).replace(",", ""))
    m = re.search(r"(\d+(?:\.\d+)?)\s*lakh", brief, re.I)
    if m: return int(float(m.group(1)) * 100000)
    return None

DEFAULT_DOCS = ["Aadhaar Card", "Bank Account Passbook", "Passport-size Photo", "Income Certificate"]
DEFAULT_STEPS = [
    "Visit myscheme.gov.in or the scheme portal.",
    "Click 'Apply Now' and register/login.",
    "Fill the application form with your details.",
    "Upload required documents.",
    "Submit and save the application reference number.",
]

def build_from_fields(fields):
    slug = fields.get("slug", "").strip()
    if not slug:
        return None

    name_en = fields.get("schemeName") or slug
    scheme_id = slug.upper()[:40]

    state_list = fields.get("beneficiaryState") or []
    if isinstance(state_list, list) and state_list:
        state = state_list[0] if len(state_list) == 1 else "ALL"
    elif isinstance(state_list, str):
        state = state_list
    else:
        state = "ALL"

    cats = fields.get("schemeCategory") or []
    category = normalize_cat(cats)

    brief = fields.get("briefDescription") or ""
    brief_clean = re.sub(r"<[^>]+>", "", brief).strip()  # strip HTML

    rules = build_rules(fields, brief_clean)
    benefit_amount = parse_benefit_amount(brief_clean)

    nodal = fields.get("nodalMinistryName") or "Government of India"
    office = f"{nodal} — {'Government of India' if state == 'ALL' else state + ' Govt.'}"

    tags = fields.get("tags") or []
    tags_str = ", ".join(tags[:5]) if tags else ""
    if tags_str:
        benefit_desc = f"{brief_clean[:300]} [Tags: {tags_str}]"
    else:
        benefit_desc = brief_clean[:350] or "Government assistance under this scheme."

    website = f"https://www.myscheme.gov.in/schemes/{slug}"

    return {
        "id": scheme_id,
        "slug": slug,
        "name_en": name_en,
        "name_hi": name_en,  # Hindi not available from search fields
        "category": category,
        "state": state,
        "benefit_amount": benefit_amount,
        "benefit_description": benefit_desc,
        "eligibility": rules,
        "required_documents": DEFAULT_DOCS.copy(),
        "how_to_apply": f"Apply online at {website}",
        "application_steps": DEFAULT_STEPS.copy(),
        "office_info": office,
        "website": website,
    }

def fetch_page(from_offset, size=50):
    url = f"https://api.myscheme.gov.in/search/v6/schemes?lang=en&from={from_offset}&size={size}"
    d = api_get(url)
    if not d: return []
    return d.get("data", {}).get("hits", {}).get("items", [])

def main():
    print("=" * 60)
    print("SarkarSaathi — Search API Scraper (FINAL)")
    print("=" * 60)

    schemes = []
    seen_slugs = set()
    offset = 0
    page_size = 50

    while len(schemes) < 100:
        print(f"\n[fetch] from={offset}, size={page_size} ...")
        items = fetch_page(offset, page_size)
        if not items:
            print("  No more results!")
            break

        for item in items:
            if len(schemes) >= 100:
                break
            fields = item.get("fields", {})
            slug = fields.get("slug", "")
            if not slug or slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            obj = build_from_fields(fields)
            if obj:
                schemes.append(obj)
                name = obj["name_en"][:55]
                print(f"  [{len(schemes):3d}] {name}")

        offset += page_size
        time.sleep(0.3)

        if offset > 500:
            break  # safety

    print(f"\n{'='*60}")
    print(f"Total schemes: {len(schemes)}")
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(schemes, f, ensure_ascii=False, indent=2)
    print(f"Saved → {OUT_FILE}")
    print("✅ Done!")

if __name__ == "__main__":
    main()
