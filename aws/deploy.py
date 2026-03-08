"""
SarkarSaathi — Python Deployment Script
Packages and deploys Lambda + API Gateway using Boto3.
Run: python aws/deploy.py
"""
import json
import os
import zipfile
import boto3
import time
import io

# Load config
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
if not os.path.exists(CONFIG_FILE):
    print(f"❌ config.json not found. Run python aws/setup.py first.")
    exit(1)

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

REGION         = config["region"]
ROLE_ARN       = config["role_arn"]
FUNCTION_NAME  = config["lambda_function"]
API_NAME       = config["api_name"]
SECRET_NAME    = config["secret_name"]

lam   = boto3.client("lambda", region_name=REGION)
apigw = boto3.client("apigatewayv2", region_name=REGION)
sm    = boto3.client("secretsmanager", region_name=REGION)
sts   = boto3.client("sts", region_name=REGION)


def step(msg): print(f"\n🏛️  {msg}")
def ok(msg):   print(f"   ✅ {msg}")
def err(msg):  print(f"   ❌ {msg}")


def package_lambda():
    step("Packaging Lambda ZIP")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        # Add lambda_function.py
        lfunc = os.path.join(os.path.dirname(__file__), "lambda_function.py")
        zip_file.write(lfunc, "lambda_function.py")
        
        # Add schemes.json as fallback
        schemes = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "schemes.json")
        if os.path.exists(schemes):
            zip_file.write(schemes, "schemes.json")
            ok("Added schemes.json fallback to ZIP")
            
    ok(f"ZIP created in memory ({len(zip_buffer.getvalue()) / 1024:.1f} KB)")
    return zip_buffer.getvalue()


def deploy_lambda(zip_bytes):
    step("Deploying Lambda Function")
    
    env_vars = {
        "REGION": REGION,
        "DATA_BUCKET": config["data_bucket"],
        "SCHEMES_KEY": config["schemes_key"],
        "SESSIONS_TABLE": config["tables"]["sessions"],
        "CACHE_TABLE": config["tables"]["cache"],
        "BEDROCK_MODEL": "anthropic.claude-3-haiku-20240307-v1:0"
    }

    def update_with_retry(func, **kwargs):
        for i in range(15):
            try:
                return func(**kwargs)
            except lam.exceptions.ResourceConflictException:
                print(f"   ⏳ Resource conflict, retrying {i+1}/15...")
                time.sleep(15)
        raise Exception("Failed after retries due to ResourceConflict")

    try:
        # Try update
        update_with_retry(lam.update_function_code, FunctionName=FUNCTION_NAME, ZipFile=zip_bytes)
        update_with_retry(lam.update_function_configuration, 
            FunctionName=FUNCTION_NAME,
            Timeout=30, MemorySize=512,
            Environment={"Variables": env_vars}
        )
        ok(f"Lambda updated: {FUNCTION_NAME}")
    except lam.exceptions.ResourceNotFoundException:
        # Create new
        print(f"   Creating new function: {FUNCTION_NAME}...")
        lam.create_function(
            FunctionName=FUNCTION_NAME,
            Runtime="python3.12",
            Role=ROLE_ARN,
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": zip_bytes},
            Timeout=30, MemorySize=512,
            Environment={"Variables": env_vars}
        )
        ok(f"Lambda created: {FUNCTION_NAME}")

    # Wait for update
    print("   Waiting for Lambda state to be Active...")
    for _ in range(30):
        resp = lam.get_function_configuration(FunctionName=FUNCTION_NAME)
        if resp.get("State") == "Active" and resp.get("LastUpdateStatus") != "InProgress":
            ok("Lambda is Active")
            break
        time.sleep(5)


def setup_api_gateway():
    step("Setting up API Gateway")
    
    # Check if exists
    apis = apigw.get_apis()["Items"]
    existing = next((a for a in apis if a["Name"] == API_NAME), None)
    
    if existing:
        api_id = existing["ApiId"]
        ok(f"Existing API found: {api_id}")
    else:
        # Create new HTTP API
        resp = apigw.create_api(
            Name=API_NAME,
            ProtocolType="HTTP",
            CorsConfiguration={
                "AllowOrigins": ["*"],
                "AllowMethods": ["GET", "POST", "OPTIONS"],
                "AllowHeaders": ["Content-Type"]
            }
        )
        api_id = resp["ApiId"]
        ok(f"Created API: {api_id}")

        # Get Lambda ARN
        lambda_arn = lam.get_function(FunctionName=FUNCTION_NAME)["Configuration"]["FunctionArn"]

        # Create integration
        integ = apigw.create_integration(
            ApiId=api_id,
            IntegrationType="AWS_PROXY",
            IntegrationUri=lambda_arn,
            PayloadFormatVersion="2.0"
        )
        integ_id = integ["IntegrationId"]

        # Create $default route
        apigw.create_route(
            ApiId=api_id,
            RouteKey="$default",
            Target=f"integrations/{integ_id}"
        )

        # Create stage
        apigw.create_stage(ApiId=api_id, StageName="prod", AutoDeploy=True)

        # Add Lambda permission
        account_id = sts.get_caller_identity()["Account"]
        lam.add_permission(
            FunctionName=FUNCTION_NAME,
            StatementId=f"apigw-{int(time.time())}",
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=f"arn:aws:execute-api:{REGION}:{account_id}:{api_id}/*"
        )
        ok("API Gateway integration and permissions set")

    api_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/prod"
    return api_url


def main():
    print("\n🚀 SarkarSaathi — Cloud Deployment")
    print("=" * 50)
    
    zip_bytes = package_lambda()
    deploy_lambda(zip_bytes)
    api_url = setup_api_gateway()
    
    # Save to config and frontend .env
    config["api_url"] = api_url
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    
    env_file = os.path.join(os.path.dirname(__file__), "..", "frontend", ".env.production")
    with open(env_file, "w") as f:
        f.write(f"VITE_API_URL={api_url}\n")
        f.write(f"VITE_COGNITO_POOL_ID={config.get('cognito_pool_id', '')}\n")
        f.write(f"VITE_COGNITO_CLIENT_ID={config.get('cognito_client_id', '')}\n")
        f.write(f"VITE_REGION={REGION}\n")
    
    ok(f"Frontend .env.production updated with API and Cognito IDs")
    
    print(f"\n{'='*50}")
    print(f"✅ DEPLOYMENT SUCCESSFUL!")
    print(f"   API URL: {api_url}")
    print(f"   Test:    curl {api_url}/health")
    print("\nNext: python aws/deploy_frontend.py")


if __name__ == "__main__":
    main()
