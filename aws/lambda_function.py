"""
SarkarSaathi — AWS Lambda Function
Replaces the local FastAPI backend.
Entry point: lambda_handler(event, context)

Routes:
  GET  /health  → status check
  POST /query   → extract profile + match schemes → return top 10

Environment variables (set by deploy.ps1):
  SCHEMES_TABLE   = ss-schemes
  SESSIONS_TABLE  = ss-sessions
  CACHE_TABLE     = ss-cache
  BEDROCK_MODEL   = anthropic.claude-3-haiku-20240307-v1:0
  REGION          = us-east-1
"""
import json
import os
import sys
import uuid
import time
import hashlib
import re
import concurrent.futures
from decimal import Decimal
from datetime import datetime

import boto3

# ── Environment ───────────────────────────────────────────────
REGION         = os.environ.get("REGION",         "us-east-1")
DATA_BUCKET    = os.environ.get("DATA_BUCKET")
SCHEMES_KEY    = os.environ.get("SCHEMES_KEY",    "data/schemes.json")
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "ss-sessions")
CACHE_TABLE    = os.environ.get("CACHE_TABLE",    "ss-cache")
BEDROCK_MODEL  = os.environ.get("BEDROCK_MODEL",  "anthropic.claude-3-haiku-20240307-v1:0")
NOVA_MODEL_ID  = os.environ.get("NOVA_MODEL_ID",  "amazon.nova-micro-v1:0")
NOVA_MAX_TOK   = int(os.environ.get("NOVA_MAX_TOKENS", "1500"))
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL   = os.environ.get("OPENROUTER_MODEL",   "meta-llama/llama-3.2-3b-instruct:free")
CACHE_TTL_SEC  = 3600
SESSION_TTL_SEC = 86400

from botocore.config import Config
boto_config = Config(read_timeout=15, connect_timeout=5, retries={"max_attempts": 0})

# ── AWS Clients ───────────────────────────────────────────────
s3       = boto3.client("s3",             region_name=REGION, config=boto_config)
dynamodb = boto3.resource("dynamodb",     region_name=REGION, config=boto_config)
bedrock  = boto3.client("bedrock-runtime", region_name=REGION, config=boto_config)
polly    = boto3.client("polly",           region_name=REGION, config=boto_config)
lambda_client = boto3.client("lambda",     region_name=REGION, config=boto_config)

sessions_table = dynamodb.Table(SESSIONS_TABLE)
cache_table    = dynamodb.Table(CACHE_TABLE)
cognito        = boto3.client("cognito-idp", region_name=REGION)

# ── In-memory scheme cache (warm Lambda = fast) ───────────────
_SCHEMES_CACHE = []


# ── OpenRouter fallback (used when Bedrock is unavailable) ────
def _openrouter_call(system_text, user_text, json_mode=False):
    """Call OpenRouter API using urllib — no extra deps required."""
    import urllib.request
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    messages = []
    if system_text:
        messages.append({"role": "system", "content": system_text})
    messages.append({"role": "user", "content": user_text})
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.3,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://sarkarsaathi.ai",
            "X-Title": "SarkarSaathi",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            body = resp.read().decode("utf-8")
            result = json.loads(body)
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        # If openrouter fails, try reading the error body
        error_info = str(e)
        if hasattr(e, 'read'):
            try: error_info += f" | Body: {e.read().decode('utf-8')}"
            except: pass
        print(f"[openrouter] ERROR: {error_info}")
        raise


def _load_schemes():
    global _SCHEMES_CACHE
    if _SCHEMES_CACHE:
        return _SCHEMES_CACHE
    try:
        if not DATA_BUCKET:
            print("[lambda] ERROR: DATA_BUCKET env var not set")
            return []
            
        print(f"[lambda] Loading schemes from s3://{DATA_BUCKET}/{SCHEMES_KEY}")
        resp = s3.get_object(Bucket=DATA_BUCKET, Key=SCHEMES_KEY)
        data = resp["Body"].read().decode("utf-8")
        _SCHEMES_CACHE = json.loads(data)
        print(f"[lambda] Loaded {len(_SCHEMES_CACHE)} schemes from S3")
    except Exception as e:
        print(f"[lambda] ERROR loading schemes from S3: {e}")
        # Try local fallback if exists (for testing/packaging)
        try:
            local_path = os.path.join(os.path.dirname(__file__), "schemes.json")
            if os.path.exists(local_path):
                with open(local_path, "r", encoding="utf-8") as f:
                    _SCHEMES_CACHE = json.load(f)
                    print(f"[lambda] Loaded {len(_SCHEMES_CACHE)} schemes from local fallback")
        except: pass
    return _SCHEMES_CACHE


