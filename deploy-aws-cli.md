# 💻 AWS Serverless Deployment — CLI Guide
## Cowell OCR MVP

> **Target audience:** Users comfortable with the command line (Git Bash / Terminal).
> **Everything done via `aws` CLI commands.** Faster than the Console method.
> **Estimated cost:** **Less than $1/month** for low usage.

---

## Table of Contents

- [0. Architecture Overview](#0-architecture-overview)
- [1. Prerequisites](#1-prerequisites)
- [2. Set Up Environment Variables](#2-set-up-environment-variables)
- [3. Create S3 Buckets](#3-create-s3-buckets)
- [4. Upload OAuth Token](#4-upload-oauth-token)
- [5. Build and Deploy Lambda](#5-build-and-deploy-lambda)
- [6. Create and Deploy API Gateway](#6-create-and-deploy-api-gateway)
- [7. Deploy Frontend to S3](#7-deploy-frontend-to-s3)
- [8. Set Up CloudFront](#8-set-up-cloudfront)
- [9. Final Steps](#9-final-steps)
- [10. Cost Breakdown](#10-cost-breakdown)
- [11. Cleanup](#11-cleanup)
- [12. Troubleshooting](#12-troubleshooting)

---

## 0. Architecture Overview

```
                    ┌─────────────────────────────────────────────┐
                    │         CloudFront CDN                      │
                    └──────────┬──────────────────────┬───────────┘
                               │                      │
                    ┌──────────▼──────┐    ┌──────────▼───────────┐
                    │   S3 Bucket     │    │   API Gateway        │
                    │ (static files)  │    │   (REST API)         │
                    └─────────────────┘    └──────────┬───────────┘
                                                      │
                                               ┌──────▼───────┐
                                               │   Lambda     │
                                               │  (FastAPI)   │
                                               └──────┬───────┘
                                                  │       │
                                        ┌─────────▼──┐ ┌──▼──────────┐
                                        │ S3 Bucket  │ │ S3 Bucket   │
                                        │ (sessions) │ │ (uploads)   │
                                        └────────────┘ └─────────────┘
```

**Services we use:** Lambda, API Gateway, S3 × 4, CloudFront, CloudWatch, IAM.

---

## 1. Prerequisites

### 1.1 — Install the AWS CLI

**Windows:** Download and run [AWSCLIV2.msi](https://awscli.amazonaws.com/AWSCLIV2.msi)
**macOS:** `brew install awscli`
**Linux:** `sudo apt install awscli -y`

Verify:
```bash
aws --version
# Should show: aws-cli/2.x.x ...
```

### 1.2 — Create an AWS Account

Go to [https://aws.amazon.com/free/](https://aws.amazon.com/free/) → **"Create a Free Account"**.

> ⚠️ AWS asks for a credit card. Everything in this guide stays within the Free Tier for 12 months.

### 1.3 — Create an IAM User and Get Access Keys

1. Log into [AWS Console](https://console.aws.amazon.com/)
2. Search for **"IAM"** → **Users** → **"Create user"**
3. Name: `cowell-deployer`
4. **"Attach policies directly"** → Search for **"AdministratorAccess"** → Check it → **Next** → **"Create user"**
5. Click the user → **"Security credentials"** tab → **"Create access key"**
6. **"Command Line Interface (CLI)"** → Check confirmation → **Next** → **"Create access key"**
7. **Download the .csv file** (this is the only time you can see the secret key!)

### 1.4 — Configure AWS CLI

```bash
aws configure
```

You'll be prompted:

```
AWS Access Key ID [None]: PASTE_FROM_CSV
AWS Secret Access Key [None]: PASTE_FROM_CSV
Default region name [None]: ap-northeast-1
Default output format [None]: json
```

> 💡 Pick the region closest to you:
> - `ap-northeast-1` (Tokyo) — closest to Japan
> - `us-east-1` (N. Virginia) — cheapest
> - `eu-west-1` (Ireland) — closest to Europe

Verify:
```bash
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AIDA...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/cowell-deployer"
}
```

### 1.5 — Install Python Dependencies

```bash
cd backend
pip install mangum boto3
```

Or if using `uv`:
```bash
cd backend
uv add mangum boto3
```

### 1.6 — Build the Frontend

```bash
cd frontend
npm install
npm run build
```

✅ Creates `frontend/dist/` folder.

---

## 2. Set Up Environment Variables

Set these variables in your terminal. They'll be used throughout the deployment.

### 2.1 — Edit These Values First

Change these to match your project:

```bash
# ── EDIT THESE ─────────────────────────────────────
export BUCKET_SUFFIX="john1985-123"     # Unique string for bucket names
export REGION="ap-northeast-1"          # Your AWS region
export GEMINI_API_KEY="AIzaSy..."       # Your Google Gemini API key
export GOOGLE_TARGET_FOLDER_ID=""       # Optional: Google Drive folder ID
# ─────────────────────────────────────────────────
```

### 2.2 — Export Derived Values

```bash
# ── Bucket names ──────────────────────────────────
export BUCKET_UPLOADS="cowell-uploads-$BUCKET_SUFFIX"
export BUCKET_SESSIONS="cowell-sessions-$BUCKET_SUFFIX"
export BUCKET_TOKEN="cowell-token-$BUCKET_SUFFIX"
export BUCKET_FRONTEND="cowell-frontend-$BUCKET_SUFFIX"

# ── Lambda function name ─────────────────────────
export LAMBDA_FN="cowell-ocr-backend"
```

---

## 3. Create S3 Buckets

```bash
echo "▶ Creating S3 buckets..."

# Helper function
create_bucket() {
  local name="$1"
  if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$name" --region "$REGION"
  else
    aws s3api create-bucket --bucket "$name" --region "$REGION" \
      --create-bucket-configuration LocationConstraint="$REGION"
  fi
  echo "  ✓ $name"
}

create_bucket "$BUCKET_UPLOADS"
create_bucket "$BUCKET_SESSIONS"
create_bucket "$BUCKET_TOKEN"
create_bucket "$BUCKET_FRONTEND"

echo "✅ All 4 buckets created"
```

---

## 4. Upload OAuth Token

```bash
echo "▶ Uploading OAuth token..."
aws s3 cp backend/credentials/token.json \
  "s3://$BUCKET_TOKEN/credentials/token.json"
echo "✅ Token uploaded to s3://$BUCKET_TOKEN/credentials/token.json"
```

> If `token.json` doesn't exist, generate it:
> ```bash
> cd backend
> python auth_oauth.py
> ```

---

## 5. Build and Deploy Lambda

### 5.1 — Create the Lambda Execution Role

First, create an IAM role that Lambda uses to access S3 and write logs.

```bash
echo "▶ Creating IAM role for Lambda..."

# Create the trust policy document
cat > /tmp/lambda-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name "$LAMBDA_FN-role" \
  --assume-role-policy-document file:///tmp/lambda-trust-policy.json

# Attach basic Lambda execution policy (CloudWatch logs)
aws iam attach-role-policy \
  --role-name "$LAMBDA_FN-role" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create and attach S3 access policy
cat > /tmp/s3-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::$BUCKET_UPLOADS",
        "arn:aws:s3:::$BUCKET_UPLOADS/*",
        "arn:aws:s3:::$BUCKET_SESSIONS",
        "arn:aws:s3:::$BUCKET_SESSIONS/*",
        "arn:aws:s3:::$BUCKET_TOKEN",
        "arn:aws:s3:::$BUCKET_TOKEN/*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name "$LAMBDA_FN-role" \
  --policy-name "s3-access" \
  --policy-document file:///tmp/s3-policy.json

# Wait for role to propagate
sleep 5

# Get the role ARN
ROLE_ARN=$(aws iam get-role --role-name "$LAMBDA_FN-role" --query 'Role.Arn' --output text)
echo "✅ Role created: $ROLE_ARN"
```

### 5.2 — Build the Deployment ZIP

```bash
echo "▶ Building Lambda deployment package..."

cd backend

# Create temp directory
mkdir -p build_temp

# Install all dependencies (use --platform for Linux-compatible binaries)
pip install -t build_temp/ \
  mangum boto3 fastapi uvicorn python-multipart google-genai gspread \
  google-auth google-auth-oauthlib google-api-python-client \
  pypdfium2 Pillow pydantic-settings httpx python-dotenv \
  --platform manylinux2014_x86_64 --only-binary=:all: 2>/dev/null || \
pip install -t build_temp/ \
  mangum boto3 fastapi uvicorn python-multipart google-genai gspread \
  google-auth google-auth-oauthlib google-api-python-client \
  pypdfium2 Pillow pydantic-settings httpx python-dotenv

# Copy app code
cp -r app build_temp/app
cp lambda_handler.py build_temp/

# Clean up unnecessary files
find build_temp -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find build_temp -name "*.pyc" -delete
rm -rf build_temp/*.dist-info build_temp/bin build_temp/*.whl 2>/dev/null || true

# Create ZIP
cd build_temp
zip -rq ../cowell-lambda.zip .
cd ..
rm -rf build_temp

echo "✅ Created: cowell-lambda.zip ($(du -h cowell-lambda.zip | cut -f1))"
```

### 5.3 — Create the Lambda Function

```bash
echo "▶ Creating Lambda function..."

# Get the account ID for resource ARN
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)

aws lambda create-function \
  --function-name "$LAMBDA_FN" \
  --runtime "python3.12" \
  --role "$ROLE_ARN" \
  --handler "lambda_handler.handler" \
  --zip-file fileb://cowell-lambda.zip \
  --memory-size 512 \
  --timeout 300 \
  --environment "Variables={
    GEMINI_API_KEY=$GEMINI_API_KEY,
    S3_BUCKET_UPLOADS=$BUCKET_UPLOADS,
    S3_BUCKET_SESSIONS=$BUCKET_SESSIONS,
    S3_BUCKET_TOKEN=$BUCKET_TOKEN,
    S3_TOKEN_KEY=credentials/token.json,
    GOOGLE_OAUTH_TARGET_FOLDER_ID=$GOOGLE_TARGET_FOLDER_ID
  }" \
  --region "$REGION"

echo "✅ Lambda function '$LAMBDA_FN' created"
```

### 5.4 — Update Lambda Code (After Changes)

Whenever you change the code:

```bash
cd backend
# Rebuild ZIP
mkdir -p build_temp
pip install -t build_temp/ mangum boto3 fastapi uvicorn python-multipart google-genai gspread google-auth google-auth-oauthlib google-api-python-client pypdfium2 Pillow pydantic-settings httpx python-dotenv
cp -r app build_temp/app
cp lambda_handler.py build_temp/
find build_temp -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
cd build_temp
zip -rq ../cowell-lambda.zip .
cd ..
rm -rf build_temp

# Upload to Lambda
aws lambda update-function-code \
  --function-name "$LAMBDA_FN" \
  --zip-file fileb://cowell-lambda.zip

echo "✅ Lambda code updated"
```

---

## 6. Create and Deploy API Gateway

### 6.1 — Create the REST API

```bash
echo "▶ Creating API Gateway..."

# Create the REST API
API_ID=$(aws apigateway create-rest-api \
  --name "cowell-ocr-api" \
  --region "$REGION" \
  --output text \
  --query 'id')

echo "  API ID: $API_ID"
echo "  API URL: https://$API_ID.execute-api.$REGION.amazonaws.com/prod"

# Get the root resource ID
ROOT_ID=$(aws apigateway get-resources \
  --rest-api-id "$API_ID" \
  --region "$REGION" \
  --output text \
  --query 'items[0].id')

echo "  Root resource ID: $ROOT_ID"
```

### 6.2 — Create Proxy Resource

```bash
# Create the {proxy+} resource
PROXY_ID=$(aws apigateway create-resource \
  --rest-api-id "$API_ID" \
  --region "$REGION" \
  --parent-id "$ROOT_ID" \
  --path-part "{proxy+}" \
  --output text \
  --query 'id')

echo "  Proxy resource ID: $PROXY_ID"
```

### 6.3 — Get Lambda ARN and Add Permission

```bash
# Get Lambda ARN
LAMBDA_ARN=$(aws lambda get-function \
  --function-name "$LAMBDA_FN" \
  --region "$REGION" \
  --output text \
  --query 'Configuration.FunctionArn')

echo "  Lambda ARN: $LAMBDA_ARN"

# Add permission for API Gateway to invoke Lambda
aws lambda add-permission \
  --function-name "$LAMBDA_FN" \
  --region "$REGION" \
  --statement-id "api-gateway-invoke" \
  --action "lambda:InvokeFunction" \
  --principal "apigateway.amazonaws.com" \
  --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/*"
```

### 6.4 — Attach Methods to Proxy

```bash
# ANY method on /{proxy+}
aws apigateway put-method \
  --rest-api-id "$API_ID" \
  --region "$REGION" \
  --resource-id "$PROXY_ID" \
  --http-method "ANY" \
  --authorization-type "NONE" \
  --no-api-key-required

# Integrate proxy with Lambda
aws apigateway put-integration \
  --rest-api-id "$API_ID" \
  --region "$REGION" \
  --resource-id "$PROXY_ID" \
  --http-method "ANY" \
  --type "AWS_PROXY" \
  --integration-http-method "POST" \
  --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations"

echo "  ✓ Proxy method (ANY /{proxy+}) configured"
```

### 6.5 — Attach Methods to Root

```bash
# ANY method on /
aws apigateway put-method \
  --rest-api-id "$API_ID" \
  --region "$REGION" \
  --resource-id "$ROOT_ID" \
  --http-method "ANY" \
  --authorization-type "NONE" \
  --no-api-key-required

# Integrate root with Lambda
aws apigateway put-integration \
  --rest-api-id "$API_ID" \
  --region "$REGION" \
  --resource-id "$ROOT_ID" \
  --http-method "ANY" \
  --type "AWS_PROXY" \
  --integration-http-method "POST" \
  --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations"

echo "  ✓ Root method (ANY /) configured"
```

### 6.6 — Deploy the API

```bash
# Create a deployment and a "prod" stage
aws apigateway create-deployment \
  --rest-api-id "$API_ID" \
  --region "$REGION" \
  --stage-name "prod" \
  --description "Deploy to prod"

echo "✅ API deployed to: https://$API_ID.execute-api.$REGION.amazonaws.com/prod"
```

### 6.7 — Test

```bash
# Save API URL for later
export API_URL="https://$API_ID.execute-api.$REGION.amazonaws.com/prod"

# Test health check
curl "$API_URL/api/health"
```

Expected:
```json
{"status":"ok","model":"gemini-2.5-flash"}
```

---

## 7. Deploy Frontend to S3

### 7.1 — Update the API URL in Frontend

```bash
echo "▶ Updating frontend config..."

# This updates the src/api/client.ts file to use the deployed API URL
# Read the current file
CLIENT_FILE="frontend/src/api/client.ts"

# Check if BASE_URL already has our API URL
if grep -q "$API_URL" "$CLIENT_FILE" 2>/dev/null; then
  echo "  ✓ API URL already set"
else
  # Replace the old BASE_URL
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS needs a backup extension
    sed -i '' "s|const BASE_URL = .*|const BASE_URL = \"$API_URL\";|" "$CLIENT_FILE"
  else
    # Linux / Git Bash
    sed -i "s|const BASE_URL = .*|const BASE_URL = \"$API_URL\";|" "$CLIENT_FILE"
  fi
  echo "  ✓ Updated BASE_URL to $API_URL"
fi
```

> ⚠️ If the sed command doesn't work, manually edit `frontend/src/api/client.ts` and change:
> ```typescript
> const BASE_URL = "/api";
> ```
> to:
> ```typescript
> const BASE_URL = "https://$API_ID.execute-api.$REGION.amazonaws.com/prod/api";
> ```

### 7.2 — Rebuild Frontend

```bash
cd frontend
npm run build
cd ..
echo "✅ Frontend built"
```

### 7.3 — Upload to S3

```bash
echo "▶ Uploading frontend to S3..."

# Enable static website hosting
aws s3api put-bucket-website \
  --bucket "$BUCKET_FRONTEND" \
  --website-configuration '{
    "IndexDocument": {"Suffix": "index.html"},
    "ErrorDocument": {"Key": "index.html"}
  }'

# Upload files
aws s3 sync frontend/dist/ "s3://$BUCKET_FRONTEND/" --delete

echo "✅ Frontend uploaded"
```

### 7.4 — Make the Bucket Public

```bash
# Disable "Block all public access"
aws s3api put-public-access-block \
  --bucket "$BUCKET_FRONTEND" \
  --public-access-block-configuration '{
    "BlockPublicAcls": true,
    "IgnorePublicAcls": true,
    "BlockPublicPolicy": false,
    "RestrictPublicBuckets": false
  }'

# Set bucket policy for public read
cat > /tmp/frontend-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::$BUCKET_FRONTEND/*"
    }
  ]
}
EOF

aws s3api put-bucket-policy \
  --bucket "$BUCKET_FRONTEND" \
  --policy file:///tmp/frontend-policy.json

echo "✅ Frontend bucket is public"

# Print the website URL
FRONTEND_URL="http://$BUCKET_FRONTEND.s3-website-$REGION.amazonaws.com"
echo "  Frontend URL: $FRONTEND_URL"
```

---

## 8. Set Up CloudFront

### 8.1 — Create Origin Access Control (OAC)

```bash
echo "▶ Creating CloudFront distribution..."

# Create Origin Access Control
OAC_ID=$(aws cloudfront create-origin-access-control \
  --origin-access-control-config '{
    "Name": "cowell-frontend-oac",
    "Description": "OAC for Cowell frontend S3 bucket",
    "SigningProtocol": "sigv4",
    "SigningBehavior": "always"
  }' \
  --output text \
  --query 'OriginAccessControl.Id')

echo "  OAC ID: $OAC_ID"
```

### 8.2 — Create Distribution

```bash
# Get the S3 bucket's regional domain name
S3_DOMAIN="$BUCKET_FRONTEND.s3.$REGION.amazonaws.com"

# Create the JSON config for CloudFront distribution
cat > /tmp/cloudfront-config.json << 'EOF'
{
  "CallerReference": "cowell-frontend-'"$(date +%s)"'",
  "Aliases": { "Quantity": 0 },
  "DefaultRootObject": "index.html",
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "S3Origin",
        "DomainName": "'"$S3_DOMAIN"'",
        "OriginAccessControlId": "'"$OAC_ID"'",
        "S3OriginConfig": { "OriginAccessIdentity": "" }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3Origin",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 3,
      "Items": ["GET", "HEAD", "OPTIONS"],
      "CachedMethods": { "Quantity": 3, "Items": ["GET", "HEAD", "OPTIONS"] }
    },
    "Compress": true,
    "DefaultTTL": 86400,
    "MaxTTL": 31536000,
    "MinTTL": 0,
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": { "Forward": "none" }
    }
  },
  "PriceClass": "PriceClass_100",
  "Enabled": true,
  "CustomErrorResponses": {
    "Quantity": 2,
    "Items": [
      {
        "ErrorCode": 403,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 0
      },
      {
        "ErrorCode": 404,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 0
      }
    ]
  }
}
EOF

# Create the distribution
DISTRIBUTION_ID=$(aws cloudfront create-distribution \
  --distribution-config file:///tmp/cloudfront-config.json \
  --output text \
  --query 'Distribution.Id')

# Get the CloudFront domain name
CF_DOMAIN=$(aws cloudfront get-distribution \
  --id "$DISTRIBUTION_ID" \
  --output text \
  --query 'Distribution.DomainName')

echo "✅ CloudFront distribution created"
echo "  Distribution ID: $DISTRIBUTION_ID"
echo "  Domain: https://$CF_DOMAIN"
```

### 8.3 — Update S3 Bucket Policy for CloudFront

We need to get the exact policy that CloudFront generates for OAC. Unfortunately, with the CLI approach, we need to construct it manually:

```bash
# Get the OAC ARN
OAC_ARN="arn:aws:cloudfront::$ACCOUNT_ID:origin-access-control/$OAC_ID"

# Create a bucket policy that allows CloudFront access
cat > /tmp/cf-bucket-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudfront.amazonaws.com"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::$BUCKET_FRONTEND/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::$ACCOUNT_ID:distribution/$DISTRIBUTION_ID"
        }
      }
    }
  ]
}
EOF

aws s3api put-bucket-policy \
  --bucket "$BUCKET_FRONTEND" \
  --policy file:///tmp/cf-bucket-policy.json

echo "✅ S3 bucket policy updated for CloudFront"
```

### 8.4 — Update CORS in Backend

Add the CloudFront URL to the CORS origins in `backend/app/main.py`:

```bash
echo "▶ Updating CORS settings..."

# Read the current main.py
MAIN_FILE="backend/app/main.py"

# Add CloudFront URL to allow_origins if not already there
if grep -q "$CF_DOMAIN" "$MAIN_FILE" 2>/dev/null; then
  echo "  ✓ CORS already includes CloudFront URL"
else
  # Insert the CloudFront URL into the allow_origins list
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|allow_origins=\[|allow_origins=[\"https://$CF_DOMAIN\", |" "$MAIN_FILE"
  else
    sed -i "s|allow_origins=\[|allow_origins=[\"https://$CF_DOMAIN\", |" "$MAIN_FILE"
  fi
  echo "  ✓ Added https://$CF_DOMAIN to CORS origins"
fi
```

### 8.5 — Rebuild and Re-deploy Lambda

```bash
echo "▶ Rebuilding and redeploying Lambda with updated CORS..."

cd backend

mkdir -p build_temp
pip install -t build_temp/ mangum boto3 fastapi uvicorn python-multipart google-genai gspread google-auth google-auth-oauthlib google-api-python-client pypdfium2 Pillow pydantic-settings httpx python-dotenv
cp -r app build_temp/app
cp lambda_handler.py build_temp/
find build_temp -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
cd build_temp
zip -rq ../cowell-lambda.zip .
cd ..
rm -rf build_temp

aws lambda update-function-code \
  --function-name "$LAMBDA_FN" \
  --zip-file fileb://cowell-lambda.zip

echo "✅ Lambda redeployed with updated CORS"
```

### 8.6 — Wait for CloudFront

```bash
echo "⏳ Waiting for CloudFront distribution to deploy..."
echo "  This takes 5-15 minutes."

# Check status
aws cloudfront get-distribution \
  --id "$DISTRIBUTION_ID" \
  --output text \
  --query 'Distribution.Status'

echo "  Run this to check status later:"
echo "  aws cloudfront get-distribution --id $DISTRIBUTION_ID --query 'Distribution.Status'"
```

---

## 9. Final Steps

### 9.1 — Test the Health Check

```bash
echo "▶ Testing..."

# Backend health check
curl -s "$API_URL/api/health" | python -m json.tool
```

### 9.2 — Test the Frontend

```bash
echo "Frontend URL: https://$CF_DOMAIN"
echo "Backend URL: $API_URL"
```

Open the Frontend URL in your browser and test the full workflow:
1. Upload a PDF → 2. Run OCR → 3. Verify data → 4. Register to Google Sheet

### 9.3 — Save Deployment Info

```bash
echo "▶ Saving deployment info..."

cat > deploy-info.txt << EOF
Cowell OCR — Deployment Information
====================================
Deployed: $(date)

Frontend URL:    https://$CF_DOMAIN
Backend API URL: $API_URL
Health Check:    $API_URL/api/health

AWS Resources:
  Lambda:               $LAMBDA_FN
  API Gateway ID:       $API_ID
  CloudFront ID:        $DISTRIBUTION_ID

S3 Buckets:
  Uploads:              $BUCKET_UPLOADS
  Sessions:             $BUCKET_SESSIONS
  Token:                $BUCKET_TOKEN
  Frontend:             $BUCKET_FRONTEND

Region: $REGION
Account: $ACCOUNT_ID
====================================
EOF

echo "✅ Saved to deploy-info.txt"
```

---

## 10. Cost Breakdown

### Free Tier (12 months): **$0/month**

| Service | Free Tier | Our Usage |
|---------|-----------|-----------|
| Lambda | 1M req/mo, 400K GB-seconds | ~100 req, ~512MB, ~30s |
| API Gateway | 1M calls/mo | ~1,000 calls |
| S3 | 5GB storage | ~100MB |
| CloudFront | 1TB transfer/mo | ~100MB |
| CloudWatch | 5GB logs/mo | ~50MB |

### After Free Tier: **~$0.21/month**

---

## 11. Cleanup

Run these commands to delete everything and avoid charges:

```bash
echo "▶ Cleaning up all resources..."

# Delete CloudFront distribution (must disable first)
DISTRIBUTION_ETAG=$(aws cloudfront get-distribution \
  --id "$DISTRIBUTION_ID" \
  --output text \
  --query 'ETag')

aws cloudfront update-distribution \
  --id "$DISTRIBUTION_ID" \
  --distribution-config file:///tmp/cloudfront-config-disabled.json 2>/dev/null || true

# For full cleanup, use the AWS Console for CloudFront (disabling via CLI is complex)
# Proceed with other resources:

# Empty and delete S3 buckets
aws s3 rb "s3://$BUCKET_UPLOADS" --force
aws s3 rb "s3://$BUCKET_SESSIONS" --force
aws s3 rb "s3://$BUCKET_TOKEN" --force
aws s3 rb "s3://$BUCKET_FRONTEND" --force

# Delete Lambda function
aws lambda delete-function --function-name "$LAMBDA_FN" --region "$REGION"

# Delete API Gateway
aws apigateway delete-rest-api --rest-api-id "$API_ID" --region "$REGION"

# Delete IAM role policies and role
aws iam detach-role-policy \
  --role-name "$LAMBDA_FN-role" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role-policy --role-name "$LAMBDA_FN-role" --policy-name "s3-access"
aws iam delete-role --role-name "$LAMBDA_FN-role"

# Delete CloudWatch log group
aws logs delete-log-group \
  --log-group-name "/aws/lambda/$LAMBDA_FN" \
  --region "$REGION"

echo "✅ Cleanup complete"
```

> ⚠️ For CloudFront, you must **disable** the distribution first (wait for deployment), then **delete** it. This is easiest to do via the AWS Console.

---

## 12. Troubleshooting

### 12.1 — Check Lambda Logs

```bash
aws logs tail "/aws/lambda/$LAMBDA_FN" --region "$REGION" --since 5m
```

### 12.2 — Invoke Lambda Directly

```bash
# Test with a health check event
aws lambda invoke \
  --function-name "$LAMBDA_FN" \
  --region "$REGION" \
  --payload '{
    "httpMethod": "GET",
    "path": "/api/health",
    "headers": {},
    "queryStringParameters": null,
    "pathParameters": null,
    "body": null,
    "isBase64Encoded": false
  }' \
  response.json

cat response.json
```

### 12.3 — Common Issues

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| `Internal server error` | Missing env var or dependency | Check logs: `aws logs tail` |
| `pypdfium2` import error | Windows ZIP on Linux Lambda | Use `--platform manylinux2014_x86_64` in pip install |
| CORS error in browser | CloudFront URL not in `allow_origins` | Update `main.py`, re-deploy Lambda |
| 403 on CloudFront | Bucket policy wrong | Check `cf-bucket-policy.json` |
| Token expired | OAuth token expired | Re-run `auth_oauth.py`, upload to S3 |
| Upload > 10MB fails | API Gateway limit | Split PDF files |

---

## Appendix: Complete One-Click Deploy Script

Save this as `deploy-aws.sh` in your project root:

```bash
#!/bin/bash
set -e
echo "========================================"
echo " Cowell OCR — AWS Serverless Deploy"
echo "========================================"

# ── EDIT THESE ─────────────────────────────────────
BUCKET_SUFFIX="${1:-john1985-123}"
REGION="${2:-ap-northeast-1}"
GEMINI_API_KEY="${3:-}"
GOOGLE_TARGET_FOLDER_ID="${4:-}"
# ─────────────────────────────────────────────────

if [ -z "$GEMINI_API_KEY" ]; then
  echo "Usage: ./deploy-aws.sh <suffix> <region> <gemini-api-key> [drive-folder-id]"
  echo "Example: ./deploy-aws.sh john1985-123 ap-northeast-1 AIzaSy..."
  exit 1
fi

# ── Derived vars ──────────────────────────────────
BUCKET_UPLOADS="cowell-uploads-$BUCKET_SUFFIX"
BUCKET_SESSIONS="cowell-sessions-$BUCKET_SUFFIX"
BUCKET_TOKEN="cowell-token-$BUCKET_SUFFIX"
BUCKET_FRONTEND="cowell-frontend-$BUCKET_SUFFIX"
LAMBDA_FN="cowell-ocr-backend"
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)

echo ""
echo "Region:         $REGION"
echo "Bucket suffix:  $BUCKET_SUFFIX"
echo "Account:        $ACCOUNT_ID"
echo ""

# ── Step 1: S3 Buckets ────────────────────────────
echo "▶ Step 1/7: S3 Buckets"
create_bucket() {
  local n="$1"
  aws s3api head-bucket --bucket "$n" 2>/dev/null && echo "  ✓ $n exists" || {
    [ "$REGION" = "us-east-1" ] && \
      aws s3api create-bucket --bucket "$n" --region "$REGION" || \
      aws s3api create-bucket --bucket "$n" --region "$REGION" \
        --create-bucket-configuration LocationConstraint="$REGION"
    echo "  ✓ Created $n"
  }
}
create_bucket "$BUCKET_UPLOADS"
create_bucket "$BUCKET_SESSIONS"
create_bucket "$BUCKET_TOKEN"
create_bucket "$BUCKET_FRONTEND"

# ── Step 2: Upload Token ─────────────────────────
echo "▶ Step 2/7: OAuth Token"
if [ -f backend/credentials/token.json ]; then
  aws s3 cp backend/credentials/token.json "s3://$BUCKET_TOKEN/credentials/token.json"
else
  echo "  ⚠️  token.json not found. Run 'python auth_oauth.py' first."
fi

# ── Step 3: IAM Role ─────────────────────────────
echo "▶ Step 3/7: IAM Role"
ROLE_NAME="$LAMBDA_FN-role"
aws iam create-role --role-name "$ROLE_NAME" \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' 2>/dev/null || true
aws iam attach-role-policy --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
cat > /tmp/s3-pol.json << XEOF
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket"],"Resource":["arn:aws:s3:::$BUCKET_UPLOADS","arn:aws:s3:::$BUCKET_UPLOADS/*","arn:aws:s3:::$BUCKET_SESSIONS","arn:aws:s3:::$BUCKET_SESSIONS/*","arn:aws:s3:::$BUCKET_TOKEN","arn:aws:s3:::$BUCKET_TOKEN/*"]}]}
XEOF
aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name "s3-access" \
  --policy-document file:///tmp/s3-pol.json
sleep 3
ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)

# ── Step 4: Lambda ───────────────────────────────
echo "▶ Step 4/7: Lambda Function"
cd backend
mkdir -p build_temp
pip install -t build_temp/ mangum boto3 fastapi uvicorn python-multipart google-genai gspread google-auth google-auth-oauthlib google-api-python-client pypdfium2 Pillow pydantic-settings httpx python-dotenv --quiet
cp -r app build_temp/app
cp lambda_handler.py build_temp/
find build_temp -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
cd build_temp && zip -rq ../cowell-lambda.zip . && cd ..
rm -rf build_temp
cd ..

aws lambda create-function \
  --function-name "$LAMBDA_FN" \
  --runtime python3.12 --role "$ROLE_ARN" \
  --handler lambda_handler.handler \
  --zip-file fileb://backend/cowell-lambda.zip \
  --memory-size 512 --timeout 300 \
  --environment "Variables={GEMINI_API_KEY=$GEMINI_API_KEY,S3_BUCKET_UPLOADS=$BUCKET_UPLOADS,S3_BUCKET_SESSIONS=$BUCKET_SESSIONS,S3_BUCKET_TOKEN=$BUCKET_TOKEN,S3_TOKEN_KEY=credentials/token.json,GOOGLE_OAUTH_TARGET_FOLDER_ID=$GOOGLE_TARGET_FOLDER_ID}" \
  --region "$REGION" 2>/dev/null || {
  echo "  Function exists, updating code instead..."
  aws lambda update-function-code --function-name "$LAMBDA_FN" --zip-file fileb://backend/cowell-lambda.zip --region "$REGION"
}

# ── Step 5: API Gateway ──────────────────────────
echo "▶ Step 5/7: API Gateway"
API_ID=$(aws apigateway create-rest-api --name "cowell-ocr-api" --region "$REGION" --output text --query 'id')
ROOT_ID=$(aws apigateway get-resources --rest-api-id "$API_ID" --region "$REGION" --output text --query 'items[0].id')
PROXY_ID=$(aws apigateway create-resource --rest-api-id "$API_ID" --region "$REGION" --parent-id "$ROOT_ID" --path-part "{proxy+}" --output text --query 'id')
LAMBDA_ARN=$(aws lambda get-function --function-name "$LAMBDA_FN" --region "$REGION" --output text --query 'Configuration.FunctionArn')
aws lambda add-permission --function-name "$LAMBDA_FN" --region "$REGION" --statement-id "api-gw" --action "lambda:InvokeFunction" --principal "apigateway.amazonaws.com" --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/*" 2>/dev/null || true

for RES in "$ROOT_ID" "$PROXY_ID"; do
  aws apigateway put-method --rest-api-id "$API_ID" --region "$REGION" --resource-id "$RES" --http-method "ANY" --authorization-type "NONE" --no-api-key-required
  aws apigateway put-integration --rest-api-id "$API_ID" --region "$REGION" --resource-id "$RES" --http-method "ANY" --type "AWS_PROXY" --integration-http-method "POST" --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations"
done

aws apigateway create-deployment --rest-api-id "$API_ID" --region "$REGION" --stage-name "prod"
API_URL="https://$API_ID.execute-api.$REGION.amazonaws.com/prod"

# ── Step 6: Frontend ─────────────────────────────
echo "▶ Step 6/7: Frontend"
sed -i "s|const BASE_URL = .*|const BASE_URL = \"$API_URL\";|" frontend/src/api/client.ts
cd frontend && npm run build --silent && cd ..
aws s3api put-bucket-website --bucket "$BUCKET_FRONTEND" --website-configuration '{"IndexDocument":{"Suffix":"index.html"},"ErrorDocument":{"Key":"index.html"}}'
aws s3 sync frontend/dist/ "s3://$BUCKET_FRONTEND/" --delete --quiet
aws s3api put-public-access-block --bucket "$BUCKET_FRONTEND" --public-access-block-configuration '{"BlockPublicAcls":true,"IgnorePublicAcls":true,"BlockPublicPolicy":false,"RestrictPublicBuckets":false}'
cat > /tmp/fp.json << XEOF
{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::$BUCKET_FRONTEND/*"}]}
XEOF
aws s3api put-bucket-policy --bucket "$BUCKET_FRONTEND" --policy file:///tmp/fp.json

# ── Step 7: Summary ──────────────────────────────
echo ""
echo "========================================"
echo "  ✅ DEPLOYMENT COMPLETE"
echo "========================================"
echo ""
echo "  Frontend (S3):  http://$BUCKET_FRONTEND.s3-website-$REGION.amazonaws.com"
echo "  Backend API:    $API_URL"
echo "  Health Check:   $API_URL/api/health"
echo ""
echo "  Next: Set up CloudFront manually via Console for HTTPS."
echo "  See deploy-aws-console.md → Section 8."
echo "========================================"
```

Run it:
```bash
chmod +x deploy-aws.sh
./deploy-aws.sh john1985-123 ap-northeast-1 AIzaSyYourGeminiKey
```

---

## Quick Reference

```
═══════════════════════════════════════════════════════
                    CLI QUICK REFERENCE
═══════════════════════════════════════════════════════

S3 Buckets:
  cowell-uploads-{suffix}    Private — temp files
  cowell-sessions-{suffix}   Private — session JSON
  cowell-token-{suffix}      Private — OAuth token
  cowell-frontend-{suffix}   Public — React static files

Lambda:
  Function:     cowell-ocr-backend
  Runtime:      Python 3.12
  Handler:      lambda_handler.handler
  Memory:       512 MB
  Timeout:      300s (5 min)

API Gateway:
  ID:           $(API_ID)
  URL:          https://{id}.execute-api.{region}.amazonaws.com/prod
  Proxy:        /{proxy+} (ANY) + / (ANY)

CloudFront:
  Distribution: $(DISTRIBUTION_ID)
  Domain:       https://{id}.cloudfront.net

Env Vars (Lambda):
  GEMINI_API_KEY=AIzaSy...
  S3_BUCKET_UPLOADS=cowell-uploads-{suffix}
  S3_BUCKET_SESSIONS=cowell-sessions-{suffix}
  S3_BUCKET_TOKEN=cowell-token-{suffix}
  S3_TOKEN_KEY=credentials/token.json

Key CLI Commands:
  Update Lambda code:
    aws lambda update-function-code --function-name cowell-ocr-backend \
      --zip-file fileb://backend/cowell-lambda.zip

  Check Lambda logs:
    aws logs tail "/aws/lambda/cowell-ocr-backend" --since 5m

  Health check:
    curl {API_URL}/api/health

Cost: <$0.21/month ✅
═══════════════════════════════════════════════════════
```
