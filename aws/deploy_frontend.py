"""
SarkarSaathi — Frontend Deployment Script
Builds React app and deploys to S3 + CloudFront.
Run: python aws/deploy_frontend.py
"""
import json
import os
import subprocess
import boto3
import time
import uuid

# Load config
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
if not os.path.exists(CONFIG_FILE):
    print(f"❌ config.json not found. Run python aws/setup.py first.")
    exit(1)

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

REGION      = config["region"]
BUCKET_NAME = "sarkarsaathi-frontend-ui"

s3 = boto3.client("s3", region_name=REGION)
cf = boto3.client("cloudfront", region_name=REGION)


def step(msg): print(f"\n[STEP] {msg}")
def ok(msg):   print(f"   OK: {msg}")
def err(msg):  print(f"   ERR: {msg}")


def build_react():
    step("Building React app")
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    env_prod = os.path.join(frontend_dir, ".env.production")
    if not os.path.exists(env_prod):
        err(".env.production missing! Run python aws/deploy.py first.")
        exit(1)
    
    try:
        subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True, shell=True)
        ok("Build complete (frontend/dist/)")
    except Exception as e:
        err(f"Build failed: {e}")
        exit(1)


def setup_s3():
    step("Setting up S3 bucket for hosting")
    try:
        if REGION == "us-east-1":
            s3.create_bucket(Bucket=BUCKET_NAME)
        else:
            s3.create_bucket(Bucket=BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": REGION})
        ok(f"Bucket created: {BUCKET_NAME}")
    except Exception:
        ok(f"Bucket already exists: {BUCKET_NAME}")

    s3.put_bucket_website(
        Bucket=BUCKET_NAME,
        WebsiteConfiguration={"IndexDocument": {"Suffix": "index.html"}, "ErrorDocument": {"Key": "index.html"}}
    )
    s3.put_public_access_block(
        Bucket=BUCKET_NAME,
        PublicAccessBlockConfiguration={"BlockPublicAcls": False, "IgnorePublicAcls": False, "BlockPublicPolicy": False, "RestrictPublicBuckets": False}
    )
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow", "Principal": "*", "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{BUCKET_NAME}/*"
        }]
    }
    s3.put_bucket_policy(Bucket=BUCKET_NAME, Policy=json.dumps(policy))
    ok("Public hosting configured")


def upload_to_s3():
    step("Uploading build to S3")
    dist_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
    import mimetypes
    count = 0
    for root, _, files in os.walk(dist_dir):
        for file in files:
            local_path = os.path.join(root, file)
            rel_path = os.path.relpath(local_path, dist_dir).replace("\\", "/")
            ctype, _ = mimetypes.guess_type(local_path)
            if not ctype: ctype = "application/octet-stream"
            s3.upload_file(local_path, BUCKET_NAME, rel_path, ExtraArgs={"ContentType": ctype})
            count += 1
    ok(f"Uploaded {count} files")


def setup_cloudfront():
    step("Setting up CloudFront")
    s3_website = f"{BUCKET_NAME}.s3-website-{REGION}.amazonaws.com"
    
    dists = cf.list_distributions().get("DistributionList", {}).get("Items", [])
    existing = next((d for d in dists if d["Origins"]["Items"][0]["DomainName"] == s3_website), None)
    
    if existing:
        cf_url = f"https://{existing['DomainName']}"
        ok(f"Existing CloudFront found: {cf_url}")
        return cf_url

    print(f"   Creating new CloudFront distribution for {s3_website}...")
    dist_config = {
        "CallerReference": str(uuid.uuid4()),
        "Comment": "SarkarSaathi React App",
        "Enabled": True,
        "DefaultRootObject": "index.html",
        "Origins": {
            "Quantity": 1,
            "Items": [{
                "Id": f"S3-{BUCKET_NAME}",
                "DomainName": s3_website,
                "CustomOriginConfig": {
                    "HTTPPort": 80,
                    "HTTPSPort": 443,
                    "OriginProtocolPolicy": "http-only"
                }
            }]
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": f"S3-{BUCKET_NAME}",
            "ViewerProtocolPolicy": "redirect-to-https",
            "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6" # CachingOptimized
        },
        "CustomErrorResponses": {
            "Quantity": 1,
            "Items": [{
                "ErrorCode": 404,
                "ResponseCode": "200",
                "ResponsePagePath": "/index.html"
            }]
        }
    }
    
    resp = cf.create_distribution(DistributionConfig=dist_config)
    cf_url = f"https://{resp['Distribution']['DomainName']}"
    ok(f"CloudFront created: {cf_url}")
    return cf_url


def invalidate_cloudfront(dist_id):
    step("Invalidating CloudFront cache")
    cf.create_invalidation(
        DistributionId=dist_id,
        InvalidationBatch={
            'Paths': {'Quantity': 1, 'Items': ['/*']},
            'CallerReference': str(int(time.time()))
        }
    )
    ok("Cache invalidation submitted — updates appear in ~1-3 min")


def main():
    print("\nSarkarSaathi -- Frontend Cloud Deployment")
    print("=" * 50)
    build_react()
    setup_s3()
    upload_to_s3()
    cf_url = setup_cloudfront()

    # Get distribution ID for invalidation
    distributions = cf.list_distributions()['DistributionList']['Items']
    dist = next((d for d in distributions if d['DomainName'] in cf_url), None)
    if dist:
        invalidate_cloudfront(dist['Id'])

    config["cloudfront_url"] = cf_url
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    print("\n---")
    print("DEPLOYMENT SUCCESSFUL!")
    print(f"   S3 Website: http://{BUCKET_NAME}.s3-website-{REGION}.amazonaws.com")
    print(f"   CloudFront: {cf_url}")
    print("   (CloudFront updates in ~1-3 minutes)")


if __name__ == "__main__":
    main()