def _decimal_to_native(obj):
    """Convert DynamoDB Decimal values back to int/float."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_native(i) for i in obj]
    return obj


# ── Profile Extraction ────────────────────────────────────────
# Regex for major Indian scripts
SCRIPT_RE = re.compile(r'[\u0900-\u097F\u0A80-\u0AFF\u0980-\u09FF]')

def _detect_lang_from_script(text):
    if re.search(r'[\u0A80-\u0AFF]', text): return "gu" # Gujarati
    if re.search(r'[\u0900-\u097F]', text): return "hi" # Hindi/Devanagari
    if re.search(r'[\u0980-\u09FF]', text): return "bn" # Bengali
    return None

GENDER_KEYWORDS = {
    "male":   ["male","man","boy","पुरुष","लड़का","आदमी","मर्द"],
    "female": ["female","woman","girl","widow","महिला","औरत","लड़की","विधवा"],
}
MARITAL_KEYWORDS = {
    "widowed":   ["widow","widower","widowed","विधवा","विधुर"],
    "unmarried": ["unmarried","single","bachelor","अविवाहित","कुंवारा","कुंवारी"],
    "divorced":  ["divorced","तलाकशुदा","तलाक"],
    "married":   ["married","wife","husband","विवाहित","शादीशुदा"],
}
OCCUPATION_KEYWORDS = {
    "farmer":      ["farmer","farming","agriculture","kisan","किसान","खेती"],
    "student":     ["student","studying","scholarship","college","university","छात्र","छात्रा","विद्यार्थी"],
    "unemployed":  ["unemployed","no job","jobless","बेरोजगार","काम नहीं"],
    "salaried":    ["salaried","job","employee","नौकरी","कर्मचारी"],
    "self_employed":["self employed","business","shop","व्यापारी","दुकान"],
    "daily_wage":  ["daily wage","labourer","mazdoor","मजदूर","दिहाड़ी"],
    "artisan":     ["artisan","craftsman","weaver","कारीगर","बुनकर"],
    "fisherman":   ["fisherman","fishing","मछुआरा"],
    "homemaker":   ["homemaker", "housewife", "stay-at-home", "गृहणी", "गृहिणी", "ગૃહિણી", "ઘરકામ"],
}
LOCATION_KEYWORDS = {
    "rural":      ["rural","village","gram","गांव","ग्राम","ग्रामीण"],
    "urban":      ["urban","city","town","शहर","नगर","शहरी"],
    "semi-urban": ["semi urban","kasba","कस्बा"],
}
CASTE_KEYWORDS = {
    "sc": ["sc","scheduled caste","dalit","अनुसूचित जाति","दलित"],
    "st": ["st","scheduled tribe","tribal","अनुसूचित जनजाति","आदिवासी"],
    "obc": ["obc","other backward","पिछड़ा","ओबीसी"],
    "general": ["general","open","सामान्य","जनरल"],
}
NEEDS_KEYWORDS = {
    "housing":    ["house","home","awas","shelter","ghar","घर","आवास","मकान"],
    "education":  ["education","school","college","scholarship","पढ़ाई","शिक्षा","छात्रवृत्ति"],
    "health":     ["health","medical","hospital","स्वास्थ्य","इलाज","बीमारी"],
    "food":       ["food","ration","grain","राशन","अनाज","खाना"],
    "employment": ["job","employment","rozgar","नौकरी","रोजगार","काम"],
    "pension":    ["pension","old age","वृद्धा","पेंशन"],
    "marriage":   ["marriage","wedding","shaadi","शादी","विवाह"],
    "disability": ["disability","disabled","divyang","विकलांग","दिव्यांग"],
    "business_loan": ["loan","capital","udyam","ऋण","लोन","उद्यम"],
}
STATES = {
    "andhra pradesh":["andhra pradesh","ap","ఆంధ్ర ಪ್ರದೇಶ್","ஆந்திரா"],
    "assam":["assam","অসম"], "bihar":["bihar","बिहार"],
    "chhattisgarh":["chhattisgarh","छत्तीसगढ़"], "delhi":["delhi","दिल्ली"],
    "goa":["goa","गोवा"], "gujarat":["gujarat","ગુજરાત","ગુજરાતની"],
    "haryana":["haryana","हरियाणा"], "himachal pradesh":["himachal pradesh","हिमाचल प्रदेश"],
    "jharkhand":["jharkhand","झारखंड"], "karnataka":["karnataka","ಕರ್ನಾಟಕ"],
    "kerala":["kerala","കേരളം"], "madhya pradesh":["madhya pradesh","mp","मध्य प्रदेश"],
    "maharashtra":["maharashtra","mh","महाराष्ट्र"], "manipur":["manipur","मणिपुर"],
    "odisha":["odisha","ଓଡ଼ିଶા"], "punjab":["punjab","ਪੰਜਾਬ"],
    "rajasthan":["rajasthan","राजस्थान"], "tamil nadu":["tamil nadu","தமிழ்நாடு","தமிழகம்"],
    "telangana":["telangana","తెలంగాణ"], "uttar pradesh":["uttar pradesh","up","उत्तर प्रदेश"],
    "uttarakhand":["uttarakhand","उत्तराखंड"], "west bengal":["west bengal","পশ্চিমবঙ্গ"],
}

def _match_keyword(text, kdict):
    t = text.lower()
    for cat, kws in kdict.items():
        for kw in kws:
            if kw.lower() in t:
                return cat
    return None

def _extract_age(text):
    for p in [
        r'(\d{1,2})\s*(?:साल|वर्ष|year|years|yr)',
        r'(?:age|aged|umra|उम्र)\s*[:\-]?\s*(\d{1,2})',
        r'i\s+am\s+(\d{1,2})',
        r'मैं\s*(\d{1,2})\s*(?:साल|वर्ष)',
    ]:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            age = int(m.group(1))
            if 5 <= age <= 100:
                return age
    return None

def _extract_income(text):
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:लाख|lakh|lac)', text, re.IGNORECASE)
    if m: return int(float(m.group(1)) * 100000)
    m = re.search(r'(\d{4,7})\s*(?:rupees|रुपये|rs|₹)', text, re.IGNORECASE)
    if m:
        val = int(m.group(1))
        if 1000 <= val <= 10000000: return val
    return None

def _extract_children(text):
    t = text.lower().strip()
    if any(k in t for k in ["no children", "none", "no kids", "zero", "0"]): return 0
    m = re.search(r'(\d+)\s*(?:बच्चे|बच्चों|children|child|kids)', t, re.IGNORECASE)
    return int(m.group(1)) if m else None

def _extract_needs(text):
    t = text.lower()
    return [need for need, kws in NEEDS_KEYWORDS.items() if any(kw.lower() in t for kw in kws)]

def _extract_state(text):
    t = text.lower()
    for state_key, kws in STATES.items():
        if any(kw.lower() in t for kw in kws):
            # Special case for AP/UP etc to avoid false positives
            if state_key in ["up", "ap", "mp"]:
                if f" {state_key} " not in f" {t} ": continue
            return state_key.title()
    return None

def rule_based_extract(query, target_lang=None):
    lang = target_lang or _detect_lang_from_script(query) or "en"
    gender = _match_keyword(query, GENDER_KEYWORDS)
    marital = _match_keyword(query, MARITAL_KEYWORDS)
    if marital == "widowed" and not gender:
        gender = "male" if any(w in query.lower() for w in ["विधुर","widower"]) else "female"
    occupation = _match_keyword(query, OCCUPATION_KEYWORDS)
    needs = _extract_needs(query)
    # NOTE: Do NOT auto-add needs based on occupation — only explicit mentions count
    return {
        "age": _extract_age(query), "gender": gender,
        "marital_status": marital, "children": _extract_children(query),
        "occupation": occupation, "income_level": _extract_income(query),
        "location_type": _match_keyword(query, LOCATION_KEYWORDS),
        "state": _extract_state(query),
        "caste": _match_keyword(query, CASTE_KEYWORDS),
        "needs": needs, "language": lang,
    }


def bedrock_extract(query):
    """Call Claude 3 Haiku via Bedrock — falls back to OpenRouter if Bedrock fails."""
    prompt = f"""Extract structured profile from this Indian government scheme query. The query may be in English, Hindi, Gujarati, Marathi, or any other Indian language.
Return ONLY valid JSON, no explanation.
RULES:
1. Only extract values EXPLICITLY stated by the user. Do NOT infer or guess.
2. If a field is not mentioned, return null (or [] for needs).
3. For "needs": ONLY add an item if the user LITERALLY mentions that need in words.
   - WRONG: User says "I am a farmer" → do NOT add "education" or "food" or anything.
   - WRONG: User says "I am a student" → do NOT auto-add "education".
   - RIGHT: User says "I need help with my child's school fees" → add "education".
   - RIGHT: User says "I need housing" → add "housing".
   - If the user does not mention any specific need, return [].

Query: {query}

