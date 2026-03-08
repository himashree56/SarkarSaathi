"""
SarkarSaathi — Bedrock Profile Extractor
Uses Claude 3 Haiku to extract structured profile from user query.
Falls back to rule-based extractor if Bedrock fails/times out.
"""
import json
import boto3
import sys
import os

# Allow importing the rule-based extractor as fallback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from extractor import extract_profile as rule_based_extract

REGION      = "us-east-1"
MODEL_ID    = "anthropic.claude-3-haiku-20240307-v1:0"
MAX_TOKENS  = 400

bedrock = boto3.client("bedrock-runtime", region_name=REGION)

EXTRACTION_PROMPT = """You are a profile extractor for an Indian government scheme navigator.
Extract structured profile information from the user's query. The query may be in Hindi or English.

User query: {query}

Extract and return ONLY a valid JSON object with these fields (use null if not mentioned):
{{
  "age": <integer or null>,
  "gender": <"male"/"female"/null>,
  "marital_status": <"married"/"unmarried"/"widowed"/"divorced"/null>,
  "children": <integer or null>,
  "occupation": <"farmer"/"student"/"unemployed"/"salaried"/"self_employed"/"daily_wage"/"artisan"/"fisherman"/null>,
  "income_level": <annual income in INR as integer, or null>,
  "location_type": <"rural"/"urban"/"semi-urban"/null>,
  "state": <Indian state name in English or null>,
  "caste": <"sc"/"st"/"obc"/"general"/null>,
  "needs": <list of: "housing","education","health","food","employment","pension","marriage","disability","business_loan" — or empty list>
}}

Rules:
- विधवा = widowed female
- किसान/farmer = farmer occupation  
- बेरोजगार/unemployed = unemployed
- गांव/village/rural = rural location_type
- शहर/city/urban = urban location_type
- आमदनी/aamdani/income = income_level (convert lakhs: 1 lakh = 100000)
- Return ONLY the JSON, no explanation."""


def extract_with_bedrock(query: str) -> dict:
    """
    Call Claude 3 Haiku via Bedrock to extract profile.
    Returns a dict of profile fields.
    """
    prompt = EXTRACTION_PROMPT.format(query=query)
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,  # Low temperature for deterministic extraction
    }
    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(payload),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    text = result["content"][0]["text"].strip()

    # Parse JSON from response
    # Claude sometimes wraps in ```json ... ```
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def extract_profile_hybrid(query: str) -> dict:
    """
    Main entry point used by Lambda.
    1. Try Bedrock for rich extraction
    2. Merge with rule-based extraction (rules catch things Bedrock misses)
    3. Return merged profile dict
    """
    # Always run rule-based (fast, free)
    rule_profile = rule_based_extract(query)
    rule_dict = rule_profile.model_dump()

    # Try Bedrock
    bedrock_dict = {}
    try:
        bedrock_dict = extract_with_bedrock(query)
    except Exception as e:
        print(f"[bedrock_extractor] Bedrock failed, using rule-based only: {e}")

    # Merge: Bedrock fields take priority; rule-based fills gaps
    merged = {}
    fields = ["age", "gender", "marital_status", "children", "occupation",
              "income_level", "location_type", "state", "caste", "needs"]

    for field in fields:
        bedrock_val = bedrock_dict.get(field)
        rule_val    = rule_dict.get(field)

        if field == "needs":
            # Union of both lists
            b_needs = bedrock_val if isinstance(bedrock_val, list) else []
            r_needs = rule_val    if isinstance(rule_val,    list) else []
            merged[field] = list(set(b_needs) | set(r_needs))
        elif bedrock_val is not None and bedrock_val != "" and bedrock_val != []:
            merged[field] = bedrock_val
        elif rule_val is not None and rule_val != "" and rule_val != []:
            merged[field] = rule_val
        else:
            merged[field] = None

    # Language detection from rule-based (Bedrock doesn't need to know)
    merged["language"] = rule_dict.get("language", "en")

    return merged


if __name__ == "__main__":
    # Quick test
    test_queries = [
        "मैं 45 साल की विधवा हूं, गांव में रहती हूं, 2 बच्चे हैं",
        "I am a 19 year old SC student looking for scholarship, income 1.5 lakh",
    ]
    for q in test_queries:
        print(f"\nQuery: {q}")
        try:
            profile = extract_profile_hybrid(q)
            print(json.dumps(profile, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"Error: {e}")
