# 🏛️ SarkarSaathi: Deployment & Setup Guide

This guide details the steps to deploy the SarkarSaathi application to a production-ready AWS environment.

## 📋 Prerequisites

Before you begin, ensure you have the following installed and configured:

1.  **AWS CLI**: Configured with an IAM user that has `AdministratorAccess`.
2.  **Node.js & npm**: For building the React frontend.
3.  **Python 3.9+**: For local backend testing.
4.  **PowerShell**: Required for running the provided `.ps1` deployment scripts on Windows.

## ⚙️ Environment Variables

### Backend (`aws/lambda_function.py`)
Ensure the following variables are configured in your Lambda's environment:

- `REGION`: Your preferred AWS region (e.g., `us-east-1`).
- `BEDROCK_MODEL`: The ID for the Bedrock model (e.g., `anthropic.claude-3-haiku-20240307-v1:0`).
- `SESSIONS_TABLE`: Name of your DynamoDB table for session storage.
- `CACHE_TABLE`: Name of your DynamoDB table for response caching.
- `OPENROUTER_API_KEY`: (Optional) Your API key for OpenRouter fallbacks.

### Frontend (`frontend/.env.production`)
- `VITE_API_URL`: The URL of your deployed API Gateway endpoint.

## 🚀 Deployment Steps

### 1. Backend Deployment (Lambda & API Gateway)
Run the automated deployment script from the project root:

```powershell
.\aws\deploy.ps1
```

**What it does**:
- Packages the `lambda_function.py` into a ZIP archive.
- Uploads the ZIP to an AWS Lambda function named `sarkarsaathi-api`.
- Configures an HTTP API in API Gateway and points it to the Lambda.
- Automatically updates your `frontend/.env.production` with the new API URL.

### 2. Database Setup (DynamoDB)
Ensure you have created two DynamoDB tables with **Partition Key** `session_id` (string):
- `sessions_table`
- `cache_table`

### 3. Frontend Deployment (S3 & CloudFront)
Run the automated frontend deployment script from the project root:

```powershell
.\aws\deploy_frontend.ps1
```

**What it does**:
- Runs `npm run build` to generate the production React assets.
- Uploads the contents of the `dist/` directory to an S3 bucket named `sarkarsaathi-frontend`.
- Configures the S3 bucket for public static website hosting.
- Invalidates the CloudFront cache to ensure the latest version is live at your custom domain/URL.

## 🔍 Verification

1.  **Backend**: Test the health endpoint:
    ```bash
    curl https://<api-id>.execute-api.<region>.amazonaws.com/prod/health
    ```
2.  **Frontend**: Open your CloudFront URL in a browser and perform a **Hard Refresh (Ctrl+F5)** to clear any old cache.

## 🛠️ Local Development

To run the frontend locally:
```bash
cd frontend
npm install
npm run dev
```

The local development server will typically be available at `http://localhost:5173`. Ensure your `.env.local` points to a reachable API endpoint.

---
*Ready for the cloud!* 🚀🏛️✅