{{
  "age": <integer or null>,
  "gender": <"male"/"female" or null>,
  "marital_status": <"married"/"unmarried"/"widowed"/"divorced" or null>,
  "children": <integer or null>,
  "occupation": <"farmer"/"student"/"unemployed"/"salaried"/"self_employed"/"daily_wage"/"artisan"/"fisherman" or null>,
  "income_level": <annual INR integer (1 lakh=100000) or null>,
  "location_type": <"rural"/"urban"/"semi-urban" or null>,
  "state": <Indian state name in English or null>,
  "caste": <"sc"/"st"/"obc"/"general" or null>,
  "needs": <ONLY what user explicitly asked for, from: ["housing","education","health","food","employment","pension","marriage","disability","business_loan"]. Return [] if nothing specific mentioned.>
}}"""

    # ── Primary: Bedrock (Claude 3 Haiku) ────────────────────────────────
    try:
        resp = bedrock.invoke_model(
            modelId=BEDROCK_MODEL,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 400, "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}]
            }),
            contentType="application/json", accept="application/json",
        )
        text = json.loads(resp["body"].read())["content"][0]["text"].strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(f"[bedrock_extract] Bedrock failed ({e}), trying OpenRouter fallback...")

    # ── Fallback: OpenRouter ─────────────────────────────────────────────
    try:
        text = _openrouter_call(
            "You are a JSON extractor. Return ONLY valid JSON with no extra text.",
            prompt,
            json_mode=True,
        )
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        return json.loads(text.strip())
    except Exception as e2:
        print(f"[bedrock_extract] OpenRouter fallback also failed: {e2}")
        raise


def extract_profile(query, target_lang=None):
    """Hybrid: Bedrock primary, rule-based secondary.
    Trust Bedrock's non-null values, but if Bedrock is null, fallback to Rule-based!
    """
    rule = rule_based_extract(query, target_lang)
    bedrock_p = None
    try:
        bedrock_p = bedrock_extract(query)
    except Exception as e:
        print(f"[bedrock] extraction fallback: {e}")

    merged = {}
    # We always start with the rule-based result
    merged = rule.copy()

    if bedrock_p is not None:
        # If Bedrock found a value, it takes precedence (more intelligent)
        for field in ["age","gender","marital_status","children","occupation",
                      "income_level","location_type","state","caste"]:
            val = bedrock_p.get(field)
            if val is not None: # <-- EXPLICIT NON-NULL CHECK
                merged[field] = val
            
        b_needs = bedrock_p.get("needs") or []
        if b_needs:
            # If Bedrock found specific needs, use those exclusively
            merged["needs"] = b_needs

    merged["language"] = rule.get("language", "en")
    return merged


def _infer_from_context(message, last_bot_msg, current_profile):
    """
    If the user gives a short answer like 'yes', 'no', or a number, 
    infer what field they are answering based on the last question asked.
    """
    msg = message.lower().strip().strip("?!.")
    if not last_bot_msg: return {}
    last_bot_msg = last_bot_msg.lower()
    
    # Check for yes/no patterns
    is_yes = msg in ["yes", "yeah", "yep", "ha", "haan", "जी", "हाँ", "हो"]
    is_no  = msg in ["no", "nah", "nope", "nahi", "nahin", "ना", "नहीं", "नाही"]
    
    inferred = {}
    
    # [1] Marital Status
    if any(k in last_bot_msg for k in ["married", "marriage", "शादी", "marital", "status"]):
        if is_yes: inferred["marital_status"] = "married"
        elif is_no or any(k in msg for k in ["single", "unmarried", "bachelor", "un-married"]): 
            inferred["marital_status"] = "unmarried"
        
    # [2] Children
    elif any(k in last_bot_msg for k in ["children", "kids", "बच्चे"]):
        if is_no or msg == "0": 
            inferred["children"] = 0
        else:
            m = re.search(r'\d+', msg)
            if m: inferred["children"] = int(m.group())

    # [3] Gender
    elif any(k in last_bot_msg for k in ["gender", "male", "female", "लिंग"]):
        if any(k in msg for k in ["female", "woman", "lady", "महिला", "स्त्री"]):
            inferred["gender"] = "female"
        elif any(k in msg for k in ["male", "man", "पुरुष"]):
            inferred["gender"] = "male"

    # [4] Age (Handle bare numbers)
    elif any(k in last_bot_msg for k in ["age", "old", "उम्र", "साल"]):
        m = re.search(r'^(\d{1,2})$', msg)
        if m:
            age = int(m.group(1))
            if 5 <= age <= 100:
                inferred["age"] = age

    # [5] State
    elif any(k in last_bot_msg for k in ["state", "live", "राज्य", "रहते"]):
        st = _extract_state(msg)
        if st: inferred["state"] = st
            
    return inferred


# ── Eligibility Matching ──────────────────────────────────────
OCC_CAT_MAP = {
    "farmer":       ["agriculture"], "student": ["education","skill"],
    "unemployed":   ["employment","skill"], "daily_wage": ["employment","social_welfare"],
    "self_employed":["business"],    "artisan": ["business","skill"],
    "fisherman":    ["agriculture"], "salaried": ["social_welfare","health"],
}
CAT_NEEDS_MAP = {
    "agriculture": ["farmer","food"], "education": ["education"], "housing": ["housing"],
    "health": ["health"],            "employment": ["employment"],
    "social_welfare": ["pension"],   "pension": ["pension"],
    "disability": ["disability"],    "women": ["marriage"],
    "food": ["food"],                "business": ["business_loan","employment"],
    "skill": ["employment"],
}

def check_scheme(scheme, profile):
    rules  = scheme.get("eligibility", {})
    score  = 0
    reasons = []
    cat    = scheme.get("category","")

    # Hard filters — handle both old field names (age_min/age_max/income_max)
    # and new field names (min_age/max_age/income_below)
    age = profile.get("age")
    if age:
        amin = rules.get("age_min") or rules.get("min_age")
        amax = rules.get("age_max") or rules.get("max_age")
        if amin and age < amin: return False, 0, []
        if amax and age > amax: return False, 0, []
        if amin or amax: score += 2; reasons.append(f"Age {age} fits range")

    sg = rules.get("gender")
    if sg and sg != "any":
        pg = profile.get("gender")
        if pg and pg != sg: return False, 0, []
        if pg == sg: score += 2; reasons.append(f"Gender matches ({sg})")

    # income_max (old) or income_below (new)
    imax = rules.get("income_max") or rules.get("income_below")
    pinc = profile.get("income_level")
    if imax and pinc is not None:
        if pinc > imax: return False, 0, []
        score += 2; reasons.append(f"Income ₹{pinc:,} within limit")

    ss = scheme.get("state","ALL")
    ps = profile.get("state")
    if ss not in ("ALL", None) and ps:
        if ps.lower() != ss.lower(): return False, 0, []
        score += 3; reasons.append(f"State matches ({ps})")
    elif ss == "ALL":
        score += 1; reasons.append("National scheme")

    # Soft matches
    pocc = profile.get("occupation")
    socc = rules.get("occupation", [])
    if isinstance(socc, str): socc = [socc]
    if socc:
        if pocc and pocc in socc: score += 4; reasons.append(f"Occupation '{pocc}' matches")
    elif pocc:
        if cat in OCC_CAT_MAP.get(pocc, []):
            score += 3; reasons.append(f"Category '{cat}' suits '{pocc}'")

    # marital_status — can be string (new) or list (old)
    sm = rules.get("marital_status", [])
    if isinstance(sm, str): sm = [sm]
    pm = profile.get("marital_status")
    if sm:
        if pm and pm in sm: score += 4; reasons.append(f"Marital status '{pm}' matches")
        elif pm and pm not in sm: return False, 0, []

    # location_type (old str) or location_types (new list)
    sloc = rules.get("location_type") or rules.get("location_types")
    ploc = profile.get("location_type")
    if sloc:
        if isinstance(sloc, list):
            if ploc and ploc in sloc: score += 2; reasons.append(f"Location '{ploc}' matches")
            elif ploc and ploc not in sloc: return False, 0, []
        else:
            if sloc != "any":
                if ploc and ploc == sloc: score += 2; reasons.append(f"Location '{ploc}' matches")
                elif ploc and ploc != sloc: return False, 0, []

    # caste — list in both old and new
    sc_list = rules.get("caste", [])
    if isinstance(sc_list, str): sc_list = [sc_list]
    pc = profile.get("caste")
    if sc_list:
        if pc and pc in sc_list: score += 3; reasons.append(f"Category '{pc.upper()}' eligible")
        elif pc and pc not in sc_list: return False, 0, []

    pneeds = profile.get("needs", [])
    for need in CAT_NEEDS_MAP.get(cat, []):
        if need in pneeds:
            score += 2; reasons.append(f"Matches need for '{need}'"); break

    # Disability flag
    if rules.get("disability") and profile.get("disability"):
        score += 3; reasons.append("Disability benefit applies")

    if score == 0:
        score = 1; reasons = reasons or ["Open to all eligible residents"]

    return True, score, reasons


def match_schemes(profile, top_n=10):
    schemes = _load_schemes()
    results = []
    for s in schemes:
        ok_flag, score, reasons = check_scheme(s, profile)
        if not ok_flag: continue
        results.append({
            "id":                  s.get("id",""),
            "name":                s.get("name") or s.get("name_en",""),
            "name_en":             s.get("name_en") or s.get("name",""),
            "name_hi":             s.get("name_hi",""),
            "category":            s.get("category",""),
            "state":               s.get("state","ALL"),
            "benefit_amount":      s.get("benefit_amount"),
            "benefit_description": s.get("benefit_description",""),
            "description":         s.get("description",""),
            "eligibility_reason":  " • ".join(reasons),
            "match_score":         score,
            "required_documents":  s.get("required_documents",[]),
            "how_to_apply":        s.get("how_to_apply",""),
            "application_steps":   s.get("application_steps",[]),
            # Support both old (office_info) and new (office_address + office_name + maps_url)
            "office_info":         s.get("office_info",""),
            "office_name":         s.get("office_name",""),
            "office_address":      s.get("office_address",""),
            "maps_url":            s.get("maps_url",""),
            "website":             s.get("website",""),
        })
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:top_n]


def translate_text(text, target_lang):
    """Use Bedrock to translate text into the user's preferred language."""
    if target_lang.lower() in ["en", "english"]: return text
    
    prompt = f"Translate the following Indian government scheme information into {target_lang}. Return ONLY the translated text:\n\n{text}"
    try:
        resp = bedrock.invoke_model(
            modelId=BEDROCK_MODEL,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000, "temperature": 0,
                "messages": [{"role": "user", "content": prompt}]
            }),
            contentType="application/json", accept="application/json",
        )
        return json.loads(resp["body"].read())["content"][0]["text"].strip()
    except Exception as e:
        print(f"[translate] error: {e}")
        return text


# ── User Auth Helpers ─────────────────────────────────────────
def get_user_id(event):
    """Extract user_id from Authorization header via Cognito."""
    auth = event.get("headers", {}).get("authorization")
    if not auth or not auth.startswith("Bearer "): return None
    token = auth.split(" ")[1]
    try:
        # Securely verify token by calling Cognito GetUser
        user = cognito.get_user(AccessToken=token)
        return user["Username"] # This is the unique User ID
    except Exception as e:
        print(f"[auth] Verification failed: {e}")
        # For expired tokens, we could try refresh token logic here
        # For now, return None to indicate authentication failed
        return None


# ── DynamoDB session helpers ──────────────────────────────────
def get_or_create_session(session_id=None):
    if not session_id:
        session_id = str(uuid.uuid4())
    try:
        resp = sessions_table.get_item(Key={"session_id": session_id})
        item = resp.get("Item")
        if item:
            return _decimal_to_native(item)
    except Exception: pass
    return {"session_id": session_id, "profile": {}, "title": None}


def generate_title(query):
    """Use Bedrock to generate a short 3-word title for the chat."""
    if not query: return "New Chat"
    prompt = f"Write a very short 2-4 word title for this user query. Do not use quotes or prefixes. Just the title text.\nQuery: '{query}'"
    try:
        resp = bedrock.invoke_model(
            modelId=BEDROCK_MODEL,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 15, "temperature": 0.3,
                "messages": [{"role": "user", "content": prompt}]
            }),
            contentType="application/json", accept="application/json",
        )
        return json.loads(resp["body"].read())["content"][0]["text"].strip(' "\'')
    except Exception as e:
        print(f"[generate_title] error: {e}")
        return "Chat Session"


