"""
SarkarSaathi — AWS Resource Setup Script
Creates all required AWS resources for the cloud deployment.
Run: python aws/setup.py

Prerequisites:
    pip install boto3
    aws configure  (with AdministratorAccess)
"""
import boto3
import json
import time
import sys

REGION         = "us-east-1"          # Bedrock available here
LAMBDA_ROLE    = "sarkarsaathi-lambda-role"
FUNCTION_NAME  = "sarkarsaathi-api"
API_NAME       = "sarkarsaathi-api-gw"
SECRET_NAME    = "sarkarsaathi/config"

# DynamoDB table names
TBL_SCHEMES  = "ss-schemes"
TBL_SESSIONS = "ss-sessions"
TBL_CACHE    = "ss-cache"

# S3 bucket for Lambda deployment ZIP
import random, string
LAMBDA_BUCKET = f"sarkarsaathi-lambda-{''.join(random.choices(string.ascii_lowercase + string.digits, k=6))}"

iam      = boto3.client("iam",      region_name=REGION)
dynamodb = boto3.client("dynamodb", region_name=REGION)
s3       = boto3.client("s3",       region_name=REGION)
lam      = boto3.client("lambda",   region_name=REGION)
apigw    = boto3.client("apigatewayv2", region_name=REGION)
sm       = boto3.client("secretsmanager", region_name=REGION)


def step(msg): print(f"\n{'='*50}\n▶  {msg}\n{'='*50}")
def ok(msg):   print(f"   ✅ {msg}")
def info(msg): print(f"   ℹ️  {msg}")


# ── 1. IAM Role ──────────────────────────────────────────────
def create_lambda_role() -> str:
    step("Creating IAM Role for Lambda")
    trust = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    })
    try:
        r = iam.create_role(RoleName=LAMBDA_ROLE, AssumeRolePolicyDocument=trust,
                            Description="SarkarSaathi Lambda execution role")
        role_arn = r["Role"]["Arn"]
        ok(f"Role created: {role_arn}")
    except iam.exceptions.EntityAlreadyExistsException:
        role_arn = iam.get_role(RoleName=LAMBDA_ROLE)["Role"]["Arn"]
        ok(f"Role already exists: {role_arn}")

    # Attach policies
    policies = [
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
        "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
        "arn:aws:iam::aws:policy/SecretsManagerReadWrite",
        "arn:aws:iam::aws:policy/AmazonCognitoReadOnly",
        "arn:aws:iam::aws:policy/AmazonPollyFullAccess",
        "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
    ]
    for p in policies:
        try:
            iam.attach_role_policy(RoleName=LAMBDA_ROLE, PolicyArn=p)
            ok(f"Attached: {p.split('/')[-1]}")
        except Exception as e:
            info(f"Policy attach: {e}")

    time.sleep(10)  # IAM propagation
    return role_arn


# ── 2. DynamoDB tables ────────────────────────────────────────
def create_dynamodb_tables():
    step("Creating DynamoDB Tables")

    tables = [
        {
            "TableName": TBL_SCHEMES,
            "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
        },
        {
            "TableName": TBL_SESSIONS,
            "KeySchema": [{"AttributeName": "session_id", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "session_id", "AttributeType": "S"}],
        },
        {
            "TableName": TBL_CACHE,
            "KeySchema": [{"AttributeName": "cache_key", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "cache_key", "AttributeType": "S"}],
        },
    ]

    for tbl in tables:
        name = tbl["TableName"]
        try:
            dynamodb.create_table(
                **tbl,
                BillingMode="PAY_PER_REQUEST",
            )
            ok(f"Created table: {name}")
            # Add TTL for sessions and cache
            if name in (TBL_SESSIONS, TBL_CACHE):
                waiter = boto3.client("dynamodb", region_name=REGION).get_waiter("table_exists")
                waiter.wait(TableName=name)
                dynamodb.update_time_to_live(
                    TableName=name,
                    TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"}
                )
                ok(f"  TTL enabled on '{name}'")
        except dynamodb.exceptions.ResourceInUseException:
            ok(f"Table already exists: {name}")


