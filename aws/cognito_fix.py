"""
Find and fix Cognito User Pool — restore IDs, enable USER_PASSWORD_AUTH, update config.json and .env files.
"""
import boto3
import json
import os

REGION = "us-east-1"
POOL_NAME = "sarkarsaathi-users"
CLIENT_NAME = "sarkarsaathi-web-client"

cog = boto3.client("cognito-idp", region_name=REGION)

# 1. Find pool
print("🔍 Searching for user pool...")
pools = cog.list_user_pools(MaxResults=20)["UserPools"]
pool = next((p for p in pools if POOL_NAME in p["Name"]), None)

if pool:
    pool_id = pool["Id"]
    print(f"   ✅ Found pool: {pool_id} ({pool['Name']})")
else:
    print(f"   ❌ No pool named '{POOL_NAME}' found. Creating...")
    resp = cog.create_user_pool(
        PoolName=POOL_NAME,
        AutoVerifiedAttributes=["email"],
        UsernameAttributes=["email"],
    )
    pool_id = resp["UserPool"]["Id"]
    print(f"   ✅ Created pool: {pool_id}")

# 2. Find or create app client
print("\n🔍 Searching for app client...")
clients = cog.list_user_pool_clients(UserPoolId=pool_id, MaxResults=20)["UserPoolClients"]
client = next((c for c in clients if CLIENT_NAME in c["ClientName"]), None)

if client:
    client_id = client["ClientId"]
    print(f"   ✅ Found client: {client_id}")
else:
    print(f"   Creating new client with USER_PASSWORD_AUTH...")
    resp = cog.create_user_pool_client(
        UserPoolId=pool_id,
        ClientName=CLIENT_NAME,
        GenerateSecret=False,
        ExplicitAuthFlows=[
            "ALLOW_USER_PASSWORD_AUTH",
            "ALLOW_REFRESH_TOKEN_AUTH",
            "ALLOW_USER_SRP_AUTH",
        ],
    )
    client_id = resp["UserPoolClient"]["ClientId"]
    print(f"   ✅ Created client: {client_id}")

# 3. Always ensure USER_PASSWORD_AUTH is enabled
print("\n⚙️  Enabling USER_PASSWORD_AUTH flow...")
cog.update_user_pool_client(
    UserPoolId=pool_id,
    ClientId=client_id,
    ExplicitAuthFlows=[
        "ALLOW_USER_PASSWORD_AUTH",
        "ALLOW_REFRESH_TOKEN_AUTH",
        "ALLOW_USER_SRP_AUTH",
    ],
)
print("   ✅ Auth flows updated")

# 4. Update config.json
config_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(config_path, "r") as f:
    config = json.load(f)

config["cognito_pool_id"] = pool_id
config["cognito_client_id"] = client_id

with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
print(f"\n   ✅ config.json updated")

# 5. Update .env files
env_prod = os.path.join(os.path.dirname(__file__), "..", "frontend", ".env.production")
env_dev  = os.path.join(os.path.dirname(__file__), "..", "frontend", ".env")
api_url  = config.get("api_url", "https://l83kehcc99.execute-api.us-east-1.amazonaws.com/prod")

for env_path in [env_prod, env_dev]:
    local_url = "http://localhost:8000" if env_path == env_dev else api_url
    with open(env_path, "w") as f:
        f.write(f"VITE_API_URL={local_url if '.env.production' not in env_path else api_url}\n")
        f.write(f"VITE_COGNITO_POOL_ID={pool_id}\n")
        f.write(f"VITE_COGNITO_CLIENT_ID={client_id}\n")
        f.write(f"VITE_REGION={REGION}\n")
    print(f"   ✅ {os.path.basename(env_path)} updated")

print(f"\n{'='*50}")
print(f"Pool ID  : {pool_id}")
print(f"Client ID: {client_id}")
print(f"{'='*50}")
print("\n✅ Done! Now rebuild with: python aws/deploy_frontend.py")