def handle_async_translate(event):
    """Background task to translate schemes without blocking API Gateway."""
    session_id = event.get("session_id")
    target_lang = event.get("target_lang")
    items = event.get("items")
    
    if not session_id or not target_lang or not items:
        return {"status": "error", "message": "Missing params"}
        
    print(f"[async_translate] Starting background task for {session_id} -> {target_lang}")
    try:
        # VISIBILITY: Background thread emoji indicator
        session = get_or_create_session(session_id)
        current_title = session.get("title") or "Search Results"
        save_session(session_id, {}, "", title=f"⚡ Translating: {current_title}...")

        translated = _batch_translate(items, target_lang)
        
        # PERSISTENCE FIX: Ensure profile and history are dicts/lists before re-saving
        profile = session.get("profile") or {}
        if isinstance(profile, str):
            try: profile = json.loads(profile)
            except: profile = {}
            
        history = session.get("history") or []
        if isinstance(history, str):
            try: history = json.loads(history)
            except: history = []
            
        save_session(
            session_id, 
            profile, 
            session.get("last_query"), 
            user_id=session.get("user_id"), 
            title=current_title, # Restore original title
            history=history, 
            summary=session.get("summary"), 
            recommended_id=session.get("recommended_id"),
            schemes=translated
        )
        print(f"[async_translate] Successfully saved translated schemes for {session_id}")
    except Exception as e:
        print(f"[async_translate] Error: {e}")
        # Mark error in title for debugging
        save_session(session_id, {}, "", title=f"❌ Translation Error")
    return {"status": "done"}


def save_session(session_id, profile_dict, query_text, user_id=None, title=None, history=None, summary=None, recommended_id=None, schemes=None):
    """
    Non-destructively update the session. 
    Uses 'update_item' to prevent wiping out data.
    """
    try:
        expr = "SET profile = :p, last_query = :q, updated_at = :t, #ttlexp = :ttl"
        vals = {
            ":p": json.dumps(profile_dict),
            ":q": query_text,
            ":t": datetime.utcnow().isoformat(),
            ":ttl": int(time.time()) + SESSION_TTL_SEC,
        }
        names = {"#ttlexp": "ttl"}
        
        if user_id:
            expr += ", user_id = :u"
            vals[":u"] = user_id
        if title:
            expr += ", title = :tle"
            vals[":tle"] = title
        if history is not None:
            expr += ", history = :h"
            vals[":h"] = json.dumps(history)
        if summary:
            expr += ", summary = :s"
            vals[":s"] = summary
        if recommended_id:
            expr += ", recommended_id = :rid"
            vals[":rid"] = recommended_id
        if schemes is not None:
            expr += ", schemes = :sc"
            vals[":sc"] = json.dumps(schemes, default=_json_serial)
            
        sessions_table.update_item(
            Key={"session_id": session_id},
            UpdateExpression=expr,
            ExpressionAttributeValues=vals,
            ExpressionAttributeNames=names
        )
    except Exception as e:
        print(f"[session] save error: {e}")


# ── Bedrock Agent Tools (Action Groups) ────────────────────────
def handle_agent_tools(event):
    """
    Handles requests from Amazon Bedrock Agent based on the OpenAPI spec.
    """
    action_group = event.get('actionGroup')
    function = event.get('function')
    parameters = event.get('parameters', []) # list of {name, value}
    request_body = event.get('requestBody', {}).get('content', {}).get('application/json', {}).get('properties', [])
    
    # Helper to get body values
    def get_body_val(name):
        for prop in request_body:
            if prop.get('name') == name: return prop.get('value')
        return None

    print(f"[agent] Invoking {action_group}.{function}")

    try:
        if function == "extractProfile":
            text = get_body_val("text")
            target_lang = get_body_val("target_lang") or "en"
            current = get_body_val("current_profile") or {}
            if isinstance(current, str): current = json.loads(current)
            
            extracted = extract_profile(text, target_lang)
            # Merge logic: Bedrock Agent will handle further refinement, 
            # but we return the newly extracted facts merged with current.
            merged = {**current, **{k: v for k, v in extracted.items() if v is not None}}
            return {"responseBody": {"application/json": {"body": json.dumps({"profile": merged})}}}

        elif function == "getSchemes":
            profile = get_body_val("profile")
            if isinstance(profile, str): profile = json.loads(profile)
            
            matched = match_schemes(profile, top_n=10)
            # Add AI reasoning for the Agent
            summary = generate_summary_for_agent(profile, matched)
            rec_id = matched[0]["id"] if matched else None
            
            return {"responseBody": {"application/json": {"body": json.dumps({
                "schemes": matched,
                "recommended_id": rec_id,
                "summary": summary
            })}}}

        elif function == "manageSession":
            sid = get_body_val("session_id")
            prof = get_body_val("profile")
            hist = get_body_val("history")
            summ = get_body_val("summary")
            rid = get_body_val("recommended_id")
            
            if isinstance(prof, str): prof = json.loads(prof)
            if isinstance(hist, str): hist = json.loads(hist)
            
            save_session(sid, prof, "", history=hist, summary=summ, recommended_id=rid)
            return {"responseBody": {"application/json": {"body": json.dumps({"status": "updated"})}}}

    except Exception as e:
        print(f"[agent] Error in tool {function}: {e}")
        return {"responseBody": {"application/json": {"body": json.dumps({"error": str(e)})}}}

    return {"responseBody": {"application/json": {"body": json.dumps({"error": "Function not found"})}}}


def generate_summary_for_agent(profile, schemes):
    """Internal helper to generate a recommendation summary for the agent's output."""
    if not schemes: return "No matching schemes found for this profile."
    top = schemes[0]
    prompt = f"Given this user profile: {json.dumps(profile)}\nAnd these schemes: {json.dumps(schemes[:3])}\nBriefly explain in 1-2 sentences why '{top['name']}' is the best match. Focus on the core benefit."
    try:
        resp = bedrock.invoke_model(
            modelId=BEDROCK_MODEL,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 150, "temperature": 0.3,
                "messages": [{"role": "user", "content": prompt}]
            }),
            contentType="application/json", accept="application/json",
        )
        return json.loads(resp["body"].read())["content"][0]["text"].strip()
    except:
        return f"Based on your profile, {top['name']} offers the most direct benefits for your situation."


# ── API Response helpers ──────────────────────────────────────
def cors_headers():
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Max-Age": "86400",
    }

def ok_response(body, code=200):
    return {"statusCode": code, "headers": cors_headers(), "body": json.dumps(body, default=_json_serial)}

def _json_serial(obj):
    """JSON serializer for objects not serializable by default json code."""
    from decimal import Decimal
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

def err_response(msg, code=400):
    return {"statusCode": code, "headers": cors_headers(), "body": json.dumps({"error": msg})}


