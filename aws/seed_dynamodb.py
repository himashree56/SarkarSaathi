"""
SarkarSaathi — DynamoDB Seeder
Loads backend/data/schemes.json → DynamoDB ss-schemes table
Run: python aws/seed_dynamodb.py
"""
import json
import boto3
import os
import sys
from decimal import Decimal

REGION     = "us-east-1"
TBL_SCHEMES = "ss-schemes"

SCHEMES_FILE = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "schemes.json")


def convert_floats(obj):
    """DynamoDB doesn't support Python floats — convert to Decimal."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats(i) for i in obj]
    return obj


def main():
    print("🏛️  SarkarSaathi — DynamoDB Seeder")
    print("=" * 50)

    if not os.path.exists(SCHEMES_FILE):
        print(f"❌ schemes.json not found at {SCHEMES_FILE}")
        print("   Run: python scrape_schemes.py first.")
        sys.exit(1)

    with open(SCHEMES_FILE, "r", encoding="utf-8") as f:
        schemes = json.load(f)
    print(f"✅ Loaded {len(schemes)} schemes from schemes.json")

    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table    = dynamodb.Table(TBL_SCHEMES)

    # Batch write (DynamoDB batch_writer handles chunking into 25-item batches)
    success = 0
    errors  = 0
    with table.batch_writer() as batch:
        for scheme in schemes:
            try:
                item = convert_floats(scheme)
                # Ensure id exists
                if not item.get("id"):
                    item["id"] = item.get("slug", "UNKNOWN")
                batch.put_item(Item=item)
                success += 1
                if success % 10 == 0:
                    print(f"   Seeded {success}/{len(schemes)}...")
            except Exception as e:
                print(f"   ⚠️  Error on {scheme.get('id', '?')}: {e}")
                errors += 1

    print(f"\n{'='*50}")
    print(f"✅ Seeded {success} schemes into DynamoDB '{TBL_SCHEMES}'")
    if errors:
        print(f"⚠️  {errors} errors — check output above")
    print("\nDone! The Lambda function will read from this table at runtime.")


if __name__ == "__main__":
    main()