# ── 3. S3 Bucket (Lambda deployment) ─────────────────────────
def create_s3_bucket() -> str:
    step("Creating S3 Bucket for Lambda ZIP")
    try:
        if REGION == "us-east-1":
            s3.create_bucket(Bucket=LAMBDA_BUCKET)
        else:
            s3.create_bucket(Bucket=LAMBDA_BUCKET,
                             CreateBucketConfiguration={"LocationConstraint": REGION})
        s3.put_bucket_versioning(Bucket=LAMBDA_BUCKET,
                                 VersioningConfiguration={"Status": "Enabled"})
        ok(f"Bucket created: {LAMBDA_BUCKET}")
    except Exception as e:
        ok(f"Bucket issue (may already exist): {e}")
    return LAMBDA_BUCKET


# ── 4. Secrets Manager ────────────────────────────────────────
def create_secret():
    step("Creating Secrets Manager Secret")
    # Load existing config for Cognito IDs
    config_json = {}
    try:
        with open("aws/config.json", "r") as f:
            config_json = json.load(f)
    except: pass
    secret_value = json.dumps({
        "REGION": REGION,
        "DATA_BUCKET": LAMBDA_BUCKET,
        "SCHEMES_KEY": "data/schemes.json",
        "SESSIONS_TABLE": TBL_SESSIONS,
        "CACHE_TABLE": TBL_CACHE,
        "BEDROCK_MODEL": "anthropic.claude-3-haiku-20240307-v1:0",
        "COGNITO_POOL_ID": config_json.get("cognito_pool_id", ""),
        "COGNITO_CLIENT_ID": config_json.get("cognito_client_id", ""),
    })
    try:
        sm.create_secret(Name=SECRET_NAME, SecretString=secret_value,
                         Description="SarkarSaathi runtime config")
        ok(f"Secret created: {SECRET_NAME}")
    except sm.exceptions.ResourceExistsException:
        sm.update_secret(SecretId=SECRET_NAME, SecretString=secret_value)
        ok(f"Secret updated: {SECRET_NAME}")


# ── 5. Save config locally ────────────────────────────────────
def save_config(role_arn: str, bucket: str):
    step("Saving config to aws/config.json")
    config = {
        "region": REGION,
        "role_arn": role_arn,
        "lambda_bucket": bucket,
        "data_bucket": bucket,
        "schemes_key": "data/schemes.json",
        "lambda_function": FUNCTION_NAME,
        "api_name": API_NAME,
        "secret_name": SECRET_NAME,
        "tables": {
            "sessions": TBL_SESSIONS,
            "cache": TBL_CACHE,
        }
    }
    
    # Preserve Cognito IDs if they exist
    try:
        if os.path.exists("aws/config.json"):
            with open("aws/config.json", "r") as f:
                old = json.load(f)
                if old.get("cognito_pool_id"):
                    config["cognito_pool_id"] = old["cognito_pool_id"]
                if old.get("cognito_client_id"):
                    config["cognito_client_id"] = old["cognito_client_id"]
    except Exception as e: 
        print(f"   ⚠️  Could not merge existing config: {e}")

    with open("aws/config.json", "w") as f:
        json.dump(config, f, indent=2)
    ok("Saved to aws/config.json")


def main():
    print("\n🏛️  SarkarSaathi — AWS Setup")
    print("=" * 50)
    print(f"Region: {REGION}")

    # Verify credentials
    try:
        sts = boto3.client("sts", region_name=REGION)
        identity = sts.get_caller_identity()
        print(f"\n✅ AWS credentials valid!")
        print(f"   Account: {identity['Account']}")
        print(f"   ARN:     {identity['Arn']}")
    except Exception as e:
        print(f"\n❌ AWS credentials not configured: {e}")
        print("\nRun: aws configure")
        sys.exit(1)

    role_arn = create_lambda_role()
    create_dynamodb_tables()
    bucket   = create_s3_bucket()
    create_secret()
    save_config(role_arn, bucket)

    print(f"\n{'='*50}")
    print("✅ AWS setup complete!")
    print("\nNext steps:")
    print("  1. python aws/seed_dynamodb.py   ← load schemes into DynamoDB")
    print("  2. powershell aws/deploy.ps1     ← deploy Lambda + API Gateway")
    print("  3. powershell aws/deploy_frontend.ps1  ← deploy React to S3")


if __name__ == "__main__":
    main()
