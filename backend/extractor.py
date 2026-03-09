"""
Profile Extraction Module for SarkarSaathi.
Supports Hindi and English using regex-based NLP patterns.
No external ML models required — fully offline.
"""
import re
import json
from typing import List, Optional
from models import UserProfile

# ─── language detection (simple heuristic for Hindi Unicode block) ───────────
HINDI_UNICODE_RE = re.compile(r'[\u0900-\u097F]')

def detect_language(text: str) -> str:
    """Return 'hi' if text contains Devanagari characters, else 'en'."""
    return "hi" if HINDI_UNICODE_RE.search(text) else "en"


# ─── keyword dictionaries ────────────────────────────────────────────────────
GENDER_KEYWORDS = {
    "male":   ["male", "man", "boy", "he", "his", "पुरुष", "लड़का", "आदमी", "मैं पुरुष", "मर्द"],
    "female": ["female", "woman", "girl", "she", "her", "widow", "महिला", "औरत", "लड़की", "विधवा", "मैं महिला"],
}

MARITAL_KEYWORDS = {
    "widowed":   ["widow", "widower", "widowed", "विधवा", "विधुर", "पति की मृत्यु", "पत्नी की मृत्यु"],
    "unmarried": ["unmarried", "single", "bachelor", "अविवाहित", "कुंवारा", "कुंवारी"],
    "divorced":  ["divorced", "divorce", "तलाकशुदा", "तलाक"],
    "married":   ["married", "wife", "husband", "spouse", "विवाहित", "शादीशुदा", "पत्नी", "पति"],
}

OCCUPATION_KEYWORDS = {
    "farmer":      ["farmer", "farming", "agriculture", "kisan", "किसान", "खेती", "कृषक", "खेत"],
    "student":     ["student", "studying", "study", "school", "college", "university", "छात्र", "छात्रा", "पढ़ाई", "विद्यार्थी"],
    "unemployed":  ["unemployed", "no job", "jobless", "no work", "बेरोजगार", "काम नहीं", "नौकरी नहीं"],
    "salaried":    ["salaried", "job", "employee", "office", "नौकरी", "कर्मचारी", "सरकारी नौकरी"],
    "self_employed": ["self employed", "business", "shop", "vyapari", "व्यापारी", "दुकान", "व्यवसाय"],
    "daily_wage":  ["daily wage", "labourer", "labor", "mazdoor", "मजदूर", "दिहाड़ी"],
    "artisan":    ["artisan", "craftsman", "weaver", "potter", "कारीगर", "बुनकर", "कुम्हार"],
    "fisherman":  ["fisherman", "fishing", "fisher", "मछुआरा", "मछली पकड़"],
}

LOCATION_KEYWORDS = {
    "rural":      ["rural", "village", "gram", "panchayat", "grama", "गांव", "ग्राम", "देहात", "ग्रामीण"],
    "urban":      ["urban", "city", "town", "municipal", "शहर", "नगर", "शहरी"],
    "semi-urban": ["semi urban", "semi-urban", "kasba", "कस्बा", "अर्ध-शहरी"],
}

CASTE_KEYWORDS = {
    "sc": ["sc", "scheduled caste", "dalit", "harijan", "अनुसूचित जाति", "दलित"],
    "st": ["st", "scheduled tribe", "tribal", "adivasi", "अनुसूचित जनजाति", "आदिवासी", "वनवासी"],
    "obc": ["obc", "other backward", "पिछड़ा", "ओबीसी", "अन्य पिछड़ा वर्ग"],
    "general": ["general", "open", "forward", "सामान्य", "जनरल"],
}

NEEDS_KEYWORDS = {
    "housing":   ["house", "home", "awas", "ghar", "shelter", "flat", "घर", "आवास", "मकान"],
    "education": ["education", "school", "college", "scholarship", "study", "पढ़ाई", "शिक्षा", "छात्रवृत्ति"],
    "health":    ["health", "medical", "hospital", "treatment", "illness", "स्वास्थ्य", "इलाज", "बीमारी", "अस्पताल"],
    "food":      ["food", "ration", "grain", "atta", "rice", "राशन", "अनाज", "भोजन", "खाना"],
    "employment":["job", "employment", "work", "rozgar", "नौकरी", "रोजगार", "काम"],
    "pension":   ["pension", "old age", "वृद्धा", "पेंशन", "बुजुर्ग"],
    "marriage":  ["marriage", "wedding", "shaadi", "शादी", "विवाह", "byah"],
    "disability":["disability", "disabled", "handicap", "divyang", "विकलांग", "दिव्यांग"],
    "business_loan": ["loan", "capital", "business loan", "udyam", "ऋण", "लोन", "कर्ज", "उद्यम"],
}