# ── Lambda handler ────────────────────────────────────────────
def lambda_handler(event, context):
    # Detect if this is an internal async task
    if event.get("task_type") == "async_translate":
        return handle_async_translate(event)
        
    # Detect if this is a Bedrock Agent invocation
    if 'actionGroup' in event:
        return handle_agent_tools(event)

    method = event.get("requestContext", {}).get("http", {}).get("method") \
             or event.get("httpMethod", "GET")
    path   = event.get("rawPath") or event.get("path", "/")

    # CORS pre-flight — return immediately with full CORS headers
    if method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": cors_headers(),
            "body": "",
        }

    # GET /session/{session_id}  — load saved session (no LLM, instant)
    if "/session/" in path and method == "GET" and not path.endswith("/history"):
        sid = path.split("/session/")[-1].strip("/")
        session = get_or_create_session(sid)
        profile = session.get("profile") or {}
        if isinstance(profile, str):
            try: profile = json.loads(profile)
            except: profile = {}
            
        history = session.get("history") or []
        if isinstance(history, str):
            try: history = json.loads(history)
            except: history = []

        if not profile and not history:
            return err_response("Session not found or empty", 404)
        
        matched = session.get("schemes")
        if matched:
            if isinstance(matched, str):
                try: matched = json.loads(matched)
                except: matched = []
        else:
            # Fallback for sessions where schemes weren't cached yet
            matched = match_schemes(profile, top_n=5)
        recommended_id = session.get("recommended_id")
        summary = session.get("summary")

        return ok_response({
            "session_id": sid,
            "profile": profile,
            "history": history,
            "schemes": matched,
            "summary": summary,
            "recommended_id": recommended_id,
            "total_matched": len(matched),
            "last_query": session.get("last_query", ""),
            "title": session.get("title", ""),
            "updated_at": session.get("updated_at", ""),
            "message": f"Found {len(matched)} schemes matching your saved profile.",
        })

    # GET /health
    if path.endswith("/health"):
        schemes = _load_schemes()
        return ok_response({"status": "ok", "schemes_loaded": len(schemes), "version": "3.0.0-auth"})

    # GET /history
    if path.endswith("/history") and method == "GET":
        user_id = get_user_id(event)
        if not user_id: 
            # Return empty history instead of 401 to allow app to continue
            return ok_response([])
        
        try:
            items = []
            last_key = None
            while len(items) < 20:
                scan_args = {
                    "FilterExpression": boto3.dynamodb.conditions.Attr("user_id").eq(user_id),
                    "Limit": 100
                }
                if last_key: scan_args["ExclusiveStartKey"] = last_key
                resp = sessions_table.scan(**scan_args)
                items.extend(resp.get("Items", []))
                last_key = resp.get("LastEvaluatedKey")
                if not last_key: break
            
            items = sorted(items, key=lambda x: x.get("updated_at", ""), reverse=True)
            return ok_response(_decimal_to_native(items[:20]))
        except Exception as e:
            return err_response(f"Database error: {e}")

    # DELETE /history/{session_id}
    if "/history/" in path and method == "DELETE":
        user_id = get_user_id(event)
        if not user_id: 
            return ok_response({"status": "error", "message": "Please sign in to delete history"})
        session_id = path.split("/history/")[-1]
        try:
            # Delete item only if it belongs to the user
            sessions_table.delete_item(
                Key={"session_id": session_id},
                ConditionExpression="user_id = :u",
                ExpressionAttributeValues={":u": user_id}
            )
            return ok_response({"status": "deleted", "session_id": session_id})
        except Exception as e:
            return err_response(f"Delete failed: {e}")

    # PUT /history/{session_id} (Rename)
    if "/history/" in path and method == "PUT":
        user_id = get_user_id(event)
        if not user_id: 
            return ok_response({"status": "error", "message": "Please sign in to rename sessions"})
        session_id = path.split("/history/")[-1]
        try:
            body = json.loads(event.get("body") or "{}")
            new_title = body.get("title")
            if not new_title: return err_response("Title required")
            
            sessions_table.update_item(
                Key={"session_id": session_id},
                UpdateExpression="SET title = :t",
                ExpressionAttributeValues={":t": new_title, ":u": user_id},
                ConditionExpression="user_id = :u",
                ExpressionAttributeNames={"#t": "title"}
            )
            return ok_response({"status": "renamed", "session_id": session_id, "title": new_title})
        except Exception as e:
            return err_response(f"Rename failed: {e}")

    # Parse body safely
    raw_body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        import base64
        try:
            raw_body = base64.b64decode(raw_body).decode("utf-8")
        except:
            pass # Keep as bytes if decode fails, json.loads might still handle it
    
    body = {}
    if raw_body:
        try:
            # If it's already a dict (some local tests), use it
            if isinstance(raw_body, dict):
                body = raw_body
            else:
                body = json.loads(raw_body)
        except Exception:
            # Fallback for non-JSON or broken encoding
            print(f"[handler] JSON load failed for body: {str(raw_body)[:100]}")
            if not path.endswith("/health"): # Health might not have body
                 pass 

    # POST /query
    if path.endswith("/query") and method == "POST":

        query = (body.get("query") or "").strip()
        if not query:
            return err_response("Query cannot be empty")

        user_id = get_user_id(event)
        session_id = body.get("session_id")
        session    = get_or_create_session(session_id)

        # Language resolution — prioritize Body, then Session Profile, then Default
        target_lang = str(body.get("language") or body.get("lang") or "").strip().lower()
        if not target_lang and session.get("profile"):
            target_lang = str(session["profile"].get("language") or "").strip().lower()
        target_lang = target_lang or "en"
        
        LANG_MAP = {
            "en": "en", "hi": "hi", "gu": "gu", "mr": "mr", "te": "te", "bn": "bn", "ta": "ta", "pa": "pa", "kn": "kn", "ml": "ml", "ur": "ur",
            "english": "en", "hindi": "hi", "gujarati": "gu", "marathi": "mr", "telugu": "te", "bengali": "bn", "tamil": "ta", "punjabi": "pa", "kannada": "kn", "malayalam": "ml", "urdu": "ur"
        }
        target_lang = LANG_MAP.get(target_lang, "en")
        
        print(f"[query] Resolved target_lang: {target_lang}")
        
        # Profile extraction (Treat every home page search as a fresh profile)
        profile = extract_profile(query, target_lang)

        # Merge with any known_profile provided by the client (e.g., auth consent)
        known_profile = body.get("known_profile") or {}
        if isinstance(known_profile, dict):
            for k, v in known_profile.items():
                if profile.get(k) is None:
                    profile[k] = v

        # Ensure language is saved to profile so the UI chip is correct
        profile["language"] = target_lang
        print(f"[query] Profile language set to: {profile['language']}")

        # Generate title if new session
        title = session.get("title")
        if not title:
            title = generate_title(query)

        # UPDATE: Add search to history so chatbot knows what we searched for
        history = session.get("history") or []
        if isinstance(history, str):
            try: history = json.loads(history)
            except: history = []
        
        # Don't add if history already has turns (prevents repeat on refresh)
        if not history:
            history.append({"role": "user",      "content": query})
            history.append({"role": "assistant", "content": f"I've analyzed your profile based on your query: '{query}'. You can see the matched schemes on the dashboard. How else can I help?"})

        # Match schemes (Keep at 5 for speed, but ensure they are matched first)
        matched = match_schemes(profile, top_n=5)
        
        save_session(session["session_id"], profile, query, user_id, title, history=history[:10], schemes=matched)
        
        message = f"Found {len(matched)} schemes matching your profile."
        if target_lang != "en":
            print(f"[query] Triggering async translation for {session['session_id']} into: {target_lang}")
            try:
                # VISIBILITY: Initial thread emoji indicator
                save_session(session["session_id"], profile, query, user_id, title=f"⏳ Triggering: {title or 'Results'}...", history=history[:10], schemes=matched)
                
                # Fire and forget secondary invocation
                lambda_client.invoke(
                    FunctionName="sarkarsaathi-api", # Hardcoded for safety
                    InvocationType='Event',
                    Payload=json.dumps({
                        "task_type": "async_translate",
                        "session_id": session["session_id"],
                        "target_lang": target_lang,
                        "items": matched
                    }, default=_json_serial)
                )
                message += f" Translation to regional language is in progress..."
            except Exception as e:
                print(f"[query] Async trigger failed: {e}")

            message = translate_text(message, target_lang)
            # FORCE profile language for UI consistency
            profile["language"] = target_lang

        return ok_response({
            "profile": profile,
            "schemes": matched,
            "total_matched": len(matched),
            "query_lang": profile.get("language","en"),
            "message": message,
            "session_id": session["session_id"],
        })

    # POST /tts  — High-quality speech synthesis (AWS Polly)
    if path.endswith("/tts") and method == "POST":
        try:
            return handle_tts(event, body)
        except Exception as e:
            return err_response(f"TTS failed: {e}")

    # ── AUTH ROUTES ──
    if "/auth/login" in path and method == "POST":
        if body.get("otp") != "1234": return err_response("Invalid OTP", 401)
        uid = str(uuid.uuid4())
        token = f"mock_jwt_{uid}"
        role = "operator" if body.get("is_operator") else "citizen"
        # Save to Dynamo cache_table for persistence across Lambda invocations
        try:
            cache_table.put_item(Item={"cache_key": f"token_{token}", "user_id": uid, "role": role, "phone": body.get("phone_number"), "ttl": int(time.time())+86400})
        except: pass
        return ok_response({"token": token, "user_id": uid, "role": role})

    if "/auth/me" in path and method == "GET":
        token = event.get("queryStringParameters", {}).get("token")
        if not token: return err_response("Unauthorized", 401)
        try:
            res = cache_table.get_item(Key={"cache_key": f"token_{token}"}).get("Item")
            if not res: return err_response("Unauthorized", 401)
            return ok_response({"user_id": res["user_id"], "role": res["role"], "phone": res.get("phone")})
        except: return err_response("Unauthorized", 401)

    # ── FEEDBACK ROUTES ──
    if "/feedback" in path and method == "POST":
        fb = body.copy()
        fb["cache_key"] = f"fb_{uuid.uuid4()}"
        fb["timestamp"] = datetime.utcnow().isoformat()
        try: cache_table.put_item(Item=fb)
        except: pass
        return ok_response({"status": "success", "message": "Feedback recorded successfully."})

    # POST /chat  — Adaptive CoT RAG chatbot (Amazon Nova Micro)
    if path.endswith("/chat") and method == "POST":
        start_time = time.time()
        try:
            message = (body.get("message") or "").strip()
            if not message:
                return err_response("Message cannot be empty")

            # Language resolution — prioritize Body, then Session Profile, then Default
            lang = body.get("language") or body.get("lang")
            if not lang and session.get("profile"):
                lang = session["profile"].get("language")
            lang = lang or "en"

            LANG_MAP = {
                "en": "en", "hi": "hi", "gu": "gu", "mr": "mr", "te": "te", "bn": "bn", "ta": "ta", "pa": "pa", "kn": "kn", "ml": "ml", "ur": "ur",
                "english": "en", "hindi": "hi", "gujarati": "gu", "marathi": "mr", "telugu": "te", "bengali": "bn", "tamil": "ta", "punjabi": "pa", "kannada": "kn", "malayalam": "ml", "urdu": "ur"
            }
            if lang.lower() in LANG_MAP: lang = LANG_MAP[lang.lower()]
            
            # Fallback regex ONLY if language is still "en" and message is CLEARLY an Indian script
            # AND no explicit language was found in body or session
            if (not (body.get("language") or body.get("lang"))) and (not session.get("profile", {}).get("language")) and lang == "en":
                script_lang = _detect_lang_from_script(message)
                if script_lang: lang = script_lang

            # GREETING CHECK: If message is a simple greeting, we should converse first, not dump schemes.
            msg_lower = message.lower().strip().strip("?!.")
            is_greeting = msg_lower in ["hi", "hello", "hey", "namaste", "namaskaram", "namaskara", "vanakkam", "pranam", "salaam", "नमस्ते", "வணக்கம்", "नमस्कार", "നമസ്കാരം", "నమస్కారం", "ನಮಸ್ಕಾರ"]

            # Session
            user_id    = get_user_id(event)
            session_id = body.get("session_id")
            session    = get_or_create_session(session_id)

            # ── History for context ──
            history = session.get("history") or []
            if isinstance(history, str):
                try: history = json.loads(history)
                except: history = []
            
            last_bot_msg = ""
            if history:
                for turn in reversed(history):
                    if turn["role"] == "assistant":
                        last_bot_msg = turn["content"]
                        break

            # Profile extraction + session merge - SKIP Bedrock if message is short OR NOT English to save 8-10s
            # (Rule-based is enough for chat flow in regional languages)
            is_shorter = len(message) < 20
            if is_shorter or lang != "en":
                profile = rule_based_extract(message, lang)
            else:
                profile = extract_profile(message, lang)
            
            # ── Context Inference for short answers ──
            # If primary extraction missed something, try inferring from last bot question
            inferred = _infer_from_context(message, last_bot_msg, profile)
            for k, v in inferred.items():
                if profile.get(k) is None:
                    profile[k] = v

            old = session.get("profile") or {}
            if isinstance(old, str):
                try: old = json.loads(old)
                except: old = {}
            old = _decimal_to_native(old)

            # Also merge any profile pre-loaded from the main search page
            known_profile = body.get("known_profile") or {}
            if isinstance(known_profile, dict):
                for field in ["age","gender","marital_status","occupation","income_level",
                              "location_type","state","caste","children","needs","consent_given"]:
                    # FIX: Use 'is None' explicitly to avoid overwriting 0 (zero)
                    if profile.get(field) is None:
                        val = known_profile.get(field)
                        # Explicit check for 0
                        if val is None or val == "": 
                            val = old.get(field)
                            
                        if val is not None and str(val) != "":
                            profile[field] = val
            else:
                for field in ["age","gender","marital_status","occupation","income_level",
                              "location_type","state","caste","children"]:
                    if profile.get(field) is None and old.get(field) is not None:
                        profile[field] = old[field]
            profile["language"] = lang

            save_session(session["session_id"], profile, message, user_id)
            print(f"[chat] T+ {time.time()-start_time:.2f}s: Profile extracted")

            # RAG retrieval
            print(f"[chat] T+ {time.time()-start_time:.2f}s: Loading schemes...")
            matched = match_schemes(profile, top_n=5)
            print(f"[chat] T+ {time.time()-start_time:.2f}s: Schemes matched ({len(matched)})")
            
            # Multilingual Translation for Chat Results (Translate top 3 shown in dashboard for regional)
            if lang != "en":
                # HYPER-OPTIMIZATION: 4s strict timeout (prev 5s) to stay under 29s
                # Also only translate top 3 to guarantee speed
                print(f"[chat] T+ {time.time()-start_time:.2f}s: Starting Translation...")
                matched = _batch_translate(matched[:3], lang, wait_timeout=4.0, start_time=start_time)
                print(f"[chat] T+ {time.time()-start_time:.2f}s: Translation done (or timed out)")

            # (History already loaded above for context inference)

            # Determine if we have enough profile data to show schemes
            key_fields = ["age", "gender", "occupation", "state", "income_level", "caste"]
            known_fields = sum(1 for f in key_fields if profile.get(f))

            # Only "profile_ready" if it's NOT a simple greeting
            # Relaxed: If we have ANY key info, we can show basics.
            profile_ready = (known_fields >= 1) and (not is_greeting)

            # Build AI response
            ai_response = _nova_chat(message, profile, matched[:5] if profile_ready else [], history, lang, start_time=start_time)
            print(f"[chat] T+ {time.time()-start_time:.2f}s: AI Response generated")

            # Only generate summary in English (redundant for regional where time is tight)
            summary = None
            if lang == "en" and body.get("include_summary") and matched and profile_ready and not is_short:
                summary = _nova_summarize(profile, matched[:5], lang)

            # Update history (keep last 10 turns)
            history = (history + [
                {"role": "user",      "content": message},
                {"role": "assistant", "content": ai_response},
            ])[-10:]

            # Generate title if missing
            title = session.get("title")
            if not title:
                title = generate_title(message)

            # Extract a recommended_id from matched if summary exists
            recommended_id = matched[0]["id"] if matched and summary else session.get("recommended_id")

            save_session(session["session_id"], profile, message, user_id, title, history=history, summary=summary, recommended_id=recommended_id)

            return ok_response({
                "session_id": session["session_id"],
                "response":   ai_response,
                "summary":    summary,
                "schemes":    matched[:5] if (matched and known_fields >= 1) else [],
                "profile":    profile,
                "language":   lang,
                "profile_score": known_fields,
            })

        except Exception as e:
            import traceback
            print(f"[chat] UNHANDLED ERROR: {e}\n{traceback.format_exc()}")
            return err_response(f"Internal error: {str(e)}", 500)

    return err_response("Not found", 404)


