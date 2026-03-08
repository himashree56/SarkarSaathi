"""
SarkarSaathi — AWS Cognito Setup
Provisions User Pool and App Client for Authentication.
Run: python aws/auth_setup.py
"""
import json
import os
import boto3

# Load existing config
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
if not os.path.exists(CONFIG_FILE):
    print(f"❌ config.json not found. Run python aws/setup.py first.")
    exit(1)

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

REGION = config["region"]
cognito = boto3.client("cognito-idp", region_name=REGION)

def step(msg): print(f"\n🔐  {msg}")
def ok(msg):   print(f"   ✅ {msg}")

def setup_cognito():
    step("Creating Cognito User Pool: sarkarsaathi-users")
    try:
        resp = cognito.create_user_pool(
            PoolName="sarkarsaathi-users",
            Policies={
                "PasswordPolicy": {
                    "MinimumLength": 8,
                    "RequireUppercase": True,
                    "RequireLowercase": True,
                    "RequireNumbers": True,
                    "RequireSymbols": False
                }
            },
            AutoVerifiedAttributes=["email"],
            UsernameAttributes=["email"],
            MfaConfiguration="OFF"
        )
        pool_id = resp["UserPool"]["Id"]
        ok(f"User Pool created: {pool_id}")
    except Exception as e:
        if "already exists" in str(e).lower() or "ResourceInUseException" in str(e):
            # Find existing
            pools = cognito.list_user_pools(MaxResults=50)["UserPools"]
            pool_id = next(p["Id"] for p in pools if p["Name"] == "sarkarsaathi-users")
            ok(f"Using existing User Pool: {pool_id}")
        else:
            raise e

    step("Creating App Client")
    try:
        clients = cognito.list_user_pool_clients(UserPoolId=pool_id, MaxResults=50).get("UserPoolClients", [])
        existing = next((c for c in clients if c["ClientName"] == "sarkarsaathi-web-client"), None)
        
        if existing:
            client_id = existing["ClientId"]
            ok(f"Using existing Client: {client_id}")
        else:
            resp = cognito.create_user_pool_client(
                UserPoolId=pool_id,
                ClientName="sarkarsaathi-web-client",
                ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH", "ALLOW_USER_SRP_AUTH"],
                GenerateSecret=False
            )
            client_id = resp["UserPoolClient"]["ClientId"]
            ok(f"App Client created: {client_id}")
    except Exception as e:
        print(f"   ❌ Error creating client: {e}")
        raise e

    # Update config
    config["cognito_pool_id"] = pool_id
    config["cognito_client_id"] = client_id
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    ok("config.json updated with Cognito IDs")

if __name__ == "__main__":
    setup_cognito()