INDIAN_STATES = {
    "andhra pradesh": "Andhra Pradesh", "ap": "Andhra Pradesh",
    "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "bihar": "Bihar",
    "chhattisgarh": "Chhattisgarh",
    "goa": "Goa",
    "gujarat": "Gujarat",
    "haryana": "Haryana",
    "himachal pradesh": "Himachal Pradesh",
    "jharkhand": "Jharkhand",
    "karnataka": "Karnataka",
    "kerala": "Kerala",
    "madhya pradesh": "Madhya Pradesh", "mp": "Madhya Pradesh",
    "maharashtra": "Maharashtra",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "odisha": "Odisha", "orissa": "Odisha",
    "punjab": "Punjab",
    "rajasthan": "Rajasthan",
    "sikkim": "Sikkim",
    "tamil nadu": "Tamil Nadu",
    "telangana": "Telangana",
    "tripura": "Tripura",
    "uttar pradesh": "Uttar Pradesh", "up": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand",
    "west bengal": "West Bengal",
    "delhi": "Delhi", "new delhi": "Delhi",
    # Hindi state names
    "उत्तर प्रदेश": "Uttar Pradesh", "महाराष्ट्र": "Maharashtra",
    "राजस्थान": "Rajasthan", "बिहार": "Bihar", "पंजाब": "Punjab",
    "हरियाणा": "Haryana", "गुजरात": "Gujarat", "मध्य प्रदेश": "Madhya Pradesh",
    "दिल्ली": "Delhi", "पश्चिम बंगाल": "West Bengal",
}


def extract_age(text: str) -> Optional[int]:
    """Extract age from text using regex patterns."""
    patterns = [
        r'(\d{1,2})\s*(?:साल|वर्ष|year|years|yr|yrs)\s*(?:का|की|के|old)?',
        r'(?:age|aged|umra|umar|उम्र|आयु)\s*[:\-]?\s*(\d{1,2})',
        r'(\d{1,2})\s*(?:का|की)\s*(?:हूं|हूँ|हो)',
        r'मैं\s*(\d{1,2})\s*(?:साल|वर्ष)',
        r'i\s+am\s+(\d{1,2})',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            age = int(m.group(1))
            if 5 <= age <= 100:
                return age
    return None


def extract_income(text: str) -> Optional[int]:
    """Extract annual income in INR from text."""
    # Handle lakh/lacs
    lakh_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:लाख|lakh|lac|lacs)\s*(?:rupees|रुपये|rs|₹)?',
        r'(?:income|salary|आमदनी|आय|कमाई|तनख्वाह)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lac|लाख)',
    ]
    for p in lakh_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return int(float(m.group(1)) * 100000)

    # Handle thousands / plain numbers with currency
    k_patterns = [
        r'(\d{4,7})\s*(?:rupees|रुपये|rs|₹)',
        r'(?:income|salary|आमदनी|आय)\s*[:\-]?\s*(\d{4,7})',
    ]
    for p in k_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 1000 <= val <= 10000000:
                return val
    return None


def extract_children(text: str) -> Optional[int]:
    """Extract number of children."""
    patterns = [
        r'(\d+)\s*(?:बच्चे|बच्चों|children|child|kids|bachche)',
        r'(?:children|बच्चे)\s*[:\-]?\s*(\d+)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def match_keyword(text: str, keyword_dict: dict) -> Optional[str]:
    """Match text against keyword dict, return the matched category."""
    text_lower = text.lower()
    for category, keywords in keyword_dict.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                return category
    return None


def extract_needs(text: str) -> List[str]:
    """Extract list of needs from text."""
    text_lower = text.lower()
    needs = []
    for need, keywords in NEEDS_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                needs.append(need)
                break
    return needs


def extract_state(text: str) -> Optional[str]:
    """Extract Indian state name from text."""
    text_lower = text.lower()
    for key, value in INDIAN_STATES.items():
        if key.lower() in text_lower:
            return value
    return None


def extract_profile(query: str, preferred_lang: Optional[str] = None) -> UserProfile:
    """
    Main extraction function.
    Parses user query (Hindi or English) and returns a structured UserProfile.
    """
    lang = preferred_lang or detect_language(query)
    text = query

    age = extract_age(text)
    income = extract_income(text)
    children = extract_children(text)
    gender = match_keyword(text, GENDER_KEYWORDS)
    marital_status = match_keyword(text, MARITAL_KEYWORDS)
    occupation = match_keyword(text, OCCUPATION_KEYWORDS)
    location_type = match_keyword(text, LOCATION_KEYWORDS)
    caste = match_keyword(text, CASTE_KEYWORDS)
    needs = extract_needs(text)
    state = extract_state(text)

    # Infer gender from marital status if not detected
    if marital_status == "widowed" and gender is None:
        # Check for widower vs widow
        if any(w in text.lower() for w in ["विधुर", "widower"]):
            gender = "male"
        else:
            gender = "female"

    # Infer needs from occupation
    if occupation == "student" and "education" not in needs:
        needs.append("education")
    if occupation == "unemployed" and "employment" not in needs:
        needs.append("employment")

    return UserProfile(
        age=age,
        gender=gender,
        marital_status=marital_status,
        children=children,
        occupation=occupation,
        income_level=income,
        location_type=location_type,
        state=state,
        caste=caste,
        needs=needs,
        language=lang,
    )
