# SarkarSaathi - Deploy React Frontend to S3 + CloudFront
# Run from project root: .\aws\deploy_frontend.ps1

$ErrorActionPreference = "Stop"

$REGION = "us-east-1"
$PYTHON = ".\venv\Scripts\python.exe"
$AWS = "$PYTHON -m awscli"
$BUCKET_NAME = "sarkarsaathi-frontend"

Write-Host "SarkarSaathi - Frontend Deployment"
Write-Host "================================================"

# Read API URL from config
if (-not (Test-Path "aws\config.json")) {
    Write-Host "No aws\config.json found. Run .\aws\deploy.ps1 first."
    exit 1
}
$config = Get-Content "aws\config.json" | ConvertFrom-Json
$API_URL = $config.api_url
Write-Host "API URL: $API_URL"

# Step 1: Build React app
Write-Host "[1] Building React app..."
Push-Location "frontend"
npm run build
Pop-Location
Write-Host "Build complete"

# Step 2: S3 setup
Write-Host "[2] Setting up S3 bucket..."
try {
    Invoke-Expression "$AWS s3api create-bucket --bucket $BUCKET_NAME --region $REGION" | Out-Null
}
catch {
    Write-Host "Bucket exists"
}

Invoke-Expression "$AWS s3 website s3://$BUCKET_NAME --index-document index.html --error-document index.html" | Out-Null

$policy_file = "aws\s3_policy.json"
@{
    Version   = "2012-10-17"
    Statement = @(@{
            Effect    = "Allow"
            Principal = "*"
            Action    = "s3:GetObject"
            Resource  = "arn:aws:s3:::$BUCKET_NAME/*"
        })
} | ConvertTo-Json -Depth 10 | Out-File $policy_file -Encoding utf8

Invoke-Expression "$AWS s3api put-public-access-block --bucket $BUCKET_NAME --public-access-block-configuration `"BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false`"" | Out-Null
Invoke-Expression "$AWS s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://$policy_file" | Out-Null
Remove-Item $policy_file
Write-Host "S3 Public Access Ready"

# Step 3: Upload files
Write-Host "[3] Uploading files..."
Invoke-Expression "$AWS s3 sync `"frontend/dist/`" `"s3://$BUCKET_NAME/`" --delete --region $REGION"
Write-Host "Upload complete"

# Step 4: CloudFront
Write-Host "[4] CloudFront Status..."
$existing_cf = Invoke-Expression "$AWS cloudfront list-distributions" | ConvertFrom-Json
$dist = $existing_cf.DistributionList.Items | Where-Object { $_.Origins.Items[0].DomainName -like "*$BUCKET_NAME*" }

if ($dist) {
    $CF_URL = "https://$($dist.DomainName)"
    Write-Host "CloudFront ready: $CF_URL"
    Write-Host "Invalidating CloudFront cache..."
    Invoke-Expression "$AWS cloudfront create-invalidation --distribution-id $($dist.Id) --paths `"/*`"" | Out-Null
    Write-Host "Cache invalidation requested."
}
else {
    Write-Host "CloudFront not found."
    $CF_URL = "N/A"
}

Write-Host "Done."