# ── Nova Micro helpers ────────────────────────────────────────────────────────

NOVA_MODEL_ID = os.environ.get("NOVA_MODEL_ID", "amazon.nova-micro-v1:0")
NOVA_MAX_TOK  = int(os.environ.get("NOVA_MAX_TOKENS", "512"))

_CHAT_SYS = (
    "You are SarkarSaathi, a warm Indian government scheme assistant. "
    "Help the user discover schemes they qualify for through NATURAL conversation. "
    "\n\nCONVERSATION RULES:"
    "\n1. GREETING: Only greet once at the very start of a conversation. NEVER say 'Hello!' or 'Hi there!' in subsequent replies — it sounds robotic. Just respond directly."
    "\n2. SHORT replies — 1-3 sentences MAX. Never dump a list."
    "\n3. DO NOT ask for information already listed in the user profile. Only ask for MISSING fields."
    "\n4. Ask ONE question at a time to fill the gaps: missing fields from [age, gender, state, occupation, income, caste/category, family situation]."
    "\n5. Once you have 3-4 facts, mention 1-2 specific relevant schemes with WHY they qualify."
    "\n6. If user expresses financial hardship, debts, or crisis — IMMEDIATELY acknowledge and mention relevant debt relief / welfare schemes."
    "\n7. STICK TO TOPIC: If the user asks a follow-up question (e.g., 'How to apply?', 'Link?', 'Eligibility?') about a scheme you JUST mentioned, answer that question specifically. DO NOT pivot to a new scheme until you have fully answered their current query."
    "\n8. For VOICE MODE: Use conversational fillers like 'I see', 'Okay', 'Hmm' occasionally. No bullet points, no asterisks, no markdown. Keep replies under 25 words. Speak like a friendly human neighbor."
    "\n9. Be empathetic — many users are first-time applicants feeling overwhelmed."
    "\n\nRemember: natural conversation, NOT a form. Never re-greet. Never re-ask what you already know. Stay on topic! Be human!"
)
_SUM_SYS = (
    "You are a government scheme advisor. Given a user profile and matching schemes, "
    "write a warm, personalized 80-word recommendation as if speaking directly to the user. "
    "Highlight the SINGLE best scheme and exactly WHY this person qualifies. "
    "Mention 1 other option in one sentence. End with a clear next step. "
    "NO bullet points, NO markdown. Plain conversational sentences. "
    "Respond in the user's language (Hindi = Hindi, English = English)."
)

