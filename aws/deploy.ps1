# SarkarSaathi — Deploy Lambda + API Gateway
# Run from project root: .\aws\deploy.ps1
# Prerequisites: aws configure, python aws/setup.py already run

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$REGION = "us-east-1"
$PYTHON = ".\venv\Scripts\python.exe"
$AWS = "$PYTHON -m awscli"
$FUNCTION_NAME = "sarkarsaathi-api"
$ZIP_FILE = "aws\lambda_deploy.zip"

# Load config
$config = Get-Content "aws\config.json" | ConvertFrom-Json
$ROLE_ARN = $config.role_arn
$API_NAME = $config.api_name

Write-Host "`n🏛️  SarkarSaathi — Lambda Deployment" -ForegroundColor Cyan
Write-Host "=" * 50

# ── Step 1: Package Lambda ZIP ─────────────────────────────────
Write-Host "`n[1] Packaging Lambda ZIP..." -ForegroundColor Yellow

# Remove old ZIP
if (Test-Path $ZIP_FILE) { Remove-Item $ZIP_FILE }

# Create temp dir for packaging
$TMP = "aws\_lambda_pkg"
if (Test-Path $TMP) { Remove-Item $TMP -Recurse -Force }
New-Item -ItemType Directory -Path $TMP | Out-Null

# Copy Lambda function and schemes fallback
Copy-Item "aws\lambda_function.py" "$TMP\lambda_function.py"
# We also copy the schemes.json as a local fallback for the Lambda
Copy-Item "backend\data\schemes.json" "$TMP\schemes.json"

# ZIP it
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    (Resolve-Path $TMP).Path,
    (Join-Path (Get-Location) $ZIP_FILE)
)
Remove-Item $TMP -Recurse -Force

$zipSize = [math]::Round((Get-Item $ZIP_FILE).Length / 1KB, 1)
Write-Host "   ✅ ZIP created: $ZIP_FILE ($zipSize KB)"

# ── Step 2: Create or Update Lambda ───────────────────────────
Write-Host "`n[2] Deploying Lambda function..." -ForegroundColor Yellow

$configProps = @{
    REGION             = $REGION
    DATA_BUCKET        = $config.data_bucket
    SCHEMES_KEY        = $config.schemes_key
    SESSIONS_TABLE     = $config.tables.sessions
    CACHE_TABLE        = $config.tables.cache
    BEDROCK_MODEL      = "anthropic.claude-3-haiku-20240307-v1:0"
    NOVA_MODEL_ID      = "amazon.nova-micro-v1:0"
    NOVA_MAX_TOKENS    = "512"
    OPENROUTER_API_KEY = (Get-Content "aws\openrouter_key.txt").Trim()
    OPENROUTER_MODEL   = "meta-llama/llama-3.2-3b-instruct:free"
}

try {
    Write-Host "   Updating Lambda code..."
    & .\venv\Scripts\python.exe -m awscli lambda update-function-code --function-name $FUNCTION_NAME --zip-file "fileb://$ZIP_FILE" --region $REGION | Out-Null

    Write-Host "   Updating Lambda configuration and environment variables..."
    # Robust deployment: write env to temp file to avoid PowerShell quoting hell
    $envFile = "aws\_tmp_env.json"
    $configJson = @{ Variables = $configProps } | ConvertTo-Json
    $configJson | Set-Content $envFile
    
    & .\venv\Scripts\python.exe -m awscli lambda update-function-configuration --function-name $FUNCTION_NAME --timeout 60 --memory-size 1024 --environment "file://$envFile" --region $REGION | Out-Null
    
    Remove-Item $envFile
    Write-Host "   ✅ Lambda updated: $FUNCTION_NAME"
}
catch {
    Write-Host "   Creating new Lambda function..."
    $envFile = "aws\_tmp_env.json"
    $configJson = @{ Variables = $configProps } | ConvertTo-Json
    $configJson | Set-Content $envFile
    & .\venv\Scripts\python.exe -m awscli lambda create-function --function-name $FUNCTION_NAME --runtime python3.12 --role $ROLE_ARN --handler lambda_function.lambda_handler --zip-file "fileb://$ZIP_FILE" --timeout 60 --memory-size 1024 --environment "file://$envFile" --region $REGION --no-cli-pager | Out-Null
    Remove-Item $envFile
    Write-Host "   ✅ Lambda created: $FUNCTION_NAME"
}

# Wait for update to complete
Write-Host "   Waiting for Lambda to be ready..."
& .\venv\Scripts\python.exe -m awscli lambda wait function-updated --function-name $FUNCTION_NAME --region $REGION

# ── Step 3: Create or get API Gateway ─────────────────────────
Write-Host "`n[3] Setting up API Gateway (HTTP API)..." -ForegroundColor Yellow

# Check if API already exists
$apis = Invoke-Expression "$AWS apigatewayv2 get-apis --region $REGION" | ConvertFrom-Json
$existing = $apis.Items | Where-Object { $_.Name -eq $API_NAME }

if ($existing) {
    $API_ID = $existing.ApiId
    Write-Host "   ✅ Existing API: $API_ID"
}
else {
    # Get Lambda ARN
    $lambdaArn = (Invoke-Expression "$AWS lambda get-function --function-name $FUNCTION_NAME --region $REGION" | ConvertFrom-Json).Configuration.FunctionArn

    # Create HTTP API with Lambda integration
    $api = Invoke-Expression "$AWS apigatewayv2 create-api --name $API_NAME --protocol-type HTTP --cors-configuration `"AllowOrigins=*,AllowMethods=GET POST PUT DELETE OPTIONS,AllowHeaders=Content-Type Authorization`" --region $REGION" | ConvertFrom-Json
    $API_ID = $api.ApiId

    # Create integration
    $integration = Invoke-Expression "$AWS apigatewayv2 create-integration --api-id $API_ID --integration-type AWS_PROXY --integration-uri $lambdaArn --payload-format-version `"2.0`" --region $REGION" | ConvertFrom-Json

    # Create catch-all route
    Invoke-Expression "$AWS apigatewayv2 create-route --api-id $API_ID --route-key `'$default`' --target `"integrations/$($integration.IntegrationId)`" --region $REGION" | Out-Null

    # Deploy to 'prod' stage
    Invoke-Expression "$AWS apigatewayv2 create-stage --api-id $API_ID --stage-name prod --auto-deploy --region $REGION" | Out-Null

    # Add Lambda permission for API GW
    $ACCOUNT_ID = (Invoke-Expression "$AWS sts get-caller-identity" | ConvertFrom-Json).Account
    Invoke-Expression "$AWS lambda add-permission --function-name $FUNCTION_NAME --statement-id apigateway-invoke --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn `"arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*`" --region $REGION" | Out-Null

    Write-Host "   ✅ API Gateway created: $API_ID"
}

$API_URL = "https://$API_ID.execute-api.$REGION.amazonaws.com/prod"

# ── Step 4: Save API URL ───────────────────────────────────────
$config | Add-Member -NotePropertyName "api_url" -NotePropertyValue $API_URL -Force
$config | ConvertTo-Json | Set-Content "aws\config.json"

# Update frontend .env.production
$envContent = "VITE_API_URL=$API_URL"
Set-Content "frontend\.env.production" $envContent
Write-Host "`n   ✅ Frontend .env.production updated with API URL"

# ── Done ───────────────────────────────────────────────────────
Write-Host "`n$('='*50)" -ForegroundColor Green
Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "   API URL: $API_URL" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test:"
Write-Host "   curl $API_URL/health"
Write-Host ""
Write-Host "Next: .\aws\deploy_frontend.ps1"
