"""
SarkarSaathi — S3 Data Seeder
Uploads backend/data/schemes.json → S3 data bucket
Run: python aws/seed_s3.py
"""
import json
import boto3
import os
import sys

# Load config
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
if not os.path.exists(CONFIG_FILE):
    print(f"❌ config.json not found at {CONFIG_FILE}. Run python aws/setup.py first.")
    sys.exit(1)

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

REGION      = config["region"]
BUCKET      = config["data_bucket"]
KEY         = config["schemes_key"]

SCHEMES_FILE = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "schemes.json")


def main():
    print("🏛️  SarkarSaathi — S3 Data Seeder")
    print("=" * 50)

    if not os.path.exists(SCHEMES_FILE):
        print(f"❌ schemes.json not found at {SCHEMES_FILE}")
        print("   Run: python scrape_schemes.py first.")
        sys.exit(1)

    print(f"✅ Found schemes.json")
    
    s3 = boto3.client("s3", region_name=REGION)
    
    print(f"   Uploading to s3://{BUCKET}/{KEY}...")
    try:
        s3.upload_file(SCHEMES_FILE, BUCKET, KEY)
        print(f"\n{'='*50}")
        print(f"✅ Uploaded schemes.json to S3!")
    except Exception as e:
        print(f"❌ Error uploading: {e}")
        sys.exit(1)

    print("\nDone! The Lambda function will read from this S3 object at runtime.")


if __name__ == "__main__":
    main()