_nova_client = None
def _get_nova():
    global _nova_client
    if _nova_client is None:
        _nova_client = boto3.client("bedrock-runtime", region_name=REGION)
    return _nova_client

def _batch_translate(items, target_lang, wait_timeout=50.0, start_time=None):
    """Translate multiple fields in parallel chunks of 5 with global timeout safety."""
    if not items or target_lang.lower() in ["en", "english"]: return items
    
    # ── Global Timeout Safety ──
    if start_time and (time.time() - start_time) > 20.0:
        print("[batch_translate] SKIPPING: Already exceeded 20s budget")
        return items
    LANG_NAME_MAP = {
        "hi": "Hindi", "gu": "Gujarati", "mr": "Marathi", "ta": "Tamil",
        "te": "Telugu", "bn": "Bengali", "kn": "Kannada", "ur": "Urdu",
        "ml": "Malayalam", "pa": "Punjabi"
    }
    lang_full = LANG_NAME_MAP.get(target_lang.lower(), target_lang)

    CHUNK_SIZE = 5  # Batch all items into a single parallel translation wave to ensure we stay under the 30s timeout
    chunks = [items[i : i + CHUNK_SIZE] for i in range(0, len(items), CHUNK_SIZE)]
    
    def translate_chunk(chunk, start_idx):
        import time, random
        to_translate = []
        for i, item in enumerate(chunk):
            real_idx = start_idx + i
            to_translate.append(f"NAME_{real_idx}: {item.get('name') or item.get('name_en','')}")
            to_translate.append(f"BENEFIT_{real_idx}: {item.get('benefit_description','')}")
            to_translate.append(f"REASON_{real_idx}: {item.get('eligibility_reason','')}")
            to_translate.append(f"APPLY_{real_idx}: {item.get('how_to_apply','')}")
            to_translate.append(f"OFFICE_{real_idx}: {item.get('nodal_office','')}")
            state = item.get('state') or 'General'
            category = item.get('category') or item.get('scheme_category') or 'Social Welfare'
            to_translate.append(f"STATE_{real_idx}: {state}")
            to_translate.append(f"CAT_{real_idx}: {category}")
            docs = item.get('required_documents', [])
            if docs: to_translate.append(f"DOCS_{real_idx}: {' | '.join(docs)}")
            steps = item.get('application_steps', [])
            if steps: to_translate.append(f"STEPS_{real_idx}: {' | '.join(steps)}")
        
        combined_text = "\n---\n".join(to_translate)
        prompt = f"""You are a professional multilingual translator. Your goal is to translate Indian government scheme data into {lang_full}.
        
        FORMAT RULES:
        1. DO NOT RETURN JSON. RETURN PLAIN TEXT.
        2. For each line in the data formatted as "KEY: text", output EXACTLY "KEY: translated_text".
        3. Translate EVERYTHING in the text to {lang_full}.
        4. For proper names (like 'Goa'), use the common transliteration in {lang_full}.
        5. Do NOT leave any part of the text in English.
        6. Do NOT add any preamble or extra text.
        
        Data to translate:
        {combined_text}"""
        
        for attempt in range(1): # Reduced retries to 1 for speed
            if start_time and (time.time() - start_time) > 23.0: break # Bail out if we're hitting the 29s gate
            try:
                resp = bedrock.invoke_model(
                    modelId=BEDROCK_MODEL,
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 1024, "temperature": 0.4,
                        "messages": [{"role": "user", "content": prompt}]
                    }),
                    contentType="application/json", accept="application/json",
                )
                resp_body = json.loads(resp["body"].read())
                text = resp_body["content"][0]["text"].strip()
                
                # Custom parse the custom delimiter format with better error handling
                parsed_res = {}
                for line in text.split("\n"):
                    line = line.strip()
                    if ":" in line:
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            # Strip markdown bolding that AI might add around keys
                            key = key.replace("**", "").replace('"', '').replace("'", "")
                            val = parts[1].strip()
                            # Skip empty keys or values
                            if key and val and key.startswith(("NAME_", "BENEFIT_", "REASON_", "APPLY_", "OFFICE_", "STATE_", "CAT_", "DOCS_", "STEPS_")):
                                parsed_res[key] = val
                
                if len(parsed_res) > 0:
                    return parsed_res
            except Exception as e:
                print(f"[translate_chunk] Attempt {attempt+1} failed: {e}")
                if attempt < 3:
                    time.sleep(0.5 + random.random() * (1.5 ** attempt))
        return {}

    # Scale concurrency: Process each item in its own task with a strict timeout
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Submit each scheme as a separate translation task
        future_to_idx = {
            executor.submit(translate_chunk, [item], i): i 
            for i, item in enumerate(items)
        }
        
        # Greedy wait: In background mode, we can wait much longer (up to Lambda 60s limit)
        # We use 50s to be safe
        done, not_done = concurrent.futures.wait(
            future_to_idx.keys(), 
            timeout=wait_timeout, 
            return_when=concurrent.futures.ALL_COMPLETED
        )
        
        for f in done:
            try:
                res = f.result()
                if res:
                    # Apply translation immediately to the items list
                    for key, content in res.items():
                        try:
                            parts = key.split("_")
                            if len(parts) >= 2:
                                prefix_type = parts[0].upper()
                                idx = int(parts[1])
                                if idx < len(items):
                                    if prefix_type == "NAME":
                                        items[idx]["name"] = content
                                        items[idx]["name_en"] = content
                                        # Dynamically sync the regional field
                                        items[idx][f"name_{target_lang.lower()}"] = content
                                    elif prefix_type == "BENEFIT": items[idx]["benefit_description"] = content
                                    elif prefix_type == "REASON": items[idx]["eligibility_reason"] = content
                                    elif prefix_type == "APPLY": items[idx]["how_to_apply"] = content
                                    elif prefix_type == "OFFICE": items[idx]["nodal_office"] = content
                                    elif prefix_type == "STATE": items[idx]["state"] = content
                                    elif prefix_type == "CAT": items[idx]["category"] = content
                                    elif prefix_type == "DOCS": 
                                        items[idx]["required_documents"] = [x.strip() for x in content.replace("|", "\n").split("\n") if x.strip()]
                                    elif prefix_type == "STEPS": 
                                        items[idx]["application_steps"] = [x.strip() for x in content.replace("|", "\n").split("\n") if x.strip()]
                        except: pass
            except: pass
        
        if not_done:
            print(f"[batch_translate] {len(not_done)} translation tasks timed out after {wait_timeout}s.")
            for f in not_done: f.cancel()
    
    return items

def _chat_converse(system_text, user_text):
    """Use Claude 3 Haiku for conversation to ensure strong multilingual support."""
    try:
        resp = bedrock.invoke_model(
            modelId=BEDROCK_MODEL,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024, "temperature": 0.4,
                "system": system_text,
                "messages": [{"role": "user", "content": user_text}]
            }),
            contentType="application/json", accept="application/json",
        )
        resp_body = json.loads(resp["body"].read())
        return resp_body["content"][0]["text"].strip()
    except Exception as e:
        print(f"[chat_converse] Haiku failed: {e}")
        # ── Fallback: OpenRouter ─────────────────────────────────────────────
        try:
            print(f"[chat_converse] Using OpenRouter fallback ({OPENROUTER_MODEL})...")
            return _openrouter_call(system_text, user_text)
        except Exception as e3:
            print(f"[chat_converse] OpenRouter fallback also failed: {e3}")
            return f"I'm having trouble connecting to the AI. (Error: {str(e3)[:50]}...)"



