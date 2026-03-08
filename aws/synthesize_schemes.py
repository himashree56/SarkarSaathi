"""
SarkarSaathi — Synthesize Schemes
Uses Bedrock Claude 3 to generate highly accurate JSON schemas
representing actual real-world schemes for specific ministries and states.
"""
import json
import boto3
import os
import time

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

REGION = config["region"]
BUCKET = config["data_bucket"]
KEY = config["schemes_key"]

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "data")
OUT_FILE = os.path.join(OUT_DIR, "schemes.json")

bedrock = boto3.client("bedrock-runtime", region_name=REGION)

CATEGORIES = [
    {
        "category": "women",
        "prompt": "List 10 major real-world government schemes related to Women & Child Welfare (including Widows support, Girl education incentives, Maternal health, Self-help groups). Focus on schemes from the Ministry of Women and Child Development and Karnataka State Government. Ensure realistic eligibility rules.",
        "state": "Karnataka"
    },
    {
        "category": "education",
        "prompt": "List 10 major real-world government schemes related to Education & Students (Scholarships for school/UG/PG, Skill development, Digital learning). Focus on Karnataka State schemes and Ministry of Skill Development.",
        "state": "Karnataka"
    },
    {
        "category": "agriculture",
        "prompt": "List 10 major real-world government schemes related to Farmers & Agriculture (Crop insurance, Subsidies for fertilizer/irrigation, Equipment financing, Solar pump schemes). Focus on Ministry of Agriculture and Karnataka Govt.",
        "state": "ALL"
    }
]

PROMPT_TEMPLATE = """You are an expert on Indian Government Schemes. 
{prompt}

Output them STRICTLY as a JSON list of objects matching this exact structure:
[
  {{
    "id": "UNIQUE_ID",
    "slug": "unique-slug",
    "name_en": "Scheme Name",
    "name_hi": "Scheme Name Hindi",
    "category": "{category}",
    "state": "{state}",  
    "benefit_amount": null or integer amount,
    "benefit_description": "Detailed description of financial or material benefits",
    "eligibility": {{
       "age_min": null or integer,
       "age_max": null or integer,
       "income_max": null or integer,
       "gender": null, "male", or "female",
       "location_type": null, "rural", or "urban",
       "caste": [] or list from ["sc","st","obc","general"],
       "marital_status": null or ["widowed"],
       "occupation": null or ["farmer", "student", "unemployed", "salaried", "self_employed", "daily_wage", "artisan", "fisherman"]
    }},
    "required_documents": ["Aadhaar", "Income Certificate"],
    "how_to_apply": "Brief instructions",
    "application_steps": ["Step 1", "Step 2"],
    "office_info": "Specific Ministry or Department Name",
    "website": "https://url-if-known-or-myscheme"
  }}
]

RULES:
- JSON only. No text before or after the JSON array.
- Create exactly 10 high-quality schemas.
"""

def generate_schemes():
    print("=" * 60)
    print("SarkarSaathi — Synthesizing State/Ministry Schemes")
    print("=" * 60)

    # 1. Load existing schemes
    with open(OUT_FILE, "r", encoding="utf-8") as f:
        existing_schemes = json.load(f)
    print(f"Loaded {len(existing_schemes)} existing schemes.")
    
    new_schemes = []

    for item in CATEGORIES:
        print(f"\\n--- Generating schemes for: {item['category']} ---")
        prompt = PROMPT_TEMPLATE.format(
            prompt=item["prompt"], category=item["category"], state=item["state"]
        )
        
        try:
            resp = bedrock.invoke_model(
                modelId="anthropic.claude-3-haiku-20240307-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096, "temperature": 0.2, # slightly higher for generation
                    "messages": [{"role": "user", "content": prompt}]
                }),
                contentType="application/json", accept="application/json",
            )
            raw_result = json.loads(resp["body"].read())["content"][0]["text"].strip()
            
            if "```" in raw_result:
                raw_result = raw_result.split("```")[1]
                if raw_result.startswith("json"): raw_result = raw_result[4:]
                
            schemes = json.loads(raw_result.strip())
            if isinstance(schemes, list):
                print(f"  > Generated {len(schemes)} schemes.")
                for s in schemes:
                    s["id"] = f"SYNTH_{s.get('slug', 'XX')}_{len(new_schemes)}"
                    new_schemes.append(s)
        except Exception as e:
            print(f"  [!] Bedrock generation error: {e}")
            
    if new_schemes:
        print(f"\\nMerging {len(new_schemes)} new schemes with {len(existing_schemes)} existing...")
        combined_schemes = existing_schemes + new_schemes
        
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            json.dump(combined_schemes, f, ensure_ascii=False, indent=2)
            
        print(f"Uploaded to local {OUT_FILE}")
        
        # Upload to S3
        s3 = boto3.client("s3", region_name=REGION)
        body = json.dumps(combined_schemes, ensure_ascii=False, indent=2)
        s3.put_object(Bucket=BUCKET, Key=KEY, Body=body.encode("utf-8"), ContentType="application/json")
        print(f"Uploaded to s3://{BUCKET}/{KEY}")
        
    print("✅ Done!")

if __name__ == "__main__":
    generate_schemes()
