"""
Eligibility Matching Engine for SarkarSaathi.
Pure Python — no external dependencies. Loads schemes at startup.
"""
import json
import os
from typing import List, Dict, Any

from models import UserProfile, SchemeMatch

# Load schemes at module import time (memory-efficient, fast)
_SCHEMES_PATH = os.path.join(os.path.dirname(__file__), "data", "schemes.json")
_SCHEMES: List[Dict[str, Any]] = []


def load_schemes() -> None:
    """Load schemes.json into memory. Called at FastAPI startup."""
    global _SCHEMES
    with open(_SCHEMES_PATH, "r", encoding="utf-8") as f:
        _SCHEMES = json.load(f)
    print(f"[matcher] Loaded {len(_SCHEMES)} schemes into memory.")


def get_schemes() -> List[Dict]:
    return _SCHEMES


def _check_eligibility(scheme: Dict, profile: UserProfile) -> tuple[bool, int, List[str]]:
    """
    Check if a user is eligible for a scheme.
    Returns (is_eligible, score, reasons).
    Hard filters (False) disqualify immediately.
    Soft matches add to score.
    """
    rules = scheme.get("eligibility", {})
    score = 0
    reasons = []

    # ── Hard filters ────────────────────────────────────────────────────
    # Age
    if profile.age is not None:
        age_min = rules.get("age_min")
        age_max = rules.get("age_max")
        if age_min and profile.age < age_min:
            return False, 0, []
        if age_max and profile.age > age_max:
            return False, 0, []
        if age_min or age_max:
            score += 2
            reasons.append(f"Age {profile.age} fits ({age_min or 0}–{age_max or '∞'})")

    # Gender
    scheme_gender = rules.get("gender")
    if scheme_gender and scheme_gender != "any":
        if profile.gender and profile.gender != scheme_gender:
            return False, 0, []
        if profile.gender == scheme_gender:
            score += 2
            reasons.append(f"Gender matches ({scheme_gender})")

    # Income
    income_max = rules.get("income_max")
    if income_max and profile.income_level is not None:
        if profile.income_level > income_max:
            return False, 0, []
        score += 2
        reasons.append(f"Income ₹{profile.income_level:,} within limit ₹{income_max:,}")

    # State (ALL means national scheme)
    scheme_state = scheme.get("state", "ALL")
    if scheme_state != "ALL" and profile.state:
        if profile.state.lower() != scheme_state.lower():
            return False, 0, []
        score += 2
        reasons.append(f"State matches ({profile.state})")
    elif scheme_state == "ALL":
        score += 1
        reasons.append("National scheme (all states)")

    # ── Soft matches ─────────────────────────────────────────────────────
    scheme_category = scheme.get("category", "")

    # Occupation — both explicit rules AND category-based inference
    OCCUPATION_CATEGORY_MAP = {
        "farmer":       ["agriculture"],
        "student":      ["education", "skill"],
        "unemployed":   ["employment", "skill"],
        "daily_wage":   ["employment", "social_welfare"],
        "self_employed":["business"],
        "artisan":      ["business", "skill"],
        "fisherman":    ["agriculture"],
        "salaried":     ["social_welfare", "health"],
    }
    scheme_occupations = rules.get("occupation", [])
    if scheme_occupations:
        if profile.occupation and profile.occupation in scheme_occupations:
            score += 4
            reasons.append(f"Occupation '{profile.occupation}' matches")
        elif profile.occupation and profile.occupation not in scheme_occupations:
            pass  # Not disqualifying, just no bonus
    elif profile.occupation:  # No explicit occupation rule — infer from category
        good_cats = OCCUPATION_CATEGORY_MAP.get(profile.occupation, [])
        if scheme_category in good_cats:
            score += 3
            reasons.append(f"Scheme category '{scheme_category}' aligns with occupation '{profile.occupation}'")

    # Marital status
    scheme_marital = rules.get("marital_status", [])
    if scheme_marital:
        if profile.marital_status and profile.marital_status in scheme_marital:
            score += 4
            reasons.append(f"Marital status '{profile.marital_status}' matches")
        elif profile.marital_status and profile.marital_status not in scheme_marital:
            return False, 0, []  # Hard disqualifier for specific marital-status schemes

    # Location type
    scheme_location = rules.get("location_type")
    if scheme_location and scheme_location != "any":
        if profile.location_type and profile.location_type == scheme_location:
            score += 2
            reasons.append(f"Location type '{profile.location_type}' matches")
        elif profile.location_type and profile.location_type != scheme_location:
            return False, 0, []

    # Caste
    scheme_caste = rules.get("caste", [])
    if scheme_caste:
        if profile.caste and profile.caste in scheme_caste:
            score += 3
            reasons.append(f"Category '{profile.caste.upper()}' eligible")
        elif profile.caste and profile.caste not in scheme_caste:
            return False, 0, []

    # Needs alignment — bonus points
    category_need_map = {
        "agriculture": ["farmer", "food"],
        "education":   ["education"],
        "housing":     ["housing"],
        "health":      ["health"],
        "employment":  ["employment"],
        "social_welfare": ["pension"],
        "pension":     ["pension"],
        "disability":  ["disability"],
        "women":       ["marriage"],
        "food":        ["food"],
        "business":    ["business_loan", "employment"],
        "skill":       ["employment"],
    }
    scheme_needs = category_need_map.get(scheme_category, [])
    for need in scheme_needs:
        if need in profile.needs:
            score += 2
            reasons.append(f"Matches your need for '{need}'")
            break

    # If we have meaningful profile info but no reasons yet, give 0 or 1 score
    has_meaningful_profile = any([
        profile.occupation, profile.marital_status, profile.caste,
        profile.location_type, profile.income_level is not None,
    ])
    if score == 0:
        if has_meaningful_profile:
            score = 1  # Low relevance but not filtered out
        else:
            score = 1  # Open national scheme
        if not reasons:
            reasons.append("National scheme open to all eligible citizens")

    return True, score, reasons


def match_schemes(profile: UserProfile, top_n: int = 10) -> List[SchemeMatch]:
    """
    Match user profile against all loaded schemes.
    Returns top-N eligible schemes sorted by match score (desc).
    """
    results = []

    for scheme in _SCHEMES:
        is_eligible, score, reasons = _check_eligibility(scheme, profile)
        if not is_eligible:
            continue

        reason_text = " • ".join(reasons) if reasons else "General eligibility"

        results.append(SchemeMatch(
            id=scheme["id"],
            name_en=scheme["name_en"],
            name_hi=scheme["name_hi"],
            category=scheme["category"],
            state=scheme.get("state", "ALL"),
            benefit_amount=scheme.get("benefit_amount"),
            benefit_description=scheme.get("benefit_description", ""),
            eligibility_reason=reason_text,
            match_score=score,
            required_documents=scheme.get("required_documents", []),
            how_to_apply=scheme.get("how_to_apply", ""),
            application_steps=scheme.get("application_steps", []),
            office_info=scheme.get("office_info", ""),
            website=scheme.get("website"),
        ))

    # Sort by score descending
    results.sort(key=lambda x: x.match_score, reverse=True)
    return results[:top_n]