_REACT_SYSTEM_PROMPT = """You are SarkarSaathi, a helpful Indian government scheme assistant.
You solve tasks using a Reasoning and Acting (ReAct) loop.

You have access to the following tools:

1. ask_user(question: str): Ask the user a clarifying question or ask for their PII consent.
2. check_eligibility(): You have already been provided the user's profile and matching schemes in the context. Use this tool when you have enough profile information (like age, income, state, caste) to give scheme recommendations to the user based on the context.
3. record_consent(): Use this when the user explicitly agrees to share their information.

You must follow this exact format:

Thought: [Consider the current state, missing profile information, consent status, etc.]
Action: [The name of the tool to use: 'ask_user', 'check_eligibility', or 'record_consent']
Action Input: [The input string for the tool, if applicable. Leave blank if not]
Observation: [The result of the action - this will be provided by the system]
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now have the final answer.
Final Answer: [The final response to send to the user, strictly in the requested language (e.g. Urdu, Telugu, etc.)]

CRITICAL RULES:
- The user MUST give explicit consent before you can process their caste, income, or other sensitive data. If `consent_given` is False, your FIRST action must be to ask for their consent using `ask_user`.
- Once they consent, use `record_consent`.
- YOU MUST RESPOND IN THE REQUESTED LANGUAGE: {lang_full}. Even if the user asks in English, if the session language is set to {lang_full}, you MUST respond in {lang_full}.
- If there are 0 schemes returned from `check_eligibility`, you MUST handle this gracefully in the Final Answer, empathetically telling them there are no specific schemes right now, but offering general advice.
"""

def _nova_chat(message, profile, top_schemes, history, lang, start_time=None):
    profile_context = ""
    if profile:
        parts = []
        for f in ["age", "gender", "occupation", "state", "income_level", "caste"]:
            val = profile.get(f)
            if val is not None and str(val) != "": parts.append(f"{f}: {val}")
        parts.append(f"Consent Given: {profile.get('consent_given', False)}")
        profile_context = "\n\nUser profile: " + " | ".join(parts)

    scheme_context = ""
    if top_schemes:
        scheme_lines = []
        for i, s in enumerate(top_schemes, 1):
            # Dynamic field selection based on language 
            name = s.get(f"name_{lang}") or s.get("name_en") or s.get("name") or "Scheme"
            scheme_lines.append(f"{i}. {name} — {s.get('benefit_description', '')} (Why: {s.get('eligibility_reason', '')})")
        scheme_context = "\n\nAvailable matching schemes:\n" + "\n".join(scheme_lines)
    else:
        scheme_context = "\n\nAvailable matching schemes: NONE (0 eligible schemes found)."

    hist_ctx = ""
    if history:
        turns = [f"{'User' if t['role']=='user' else 'Assistant'}: {t['content']}" for t in history[-4:]]
        hist_ctx = "\n\nConversation history:\n" + "\n".join(turns)

    LANG_NAME_MAP = {
        "hi": "Hindi", "gu": "Gujarati", "mr": "Marathi", "ta": "Tamil",
        "te": "Telugu", "bn": "Bengali", "kn": "Kannada", "ur": "Urdu",
        "ml": "Malayalam", "pa": "Punjabi", "en": "English"
    }
    lang_full = LANG_NAME_MAP.get(lang, "English")

    # Use a conversational prompt for non-English to guarantee a natural speed-turn
    sys_prompt = _REACT_SYSTEM_PROMPT
    if lang != "en":
        sys_prompt = (
            "You are SarkarSaathi, a friendly Indian government scheme advisor. "
            "Help the user discover and understand schemes naturally. "
            "IMPORTANT: "
            "1. If the user just greeted you (e.g. Namaste, Hello), DO NOT dump scheme names. Just greet them back warmly and ask how you can help. "
            "2. If schemes are provided in the context, ONLY mention them if the user specifically asked for recommendations or if they directly answer the user's question. "
            "3. BE CONVERSATIONAL. Don't repeat the same scheme descriptions in every turn if you've already said them. Look at the 'Conversation history' to see what you just said. "
            "4. If the user asks about a specific state or category, focus your whole answer on that. "
            "5. Respond strictly in the requested language."
        )

    prompt_context = f"User query: {message}{profile_context}{scheme_context}{hist_ctx}\n\nRespond in language: {lang_full}\n"
    
    # HYPER-SPEED: Single turn with Haiku (much faster & reliable for multilingual)
    try:
        resp = bedrock.invoke_model(
            modelId=BEDROCK_MODEL,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": NOVA_MAX_TOK,
                "temperature": 0.4,
                "system": sys_prompt,
                "messages": [{"role": "user", "content": prompt_context}]
            }),
            contentType="application/json", accept="application/json",
        )
        response = json.loads(resp["body"].read())["content"][0]["text"].strip()
        
        if "Final Answer:" in response:
            return response.split("Final Answer:", 1)[1].strip()
        return response
    except Exception as e:
        print(f"[_nova_chat] Haiku Speed-Turn Error: {e}")
        return "I apologize, but I am unable to process your request at this time."


def _nova_summarize(profile, schemes, lang):
    pparts = []
    for f, label in [("age","Age"),("gender","Gender"),("occupation","Occupation"),
                     ("state","State"),("income_level","Income"),("caste","Category")]:
        val = profile.get(f)
        if val is not None and str(val) != "": pparts.append(f"{label}: {val}")
    profile_desc = ", ".join(pparts) if pparts else "a citizen"

    scheme_lines = []
    for i, s in enumerate(schemes, 1):
        name = s.get("name_hi") if lang == "hi" else s.get("name_en") or s.get("name","")
        scheme_lines.append(
            f"{i}. {name}\n   Benefit: {s.get('benefit_description','')}\n"
            f"   Why: {s.get('eligibility_reason','')}\n   Apply: {s.get('how_to_apply','')}"
        )

    LANG_DISP = {
        "en": "English", "hi": "Hindi", "gu": "Gujarati", "mr": "Marathi",
        "te": "Telugu", "bn": "Bengali", "ta": "Tamil", "pa": "Punjabi",
        "kn": "Kannada", "ml": "Malayalam", "ur": "Urdu"
    }
    lang_label = LANG_DISP.get(lang.lower(), "English")
    
    prompt = f"User profile: {profile_desc}\nSchemes matched:\n" + "\n".join(scheme_lines) + f"\n\nInstruction: Summarize the schemes for the user based on their profile. CRITICAL: YOU MUST REPLY STRICTLY IN {lang_label.upper()}."
    
    return _chat_converse(_SUM_SYS, prompt)

def handle_tts(event, body):
    """Generate high-quality speech using a Romanized transliteration + Polly English-Indian voice."""
    print("[tts] V2_ROMANIZED_ACTIVE")
    from botocore.config import Config
    
    text = body.get("text", "").strip()
    lang = (body.get("language") or "en").lower()
    if not text:
        return err_response("Missing text", 400)

    # Use Mumbai (ap-south-1) for Polly to be safe, though Kajal (Neural) is in us-east-1 too
    polly_client = boto3.client("polly", region_name="us-east-1", config=Config(parameter_validation=False))
    
    # ── 1. Transliterate to Romanized English script using Bedrock ─────────────────
    romanized_text = text
    if lang != "en":
        # Map ISO code to full name for Bedrock prompt clarity
        full_langs = {
            "hi": "Hindi", "gu": "Gujarati", "mr": "Marathi", "bn": "Bengali",
            "ta": "Tamil", "te": "Telugu", "kn": "Kannada", "ur": "Urdu",
            "ml": "Malayalam"
        }
        lang_name = full_langs.get(lang, lang)
        
        try:
            # Log hex bytes of text to debug encoding issues
            print(f"[tts] Text bytes: {text.encode('utf-8').hex()}")
            
            # Simple, direct prompt for Haiku
            prompt = f"Convert this {lang_name} text into phonetic English (Roman script). Return ONLY the phonetic result. Text: {text}"
            
            bedrock = boto3.client("bedrock-runtime", region_name=REGION)
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}]
            }
            resp = bedrock.invoke_model(
                modelId="anthropic.claude-3-haiku-20240307-v1:0",
                body=json.dumps(payload)
            )
            raw_body = resp['body'].read().decode('utf-8')
            result = json.loads(raw_body)
            romanized_text = result['content'][0]['text'].strip()
            print(f"[tts] Romanized ({lang}): {romanized_text}")
        except Exception as e:
            print(f"[tts] Transliterate failed, falling back: {e}")
            romanized_text = text

    # ── 2. Synthesize using high-quality Neural English-Indian voice ────────────────
    try:
        # We always use Kajal (Neural hi-IN) because it handles Romanized Indian text beautifully
        kwargs = {
            "OutputFormat": "mp3",
            "Text": romanized_text,
            "VoiceId": "Kajal",
            "Engine": "neural",
            "LanguageCode": "hi-IN"
        }

        resp = polly_client.synthesize_speech(**kwargs)
        
        import base64
        audio_data = base64.b64encode(resp['AudioStream'].read()).decode('utf-8')
        
        return ok_response({
            "audio": audio_data,
            "format": "mp3",
            "romanized": romanized_text if lang != "en" else None
        })
    except Exception as e:
        print(f"[tts] error: {e}")
        return err_response(f"Speech synthesis failed: {str(e)}", 500)
