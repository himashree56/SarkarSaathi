"""
SarkarSaathi — Scrape 1000 Schemes across 10 Categories
Fetches from myscheme API by keyword, saves to schemes.json, uploads to S3.
"""
import json, time, re, os, urllib.request, urllib.parse
import boto3

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

REGION = config["region"]
BUCKET = config["data_bucket"]
KEY = config["schemes_key"]

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "data")
OUT_FILE = os.path.join(OUT_DIR, "schemes.json")
os.makedirs(OUT_DIR, exist_ok=True)

HEADERS = {
    "x-api-key": "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc",
    "Accept": "application/json",
    "Origin": "https://www.myscheme.gov.in",
    "Referer": "https://www.myscheme.gov.in/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}

CATEGORIES = {
    "women": ["women", "child", "widow", "girl", "maternal", "shg", "mahila"],
    "education": ["education", "student", "scholarship", "school", "learning", "minority"],
    "agriculture": ["farmer", "agriculture", "crop", "irrigation", "kisan", "krishi"],
    "employment": ["employment", "skill", "job", "training", "startup", "msme"],
    "health": ["health", "insurance", "medical", "nutrition", "swasthya"],
    "housing": ["housing", "awas", "sanitation", "water", "drinking"],
    "pension": ["senior", "pension", "old age", "welfare", "social security", "vriddha"],
    "disability": ["disability", "disabled", "divyang", "handicap", "assistive"],
    "business": ["entrepreneur", "startup", "business", "loan", "msme", "innovation"],
    "energy": ["solar", "energy", "electricity", "cooking fuel", "electrification", "pump"]
}

def api_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  WARN {url[-60:]}: {e}")
        return None

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
    rules = {}
    text = (brief or "").lower()
    scheme_for = fields.get("schemeFor", "")
    tags = " ".join(fields.get("tags") or []).lower()
    combined = f"{text} {scheme_for} {tags}".lower()

    inc = extract_income(combined)
    if inc: rules["income_max"] = inc

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

def build_from_fields(fields, target_cat):
    slug = fields.get("slug", "").strip()
    if not slug: return None

    name_en = fields.get("schemeName") or slug
    scheme_id = slug.upper()[:40]

    state_list = fields.get("beneficiaryState") or []
    if isinstance(state_list, list) and state_list:
        state = state_list[0] if len(state_list) == 1 else "ALL"
    elif isinstance(state_list, str):
        state = state_list
    else:
        state = "ALL"

    brief = fields.get("briefDescription") or ""
    brief_clean = re.sub(r"<[^>]+>", "", brief).strip()

    rules = build_rules(fields, brief_clean)
    benefit_amount = parse_benefit_amount(brief_clean)

    nodal = fields.get("nodalMinistryName") or "Government of India"
    office = f"{nodal} — {'Government of India' if state == 'ALL' else state + ' Govt.'}"

    tags = fields.get("tags") or []
    tags_str = ", ".join(tags[:5]) if tags else ""
    benefit_desc = f"{brief_clean[:300]} [Tags: {tags_str}]" if tags_str else (brief_clean[:350] or "Government assistance.")

    website = f"https://www.myscheme.gov.in/schemes/{slug}"

    return {
        "id": scheme_id,
        "slug": slug,
        "name_en": name_en,
        "name_hi": name_en,
        "category": target_cat,
        "state": state,
        "benefit_amount": benefit_amount,
        "benefit_description": benefit_desc,
        "eligibility": rules,
        "required_documents": ["Aadhaar Card", "Bank Account Passbook", "Passport-size Photo", "Income Certificate"],
        "how_to_apply": f"Apply online at {website}",
        "application_steps": ["Visit myscheme.gov.in.", "Click 'Apply Now' and register.", "Fill form.", "Upload documents.", "Submit."],
        "office_info": office,
        "website": website,
    }

def main():
    print("=" * 60)
    print("SarkarSaathi — Bulk Sector-wise Scraper (1000 Schemes)")
    print("=" * 60)

    all_schemes = []
    seen_slugs = set()

    for cat_name, keywords in CATEGORIES.items():
        cat_schemes = []
        print(f"\n--- Scraping Category: {cat_name.upper()} ---")
        
        for kw in keywords:
            if len(cat_schemes) >= 100: break
            
            offset = 0
            page_size = 20
            while len(cat_schemes) < 100 and offset < 200:
                q_enc = urllib.parse.quote(kw)
                url = f"https://api.myscheme.gov.in/search/v6/schemes?lang=en&q=%5B%5D&keyword={q_enc}&sort=&from={offset}&size={page_size}"
                
                d = api_get(url)
                if not d: break
                
                items = d.get("data", {}).get("hits", {}).get("items", [])
                if not items: break
                
                for item in items:
                    if len(cat_schemes) >= 100: break
                        
                    fields = item.get("fields", {})
                    slug = fields.get("slug", "")
                    if not slug or slug in seen_slugs: continue
                    
                    obj = build_from_fields(fields, cat_name)
                    if obj:
                        cat_schemes.append(obj)
                        seen_slugs.add(slug)
                        print(f"  [{len(cat_schemes):2d}] {obj['name_en'][:50]} (kw: {kw})")
                
                offset += page_size
                time.sleep(0.3)
                
        # Fill shortfalls with default category endpoint if needed
        # Just move to next if we couldn't get 100.
        print(f">>> Found {len(cat_schemes)} schemes for {cat_name}")
        all_schemes.extend(cat_schemes)
        
    print(f"\n{'='*60}")
    print(f"Total schemes collected: {len(all_schemes)}")
    
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_schemes, f, ensure_ascii=False, indent=2)
    print(f"Saved local → {OUT_FILE}")
    
    # Upload to S3
    s3 = boto3.client("s3", region_name=REGION)
    body = json.dumps(all_schemes, ensure_ascii=False, indent=2)
    s3.put_object(
        Bucket=BUCKET,
        Key=KEY,
        Body=body.encode("utf-8"),
        ContentType="application/json",
    )
    print(f"Uploaded to s3://{BUCKET}/{KEY}")
    print("✅ Done!")

if __name__ == "__main__":
    main()
