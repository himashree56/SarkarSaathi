"""
SarkarSaathi — Custom Portals Scraper (LLM-Assisted)
Attempts to fetch schemes from state portals and ministries.
Uses BeautifulSoup to strip UI/HTML, then Bedrock Claude 3 to extract schemes into JSON format.
"""
import requests
import json
import boto3
import time
import os
import re
from bs4 import BeautifulSoup

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

REGION = config["region"]
BUCKET = config["data_bucket"]
KEY = config["schemes_key"]

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "data")
OUT_FILE = os.path.join(OUT_DIR, "schemes.json")

bedrock = boto3.client("bedrock-runtime", region_name=REGION)

TARGET_URLS = [
    # Karnataka Portals
    ("Karnataka Seva Sindhu", "https://sevasindhu.karnataka.gov.in/Sevasindhu/DepartmentServices", "Karnataka"),
    ("Karnataka Gov", "https://www.karnataka.gov.in/english/services/schemes", "Karnataka"),
    # Ministries
    ("Min Women & Child", "https://wcd.nic.in/schemes", "ALL"),
    ("Min Agriculture", "https://agricoop.gov.in/en/schemes", "ALL"),
    ("Min Skill Development", "https://msde.gov.in/en/schemes-initiatives", "ALL"),
    ("Min Rural Development", "https://rural.nic.in/en/scheme-0", "ALL")
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

PROMPT_TEMPLATE = """You are a highly capable AI assistant that extracts Government Schemes structured data from messy scraped website text.
Below is the raw text extracted from a government website ({source_name}).

Extract any and all mentioned schemes and output them strictly as a JSON list of objects matching this exact structure:

[
  {{
    "id": "UNIQUE_ID_LIKE_WCD_001",
    "slug": "unique-slug",
    "name_en": "Scheme Name",
    "name_hi": "Scheme Name in Hindi (or just english name if unavailable)",
    "category": "One of: women, education, agriculture, employment, health, housing, pension, disability, business, energy",
    "state": "{state}",  
    "benefit_amount": null or integer amount,
    "benefit_description": "Detailed description of benefits",
    "eligibility": {{
       "age_min": null or integer,
       "age_max": null or integer,
       "income_max": null or integer,
       "gender": null, "male", or "female",
       "location_type": null, "rural", or "urban",
       "caste": [] or list from ["sc","st","obc","general"],
       "marital_status": ["widowed"] etc,
       "occupation": ["farmer", "student", "unemployed", "salaried", "self_employed", "daily_wage", "artisan", "fisherman"]
    }},
    "required_documents": ["Aadhaar", "Income Certificate", etc],
    "how_to_apply": "Brief instructions",
    "application_steps": ["Step 1", "Step 2"],
    "office_info": "{source_name} - Government Office",
    "website": "{url}"
  }}
]

RULES:
- ONLY output valid JSON. No conversational text.
- If no schemes are found, output an empty array: []
- Extract as many discrete schemes as you can identify from the text without exceeding max tokens.

Raw Scraped Text:
{text}
"""

def extract_schemes_from_text(text, source_name, source_url, state):
    if not text.strip(): return []
    
    # Chunk text if too huge (Claude Haiku has 200k context window, but output max is 4096)
    # So we limit input text to about 10000 characters to keep it focused
    chunks = [text[i:i+10000] for i in range(0, len(text), 10000)]
    all_schemes = []
    
    for chunk in chunks[:3]: # Limit to first 3 chunks to save time
        prompt = PROMPT_TEMPLATE.format(source_name=source_name, url=source_url, state=state, text=chunk)
        
        try:
            resp = bedrock.invoke_model(
                modelId="anthropic.claude-3-haiku-20240307-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096, "temperature": 0.1,
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
                all_schemes.extend(schemes)
        except Exception as e:
            print(f"  [!] Bedrock extraction error: {e}")
            break
            
    return all_schemes

def main():
    print("=" * 60)
    print("SarkarSaathi — LLM-Assisted Custom Scraper")
    print("=" * 60)

    # 1. Load existing schemes so we don't drop them
    with open(OUT_FILE, "r", encoding="utf-8") as f:
        existing_schemes = json.load(f)
    print(f"Loaded {len(existing_schemes)} existing schemes.")
    
    new_schemes = []

    for name, url, state in TARGET_URLS:
        print(f"\\n--- Scraping {name} ---")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "lxml")
                
                # Try to target main content area if available
                content_area = soup.find('main') or soup.find(id=re.compile("content", re.I)) or soup.find(class_=re.compile("content", re.I))
                if content_area:
                    text = content_area.get_text(separator=' ', strip=True)
                else:
                    text = soup.body.get_text(separator=' ', strip=True) if soup.body else soup.get_text(separator=' ', strip=True)
                
                print(f"  > Extracted {len(text)} characters of raw text.")
                
                if "captcha" in text.lower() or "cloudflare" in text.lower() or len(text) < 500:
                    print("  [!] Text implies Captcha/WAF block or too short. Skipping.")
                    continue
                    
                schemes = extract_schemes_from_text(text, name, url, state)
                print(f"  > Bedrock extracted {len(schemes)} schemes.")
                
                for s in schemes:
                    if s not in new_schemes:
                        # Add tracking ID
                        s["id"] = f"{name.replace(' ', '')}_{len(new_schemes)}".upper()
                        new_schemes.append(s)
            
            else:
                print(f"  [!] HTTP {resp.status_code}")
                
        except Exception as e:
            print(f"  [!] Failed to request: {e}")
            
        time.sleep(2) # Be polite
        
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
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()
