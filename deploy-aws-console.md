# 🖱️ AWS Serverless Deployment — AWS Console Guide
## Cowell OCR MVP

> **Target audience:** Absolute beginners who have never deployed to AWS.
> **No commands required.** Everything is done through the AWS Console (web UI).
> **Estimated cost:** **Less than $1/month** for low usage.

---

## Table of Contents

- [0. Architecture Overview](#0-architecture-overview)
- [1. Create an AWS Account](#1-create-an-aws-account)
- [2. Prepare the Code for Deployment](#2-prepare-the-code-for-deployment)
- [3. Create S3 Buckets (Storage)](#3-create-s3-buckets-storage)
- [4. Upload OAuth Token to S3](#4-upload-oauth-token-to-s3)
- [5. Create the Lambda Function (Backend)](#5-create-the-lambda-function-backend)
- [6. Set Up API Gateway](#6-set-up-api-gateway)
- [7. Deploy the Frontend (React)](#7-deploy-the-frontend-react)
- [8. Set Up CloudFront (CDN + HTTPS)](#8-set-up-cloudfront-cdn--https)
- [9. Test Everything](#9-test-everything)
- [10. Cost Breakdown](#10-cost-breakdown)
- [11. Troubleshooting](#11-troubleshooting)
- [12. Cleanup (To Avoid Charges)](#12-cleanup-to-avoid-charges)

---

## 0. Architecture Overview

Here's what we're building:

```
                    ┌─────────────────────────────────────────────┐
                    │         CloudFront CDN                      │
                    │   (serves frontend, proxies /api to API GW) │
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
                                               └──┬───────┬───┘
                                                  │       │
                                        ┌─────────▼──┐ ┌──▼──────────┐
                                        │ S3 Bucket  │ │ S3 Bucket   │
                                        │ (sessions) │ │ (uploads)   │
                                        └────────────┘ └─────────────┘
```

**Services we'll use (all free-tier eligible):**

| AWS Service | What it does for us |
|-------------|-------------------|
| **S3** | Stores our React files, temp uploads, session data, and OAuth token |
| **Lambda** | Runs the Python backend (FastAPI) — no server to manage |
| **API Gateway** | Gives Lambda an HTTP URL that our frontend can call |
| **CloudFront** | Delivers the frontend fast with HTTPS worldwide |
| **CloudWatch** | Lets us see backend logs for debugging |
| **IAM** | Controls permissions between AWS services |

---

## 1. Create an AWS Account

### Step 1.1 — Go to AWS

1. Open your browser and go to [https://aws.amazon.com/free/](https://aws.amazon.com/free/)
2. Click the orange **"Create a Free Account"** button (top right)

### Step 1.2 — Sign up

1. Enter your **email address** and an **AWS account name** (e.g., `cowell-account`)
2. Choose **"Personal"** for account type
3. Fill in your name, phone number, address, and credit card info
   - > ⚠️ **Don't worry:** Everything in this guide stays within the Free Tier. AWS charges only if you exceed free limits. Set a budget alert in Step 1.4.
4. Verify your identity with a phone call (they call and give a code)
5. Choose the **"Basic (free)"** support plan
6. Click **"Sign up"** and wait for confirmation (usually 1-2 minutes)

> ✅ You now have an AWS account! Log in at [https://console.aws.amazon.com/](https://console.aws.amazon.com/)

### Step 1.3 — Pick a Region

At the top right of the AWS Console, you'll see a region name (e.g., "N. Virginia" or "Ohio").

Click it and select **Asia Pacific (Tokyo) — `ap-northeast-1`**.

> Why Tokyo? It's closest to Japan, giving the lowest latency. If you're elsewhere, pick the nearest region:
> - **North America:** `us-east-1` (N. Virginia) — cheapest, most services
> - **Europe:** `eu-west-1` (Ireland)
> - **Southeast Asia:** `ap-southeast-1` (Singapore)

### Step 1.4 — Set a Budget Alert (Optional but Recommended)

1. In the search bar at the top, type **"Billing"** and click it
2. In the left menu, click **"Budgets"**
3. Click **"Create budget"**
4. **Budget type:** Cost budget
5. **Name:** `monthly-limit`
6. **Period:** Monthly
7. **Budget amount:** `$5`
8. **Email recipients:** Your email
9. Click **"Create budget"**

> ✅ If costs ever exceed $5, you'll get an email alert.

---

## 2. Prepare the Code for Deployment

Before we go to AWS, we need to prepare the code on your computer.

### Step 2.1 — Open Your Project Folder

Open **File Explorer** and go to your project folder:

```
E:\Projects\AONE Properties\cowell-mvp
```

### Step 2.2 — Install Mangum and boto3

We need two Python packages for Lambda deployment. Open **Git Bash** (or Command Prompt) and run:

```bash
cd backend
pip install mangum boto3
```

> 💡 If you use `uv` (the project's package manager):
> ```bash
> uv add mangum boto3
> ```

### Step 2.3 — Check That lambda_handler.py Exists

In your project folder, check if this file exists:

```
backend/lambda_handler.py
```

If it doesn't exist, create it by opening **Notepad** and pasting this:

```python
"""
Lambda entry point for Cowell OCR API.
Downloads OAuth token from S3, wraps FastAPI with Mangum.
"""
import json
import logging
import os
from pathlib import Path
import boto3
from mangum import Mangum

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("cowell.lambda")

# ── Download OAuth token from S3 on cold start ──────────────────
S3_BUCKET_TOKEN = os.environ.get("S3_BUCKET_TOKEN", "")
S3_TOKEN_KEY = os.environ.get("S3_TOKEN_KEY", "credentials/token.json")

token_dir = Path("/tmp/credentials")
token_dir.mkdir(parents=True, exist_ok=True)
token_path = token_dir / "token.json"

if S3_BUCKET_TOKEN and not token_path.exists():
    try:
        s3 = boto3.client("s3")
        s3.download_file(S3_BUCKET_TOKEN, S3_TOKEN_KEY, str(token_path))
        log.info("Downloaded OAuth token from s3://%s/%s", S3_BUCKET_TOKEN, S3_TOKEN_KEY)
    except Exception as exc:
        log.error("Failed to download OAuth token: %s", exc)

os.environ["GOOGLE_OAUTH_TOKEN_PATH"] = str(token_path)

# ── Import the FastAPI app ─────────────────────────────────────
from app.main import app

# ── Create Mangum handler for Lambda ───────────────────────────
handler = Mangum(app, lifespan="off")
```

Save it as `backend/lambda_handler.py`.

### Step 2.4 — Update the Frontend API URL

Open the file `frontend/src/api/client.ts` in a text editor (like Notepad).

Find the line that says:
```typescript
const BASE_URL = "/api";
```

Replace it with:
```typescript
// Will update this URL after API Gateway is created
// For now, keep /api for local dev
const BASE_URL = "/api";
```

We'll come back and change this later once we have the API Gateway URL.

### Step 2.5 — Update CORS Settings (For Later)

Open `backend/app/main.py` and find the CORS section. It should look like:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    ...
)
```

We'll add your CloudFront URL here later (in Step 8.8).

### Step 2.6 — Build the Deployment ZIP

Open **Git Bash** in the `backend` folder:

```bash
cd backend
```

Now create the deployment package:

```bash
# Create a temporary directory
mkdir -p build_temp

# Install all dependencies into it
pip install -t build_temp/ mangum boto3 fastapi uvicorn python-multipart google-genai gspread google-auth google-auth-oauthlib google-api-python-client pypdfium2 Pillow pydantic-settings httpx python-dotenv

# Copy your app code
cp -r app build_temp/app
cp lambda_handler.py build_temp/

# Remove unnecessary files
rm -rf build_temp/__pycache__ build_temp/app/__pycache__
find build_temp -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find build_temp -name "*.pyc" -delete

# Create the ZIP
cd build_temp
zip -rq ../cowell-lambda.zip .
cd ..

# Clean up
rm -rf build_temp

echo "✅ Created: cowell-lambda.zip"
```

> 🐌 This will take a minute. The ZIP file will be about 30-50MB.

> ⚠️ **If you're on Windows:** The ZIP may include Windows-specific binaries for pypdfium2 that won't work on Lambda (which runs Linux). Don't worry — we'll handle this in Step 5.7 (Lambda Layers).

### Step 2.7 — Build the Frontend

In **Git Bash**, from the project root:

```bash
cd frontend
npm install
npm run build
```

This creates a `frontend/dist` folder with the built website files.

> ✅ Your code is ready. Put `cowell-lambda.zip` and the `frontend/dist` folder somewhere you can find — we'll use them in the AWS Console.

---

## 3. Create S3 Buckets (Storage)

S3 is like Google Drive for apps. Each bucket is a folder with files. We need **4 buckets**.

### Step 3.1 — Open S3 in AWS Console

1. Log into [AWS Console](https://console.aws.amazon.com/)
2. In the **search bar at the top**, type `S3`
3. Click the first result: **"S3"** (under Services)

### Step 3.2 — Create the Uploads Bucket

1. Click the orange **"Create bucket"** button
2. **Bucket name:** Enter `cowell-uploads-` followed by something unique
   - Example: `cowell-uploads-john1985`
   - ⚠️ Bucket names must be **globally unique**. If it says "name already exists", add more numbers like `cowell-uploads-john1985-123`
3. **AWS Region:** Make sure it shows the region you picked (e.g., `Asia Pacific (Tokyo) ap-northeast-1`)
4. **Block Public Access settings:** Leave all **4 checkboxes checked** (this bucket must be private)
5. **Bucket Versioning:** Disable
6. Leave everything else as default
7. Click the orange **"Create bucket"** button at the bottom

### Step 3.3 — Create the Sessions Bucket

1. Click **"Create bucket"** again
2. **Bucket name:** `cowell-sessions-john1985-123` (use same suffix)
3. **Block Public Access:** All checked (private)
4. Click **"Create bucket"**

### Step 3.4 — Create the Token Bucket

1. Click **"Create bucket"** again
2. **Bucket name:** `cowell-token-john1985-123` (use same suffix)
3. **Block Public Access:** All checked (private)
4. Click **"Create bucket"**

### Step 3.5 — Create the Frontend Bucket

1. Click **"Create bucket"** again
2. **Bucket name:** `cowell-frontend-john1985-123` (use same suffix)
3. **Block Public Access:** This one will be **partially public** — leave all checked for now (we'll make it public in Step 7.4)
4. Click **"Create bucket"**

> ✅ You should now see 4 buckets in your list. Write down the names somewhere.

---

## 4. Upload OAuth Token to S3

Your `token.json` file contains the Google OAuth credentials that the backend needs to create Google Sheets and upload photos to Google Drive.

### Step 4.1 — Find Your token.json

On your computer, go to:

```
E:\Projects\AONE Properties\cowell-mvp\backend\credentials\token.json
```

> ⚠️ If this file doesn't exist, you need to generate it first. Open Git Bash in the backend folder and run:
> ```bash
> python auth_oauth.py
> ```
> This will open a browser window — log into Google and authorize the app.

### Step 4.2 — Upload token.json to S3

1. Go back to the S3 page in AWS Console
2. Click on your **token bucket**: `cowell-token-john1985-123`
3. Click the **"Upload"** button

   ```
   ┌──────────────────────────────────────────────┐
   │   │  Upload  │  Create folder  │  Download   │
   └──────────────────────────────────────────────┘
   ```

4. Click **"Add files"** and select your `token.json`
5. Under **"Destination"**, you'll see the path. We need it inside a folder called `credentials/`:
   - Click **"Add folder"**
   - Type: `credentials`
   - Click into the `credentials/` folder
   - Now click **"Add files"** again and select `token.json`
6. Click the orange **"Upload"** button at the bottom
7. After upload, you should see: `credentials/token.json` in your bucket

> ✅ Token is stored. Lambda will download it when it starts.

---

## 5. Create the Lambda Function (Backend)

Lambda runs your Python code in response to API calls — no server to manage.

### Step 5.1 — Open Lambda in AWS Console

1. In the search bar, type `Lambda`
2. Click **"Lambda"** (under Services)

### Step 5.2 — Create the Function

1. Click the orange **"Create function"** button
2. Select **"Author from scratch"** (this should be highlighted)
3. **Function name:** Type `cowell-ocr-backend`
4. **Runtime:** Click the dropdown and select **Python 3.12**
   - (If 3.12 isn't listed, select the latest Python 3.x available)
5. **Architecture:** Keep **x86_64**
6. **Permissions:** Click **"Change default execution role"**
   - Select **"Create a new role with basic Lambda permissions"**
   - This creates a role that lets Lambda write logs to CloudWatch
7. Click the orange **"Create function"** button

> Wait 10-20 seconds while AWS creates the function.

### Step 5.3 — Upload Your Code

Scroll down to the **"Code source"** section.

```
┌─────────────────────────────────────────────────┐
│ Code source                                      │
│ ┌─────────────────────────────────────────────┐  │
│ │                                             │  │
│ │  [Upload from]  ▼  [Save]  [Test]          │  │
│ │                                             │  │
│ └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

1. Click the **"Upload from"** dropdown button
2. Select **".zip file"**
3. Click **"Upload"** and select the `cowell-lambda.zip` file you created earlier
4. Click **"Save"** (top right of the code section)

> Wait 10-20 seconds for the upload to finish.

### Step 5.4 — Set the Handler

Look at the **"Runtime settings"** section (above the code section):

1. Click **"Edit"**
2. **Handler:** Change it to `lambda_handler.handler`
   - (This tells Lambda: "run the function named `handler` inside the file `lambda_handler.py`")
3. Click **"Save"**

### Step 5.5 — Configure Environment Variables

Scroll down to **"Environment variables"** and click **"Edit"**:

```
┌──────────────────────────────────────────────┐
│ Environment variables                         │
│ [Edit]                                        │
│ ┌──────────────────────────────────────────┐  │
│ │ No environment variables configured      │  │
│ └──────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

1. Click **"Add environment variable"** — do this for each row below:

| Key | Value | Example |
|-----|-------|---------|
| `GEMINI_API_KEY` | *(your Gemini API key)* | `AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz12345` |
| `S3_BUCKET_UPLOADS` | *(your uploads bucket name)* | `cowell-uploads-john1985-123` |
| `S3_BUCKET_SESSIONS` | *(your sessions bucket name)* | `cowell-sessions-john1985-123` |
| `S3_BUCKET_TOKEN` | *(your token bucket name)* | `cowell-token-john1985-123` |
| `S3_TOKEN_KEY` | *(path to token in bucket)* | `credentials/token.json` |

2. Optionally add (if you want sheets created in a specific Drive folder):
   `GOOGLE_OAUTH_TARGET_FOLDER_ID` = *(your Google Drive folder ID)*

3. Click **"Save"**

### Step 5.6 — Increase Memory and Timeout

OCR processing takes time. Default Lambda settings are too small.

1. Click the **"Configuration"** tab (next to "Code")
2. In the left sidebar, click **"General configuration"**
3. Click **"Edit"**

   ```
   ┌──────────────────────────────────────────────┐
   │ General configuration                        │
   │ [Edit]                                       │
   │ Memory (MB): 128 MB                          │
   │ Timeout: 3 seconds    ← Too small!           │
   │ ...                                          │
   └──────────────────────────────────────────────┘
   ```

4. **Memory (MB):** Change from `128` to **`512`**
   - (More memory = faster processing. 512MB is the sweet spot for Python + image processing)
5. **Timeout:** Change from `0 min 3 sec` to **`5 min`**
   - (Set minutes to `5`, seconds to `0`)
6. Click **"Save"**

### Step 5.7 — Add Lambda Permissions to Access S3

Lambda needs permission to read/write to your S3 buckets.

1. Still on the **"Configuration"** tab
2. In the left sidebar, click **"Permissions"**

   ```
   ┌──────────────────────────────────────────────┐
   │ Resource summary                             │
   │ Execution role: cowell-ocr-backend-role-xxxxx │
   │ [Click this link]                            │
   └──────────────────────────────────────────────┘
   ```

3. Click the link under **"Execution role"** (it's a blue link)
   - This opens IAM in a new browser tab

4. In IAM, you'll see the role page. Click **"Add permissions"** → **"Create inline policy"**

   ```
   ┌──────────────────────────────────────────────┐
   │ Permissions policies (1 policy, 0 associated │
   │ [Add permissions] ▼                          │
   │ ├ Attach policies                            │
   │ └ Create inline policy    ← Click this       │
   └──────────────────────────────────────────────┘
   ```

5. Click the **"JSON"** tab (not "Visual")

6. **Delete** the existing text and **paste** this instead (replace `john1985-123` with your actual suffix):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::cowell-uploads-john1985-123",
                "arn:aws:s3:::cowell-uploads-john1985-123/*",
                "arn:aws:s3:::cowell-sessions-john1985-123",
                "arn:aws:s3:::cowell-sessions-john1985-123/*",
                "arn:aws:s3:::cowell-token-john1985-123",
                "arn:aws:s3:::cowell-token-john1985-123/*"
            ]
        }
    ]
}
```

> 💡 Replace `john1985-123` with the suffix you used for your bucket names!

7. Click **"Next"**
8. **Policy name:** Type `cowell-s3-access`
9. Click **"Create policy"**

> ✅ Lambda can now read/write to your S3 buckets.

### Step 5.8 — Add Lambda Layers (Fix for pypdfium2)

**Skip this step if you created the ZIP on Linux/Mac.** This is only needed if you created the ZIP on **Windows** (because pypdfium2 includes Windows-native DLLs that won't run on Lambda's Linux).

We need to create a Lambda Layer with Linux-compatible libraries.

**Using AWS CloudShell (easier method):**

1. In the AWS Console, look at the **top navigation bar** — you'll see an icon that looks like `>_`
   - It's next to the search bar
   - Hover over it and it says "CloudShell"
2. Click it. A terminal panel will open at the bottom of the screen (this is a Linux terminal in AWS)

3. In CloudShell, paste these commands one by one (right-click to paste):

```bash
# Create a directory for the layer
mkdir -p python/lib/python3.12/site-packages

# Install pypdfium2 with Linux-native binaries
pip3 install pypdfium2 Pillow -t python/lib/python3.12/site-packages --platform manylinux2014_x86_64 --only-binary=:all:

# Remove unnecessary files to reduce size
rm -rf python/lib/python3.12/site-packages/*.dist-info
rm -rf python/lib/python3.12/site-packages/__pycache__

# Create the ZIP
zip -r pypdfium2-layer.zip python/

# Upload to S3 (replace with your actual uploads bucket name)
aws s3 cp pypdfium2-layer.zip s3://cowell-uploads-john1985-123/layers/
```

4. Now go back to the **Lambda Console** (not CloudShell)
5. In the left menu of Lambda, click **"Layers"**

   ```
   ┌──────────────────────────────────────────────┐
   │ Lambda                                        │
   │ ├ Functions                                   │
   │ ├ Layers                    ← Click this      │
   │ └ Additional configurations                   │
   └──────────────────────────────────────────────┘
   ```

6. Click **"Create layer"**

   ```
   ┌──────────────────────────────────────────────┐
   │ Layer configuration                           │
   │ Name: [________________]                      │
   │ Description: (optional)                       │
   │ Layer packaging: ○ Upload a .zip file         │
   │                ● Upload a file from Amazon S3  │
   │ S3 link URL: [_____________________________]  │
   └──────────────────────────────────────────────┘
   ```

7. **Name:** Type `pypdfium2-pillow`
8. **Layer packaging:** Select **"Upload a file from Amazon S3"**
9. **S3 link URL:** Enter:
   ```
   https://s3.ap-northeast-1.amazonaws.com/cowell-uploads-john1985-123/layers/pypdfium2-layer.zip
   ```
   (Replace `ap-northeast-1` with your region, and `john1985-123` with your bucket suffix)

10. **Compatible runtimes:** Select **Python 3.12**
11. **Architecture:** Select **x86_64**
12. Click **"Create"**

**Attach the layer to your function:**

1. Go back to your Lambda function (`cowell-ocr-backend`)
2. Scroll down to **"Layers"** section
3. Click **"Add a layer"**

   ```
   ┌──────────────────────────────────────────────┐
   │ Layers (0)                                    │
   │ [Add a layer]                                 │
   └──────────────────────────────────────────────┘
   ```

4. **Layer source:** Select **"Custom layers"**
5. **Custom layer:** Select `pypdfium2-pillow` from the dropdown
6. **Version:** 1
7. Click **"Add"**

> ✅ The Linux-native libraries are now available to your Lambda function.

> 💡 **If CloudShell isn't available** in your region, or you can't install pypdfium2, there's a simple fallback: create the ZIP on an **Amazon Linux EC2 instance** (free tier), or use the manual method of uploading the layer ZIP to S3 via the console.

---

## 6. Set Up API Gateway

API Gateway gives Lambda an HTTP endpoint so your frontend can call the backend.

### Step 6.1 — Open API Gateway

1. In the search bar, type `API Gateway`
2. Click **"API Gateway"** (under Services)

### Step 6.2 — Create a REST API

1. Click the **"Create API"** button

   ```
   ┌─────────────────────────────────────────────────┐
   │   REST API                                       │
   │   [Build]          ← Click this "Build" button   │
   │                                                  │
   │   HTTP API (Newer, faster)                       │
   │   [Build]                                        │
   │                                                  │
   │   WebSocket API                                  │
   │   [Build]                                        │
   └─────────────────────────────────────────────────┘
   ```

2. Under **"REST API"** (not HTTP API), click **"Build"**
3. **Choose the protocol:** Select **"REST"** (already selected)
4. **Create new API:** Select **"New API"**
5. **API name:** Type `cowell-ocr-api`
6. **Endpoint Type:** Select **"Regional"** (not Edge-optimized)
7. Click the orange **"Create API"** button

### Step 6.3 — Create a Proxy Resource

We need a catch-all route (`/{proxy+}`) that forwards every request to Lambda.

1. In the left sidebar, you'll see a resource tree:

   ```
   ┌──────────────────────────────────────────────┐
   │ Resources                                     │
   │                                              │
   │   /                                          │
   │                                              │
   └──────────────────────────────────────────────┘
   ```

2. Click on **"/"** (the root)
3. Click the blue **"Actions"** dropdown button
4. Click **"Create Resource"**

   ```
   ┌──────────────────────────────────────────────┐
   │ Create Resource                               │
   │                                              │
   │ ☑ Configure as proxy resource                 │
   │                                              │
   │ Resource Path: /{proxy+}                     │
   │                                              │
   │ [Create Resource]                            │
   └──────────────────────────────────────────────┘
   ```

5. **Check** the box that says **"Configure as proxy resource"**
   - The Resource Path will auto-fill to `/{proxy+}`
6. Click **"Create Resource"**

### Step 6.4 — Connect the Proxy to Lambda

Now we tell API Gateway: "when someone hits this URL, run the Lambda function."

1. With `ANY` / `{proxy+}` selected, click **"Actions"** → **"Create Method"**

   ```
   ┌──────────────────────────────────────────────┐
   │ /{proxy+}                                     │
   │   ANY                                         │
   │                                               │
   │ [Create Method]                               │
   └──────────────────────────────────────────────┘
   ```

2. A dropdown appears — select **`ANY`** (it might already be selected) and click the checkmark ✓

   ```
   ┌──────────────────────────────────────────────┐
   │ /{proxy+} - ANY - Setup                       │
   │                                              │
   │ Integration type: ● Lambda Function ○ HTTP   │
   │                                               │
   │ ☑ Use Lambda Proxy integration               │
   │                                               │
   │ Lambda Region: ap-northeast-1                │
   │ Lambda Function: cowell-ocr-backend           │
   │                                               │
   │ [Save]                                        │
   └──────────────────────────────────────────────┘
   ```

3. **Integration type:** Make sure **"Lambda Function"** is selected
4. **Check** the box **"Use Lambda Proxy integration"**
   - ⚠️ This is **very important** — without it, the request details (headers, body, path) won't reach your FastAPI app
5. **Lambda Region:** Your region (e.g., `ap-northeast-1`)
6. **Lambda Function:** Start typing `cowell-ocr-backend` and select it from the dropdown
7. Click **"Save"**
8. A popup says "You are about to give API Gateway permission to invoke your Lambda function" — Click **"OK"**

### Step 6.5 — Create the Root Method Too

We need a method for the root path (`/`) as well, for the health check (`/api/health`).

1. Click on **"/"** in the resource tree
2. Click **"Actions"** → **"Create Method"**
3. Select **`ANY`** → click checkmark ✓
4. Same settings: Lambda Function, check "Use Lambda Proxy integration"
5. Select `cowell-ocr-backend`
6. Click **"Save"** → **"OK"**

### Step 6.6 — Deploy the API

1. Click the **"Actions"** dropdown button
2. Click **"Deploy API"**

   ```
   ┌──────────────────────────────────────────────┐
   │ Deploy API                                    │
   │                                              │
   │ Deployment stage: [New Stage]                 │
   │ Stage name: [prod]                           │
   │                                              │
   │ [Deploy]                                      │
   └──────────────────────────────────────────────┘
   ```

3. **Deployment stage:** Select **`[New Stage]`**
4. **Stage name:** Type `prod`
5. Click **"Deploy"**

### Step 6.7 — Copy the Invoke URL

After deployment, you'll see something like:

```
Invoke URL: https://abc123def.execute-api.ap-northeast-1.amazonaws.com/prod
```

**COPY THIS URL.** This is your **Backend API URL**. Write it down somewhere — you'll need it several times.

> It looks like: `https://xxxxxxxxxx.execute-api.your-region.amazonaws.com/prod`

### Step 6.8 — Test the API

Open a new browser tab and visit:

```
https://abc123def.execute-api.ap-northeast-1.amazonaws.com/prod/api/health
```

(Replace with your actual URL.)

If everything works, you should see:
```json
{"status": "ok", "model": "gemini-2.5-flash"}
```

#### If you get an error:

Don't panic. Common issues at this stage:

**Error: `{"message": "Internal server error"}`**
1. Go to Lambda → Click your function → **"Monitor"** tab → **"View CloudWatch logs"**
2. Click the latest log stream
3. Look for `ERROR` or `Traceback` — that's your error.

**Most likely causes:**
- `GEMINI_API_KEY` missing (forgot to add env var)
- pypdfium2 not working (need the Lambda Layer from Step 5.8)
- ZIP file missing some dependencies

> ✅ API Gateway is live! Your backend can be reached at the Invoke URL.

---

## 7. Deploy the Frontend (React)

### Step 7.1 — Update the Frontend Config

Open `frontend/src/api/client.ts` again and find the `BASE_URL` line.

Change it to your API Gateway URL:

```typescript
// Before (local dev):
const BASE_URL = "/api";

// After (production):
const BASE_URL = "https://abc123def.execute-api.ap-northeast-1.amazonaws.com/prod/api";
```

Replace the URL with your actual API Gateway Invoke URL.

### Step 7.2 — Rebuild the Frontend

Open Git Bash:

```bash
cd frontend
npm run build
```

> If WebStorm/VSCode says `npm: command not found`, open a **new** Git Bash window.

### Step 7.3 — Upload Files to S3

1. Go back to the S3 page in AWS Console
2. Click on your **frontend bucket**: `cowell-frontend-john1985-123`
3. Click the **"Upload"** button

   ```
   ┌──────────────────────────────────────────────┐
   │   │  Upload  │  Create folder  │  Download   │
   └──────────────────────────────────────────────┘
   ```

4. Click **"Add files"** — navigate to `frontend/dist/` and select ALL files
   - Or just drag-and-drop the entire `dist` folder contents
5. Click the orange **"Upload"** button

   > ⏳ Wait for the upload to finish. You should see "Upload succeeded: 15 files" or similar.

### Step 7.4 — Make the Bucket Public

The files need to be readable by anyone visiting your website.

1. Click on your frontend bucket name
2. Click the **"Permissions"** tab

   ```
   ┌──────────────────────────────────────────────┐
   │ Properties  │  Permissions  │  Metrics       │
   └──────────────────────────────────────────────┘
   ```

3. Scroll to **"Block public access (bucket settings)"**
4. Click **"Edit"**

   ```
   ┌──────────────────────────────────────────────┐
   │ Edit Block public access settings             │
   │                                              │
   │ ☐ Block _all_ public access                  │
   │   (uncheck this box)                         │
   │                                              │
   │ ☑ Block public access to buckets and         │
   │    objects granted through new access         │
   │    control lists (ACLs)                       │
   │   (leave checked)                            │
   │                                              │
   │ [Save changes]                                │
   └──────────────────────────────────────────────┘
   ```

5. **Uncheck** the first box: "Block _all_ public access"
6. Leave the other boxes checked
7. Click **"Save changes"**
8. In the popup, type `confirm` and click **"Confirm"**

### Step 7.5 — Add a Bucket Policy

1. Still on the **"Permissions"** tab, scroll to **"Bucket policy"**
2. Click **"Edit"**

   ```
   ┌──────────────────────────────────────────────┐
   │ Bucket policy                                 │
   │ [Edit]                                        │
   │ ┌──────────────────────────────────────────┐  │
   │ │ No bucket policy                         │  │
   │ └──────────────────────────────────────────┘  │
   └──────────────────────────────────────────────┘
   ```

3. In the editor, paste this (replace `cowell-frontend-john1985-123` with YOUR actual bucket name):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::cowell-frontend-john1985-123/*"
        }
    ]
}
```

4. Click **"Save changes"**

### Step 7.6 — Enable Static Website Hosting

1. Click the **"Properties"** tab

2. Scroll down to **"Static website hosting"**

   ```
   ┌──────────────────────────────────────────────┐
   │ Static website hosting                        │
   │ [Edit]                                        │
   │ Disabled                                      │
   └──────────────────────────────────────────────┘
   ```

3. Click **"Edit"**
4. Select **"Enable"**

   ```
   ┌──────────────────────────────────────────────┐
   │ Static website hosting                        │
   │                                              │
   │ ● Enable                                     │
   │ ○ Disabled                                   │
   │                                              │
   │ Index document: [index.html]                 │
   │ Error document: [index.html]  ← IMPORTANT!  │
   │                                              │
   │ [Save changes]                                │
   └──────────────────────────────────────────────┘
   ```

5. **Index document:** Type `index.html`
6. **Error document:** Type `index.html`
   - > 🧠 Why `index.html` for errors? Because React uses client-side routing. When you visit `/process/abc123`, S3 looks for a file called `abc123` and gets a 404. By serving `index.html` instead, React Router handles the URL correctly.
7. Click **"Save changes"**

8. After saving, you'll see an **Endpoint URL** like:
   ```
   http://cowell-frontend-john1985-123.s3-website-ap-northeast-1.amazonaws.com
   ```

9. **Click that URL** — your frontend should load! (The page might look plain if API calls aren't working yet — that's OK.)

> ✅ Your frontend is now publicly accessible!

---

## 8. Set Up CloudFront (CDN + HTTPS)

CloudFront gives you:
- ✅ **HTTPS** (browsers block some features on non-HTTPS sites)
- ✅ **Faster global loading** (serves files from edge locations near the user)
- ✅ **Better security** (hides your S3 bucket from direct access)

### Step 8.1 — Open CloudFront

1. In the search bar, type `CloudFront`
2. Click **"CloudFront"** (under Services)

### Step 8.2 — Create a Distribution

1. Click the orange **"Create distribution"** button

### Step 8.3 — Configure Origin

**Origin section:**

1. **Origin domain:** Click the dropdown — select your **S3 bucket endpoint**
   - Look for: `cowell-frontend-john1985-123.s3.ap-northeast-1.amazonaws.com`
   - ⚠️ Don't select the one that ends with `s3-website-ap-northeast-1.amazonaws.com` — select the standard S3 endpoint

2. **Origin access:** Select **"Origin access control settings (recommended)"**
   - Click **"Create control setting"** (a small link below)

   ```
   ┌──────────────────────────────────────────────┐
   │ Create origin access control                 │
   │                                              │
   │ Name: cowell-frontend-oac                    │
   │                                              │
   │ Signing behavior: ● Sign requests (recommend)│
   │                                              │
   │ [Create]                                      │
   └──────────────────────────────────────────────┘
   ```

   - **Name:** `cowell-frontend-oac`
   - **Signing behavior:** Select **"Sign requests (recommended)"**
   - Click **"Create"**

### Step 8.4 — Default Cache Behavior Settings

1. **Viewer protocol policy:** Select **"Redirect HTTP to HTTPS"**
2. **Allowed HTTP methods:** Select **"GET, HEAD, OPTIONS"** (frontend is read-only)
3. **Cache policy:** Leave as default (`CachingOptimized`)
4. **Compress objects automatically:** Check **Yes** (CloudFront will gzip your files)

### Step 8.5 — Distribution Settings

1. **Default root object:** Type `index.html`
2. **Price class:** Select **"Use only North America and Europe"** (cheapest option)
   - > 💡 If your users are all in Japan, select this same option — closest edge is in Europe which is still fine.
   - > For fastest Japan performance, use "All edge locations" but it costs more.
3. **Custom error responses:** We'll add this in Step 8.7
4. Click **"Create distribution"**

### Step 8.6 — Update Bucket Policy for CloudFront

After creating the distribution, you'll see a yellow warning banner:

```
┌──────────────────────────────────────────────┐
│ ⚠️ Origin access control requires that the    │
│ S3 bucket policy grants CloudFront access.   │
│                                              │
│ [Copy policy]  [Back to distribution detail] │
└──────────────────────────────────────────────┘
```

1. Click **"Copy policy"** — it copies a JSON policy to your clipboard
2. Click the link that says **"S3 bucket"** or go back to S3 Console
3. Click your **frontend bucket** → **Permissions** tab → **Bucket policy** → **Edit**
4. **Replace** the existing policy with what you copied
5. Click **"Save changes"**

### Step 8.7 — Handle SPA Routing (Error Pages)

React Router needs a special trick: when CloudFront can't find a file, it should serve `index.html` instead of showing a 403/404 error.

1. Go to CloudFront → Click your distribution
2. Click the **"Error pages"** tab

   ```
   ┌──────────────────────────────────────────────┐
   │ Error pages                                   │
   │ [Create custom error response]                │
   └──────────────────────────────────────────────┘
   ```

3. Click **"Create custom error response"**
4. **HTTP error code:** Select **`403: Forbidden`**
5. **Customize error response:** Select **"Yes"**

   ```
   ┌──────────────────────────────────────────────┐
   │ Customize error response: ● Yes ○ No         │
   │                                              │
   │ Response page path: [/index.html]            │
   │                                              │
   │ HTTP Response Code: [200: OK]                │
   └──────────────────────────────────────────────┘
   ```

6. **Response page path:** Type `/index.html`
7. **HTTP Response Code:** Select **`200: OK`**
8. Click **"Create"**

9. Repeat for the second error:
   - Click **"Create custom error response"** again
   - **HTTP error code:** **`404: Not Found`**
   - **Customize:** Yes
   - **Response page path:** `/index.html`
   - **HTTP Response Code:** **`200: OK`**
   - Click **"Create"**

### Step 8.8 — Update CORS in Backend

Now we need to tell the backend to accept requests from our CloudFront URL.

1. Open `backend/app/main.py` in a text editor
2. Find the CORS section:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    ...
)
```

3. Add your CloudFront URL:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://d1234abcdef.cloudfront.net",  # ← YOUR CloudFront URL
    ],
    ...
)
```

4. **Rebuild the ZIP:**

```bash
cd backend
mkdir -p build_temp
pip install -t build_temp/ mangum boto3 fastapi uvicorn python-multipart google-genai gspread google-auth google-auth-oauthlib google-api-python-client pypdfium2 Pillow pydantic-settings httpx python-dotenv
cp -r app build_temp/app
cp lambda_handler.py build_temp/
rm -rf build_temp/__pycache__
cd build_temp
zip -rq ../cowell-lambda.zip .
cd ..
rm -rf build_temp
```

5. **Re-upload to Lambda:**
   - Go to Lambda → Your function
   - In "Code source", click **"Upload from"** → **".zip file"**
   - Select the new `cowell-lambda.zip`
   - Click **"Save"**

### Step 8.9 — Wait for CloudFront Deployment

CloudFront takes **5-15 minutes** to deploy. You'll see:

```
┌──────────────────────────────────────────────┐
│ Status: In Progress                           │
│ Last Modified: 2026-07-18                    │
└──────────────────────────────────────────────┘
```

Wait until the status changes to **"Deployed"** (refresh the page every few minutes).

### Step 8.10 — Get Your CloudFront URL

1. Click on your distribution
2. Copy the **Distribution domain name** — it looks like:
   ```
   d1234abcdef.cloudfront.net
   ```
3. Open it in your browser — your app should load!

> ✅ Your site is live at `https://d1234abcdef.cloudfront.net` with HTTPS!

---

## 9. Test Everything

### 9.1 — Health Check

Visit this URL in your browser (replace with your API URL):

```
https://abc123def.execute-api.ap-northeast-1.amazonaws.com/prod/api/health
```

Expected:
```json
{"status": "ok", "model": "gemini-2.5-flash"}
```

### 9.2 — Full App Test

1. Open your CloudFront URL: `https://d1234abcdef.cloudfront.net`
2. You should see the **Upload Page** with two upload areas
3. Upload a survey PDF (you can test with the sample file in `Requiremnts/sample input output/`)
4. Upload a photo (optional)
5. Click **"Run OCR"** — wait for processing
6. The **Edit Page** should show the extracted rows
7. Click **"Register to Google Sheet"**
8. Check your Google Drive for a new spreadsheet!

### 9.3 — Check Logs (If Something Fails)

1. Go to Lambda → Your function → **"Monitor"** tab
2. Click **"View CloudWatch logs"**
3. Click the latest log stream
4. Look for `ERROR` or `Traceback`

---

## 10. Cost Breakdown

### First 12 Months (Free Tier)

| Service | Free Tier Limit | Our Usage | Cost |
|---------|----------------|-----------|------|
| **Lambda** | 1M requests/month + 400,000 GB-seconds | ~100 req/mo, 512MB, ~30s avg | **$0** |
| **API Gateway** | 1M API calls/month | ~1,000 calls/mo | **$0** |
| **S3** | 5GB storage, 20K GET, 2K PUT | ~100MB | **$0** |
| **CloudFront** | 1TB transfer/month, 10M requests | ~100MB | **$0** |
| **CloudWatch** | 5GB logs/month | ~50MB | **$0** |

### After Free Tier (Monthly Estimate)

| Service | Monthly Cost |
|---------|-------------|
| Lambda (very low usage) | ~$0.10 |
| API Gateway | ~$0.05 |
| S3 | ~$0.01 |
| CloudFront | ~$0.05 |
| **TOTAL** | **~$0.21/month** |

---

## 11. Troubleshooting

### "Internal Server Error" (blank error page)

**Most likely causes:**

| Cause | How to fix |
|-------|-----------|
| Missing `GEMINI_API_KEY` | Go to Lambda → Environment variables → Add it |
| pypdfium2 layer not attached | Go to Lambda → Layers → Add the layer from Step 5.8 |
| OAuth token expired | Run `auth_oauth.py` locally, upload new token to S3 bucket |
| Lambda timeout | Go to Lambda → General config → Increase timeout to 5 min |
| Lambda out of memory | Go to Lambda → General config → Set memory to 512MB or 1024MB |

**How to diagnose:** Lambda → Monitor → View CloudWatch logs → Click latest log

### CORS Error in Browser

**Error message:**
```
Access to fetch at 'https://api-url/prod/api/upload' 
from origin 'https://d1234abc.cloudfront.net' has been blocked by CORS policy
```

**Fix:** Add your CloudFront URL to the `allow_origins` list in `backend/app/main.py`, re-ZIP, and re-upload to Lambda.

### 403 Forbidden on Frontend

**Cause:** S3 bucket policy not set correctly, or CloudFront can't access S3.

**Fix:**
1. Check S3 bucket policy (Step 7.5)
2. Check CloudFront origin access settings (Step 8.6)
3. Make sure you copied the policy from the yellow warning in CloudFront

### App Opens but Looks Broken (No CSS/JS)

**Cause:** Files weren't uploaded to S3, or SPA error page not configured.

**Fix:**
1. Re-upload the `frontend/dist` contents to S3 (Step 7.3)
2. Check that error document is set to `index.html` (Step 7.6)
3. Check that CloudFront error pages are configured (Step 8.7)

### OAuth Token Expired

Google OAuth tokens expire after a while (can be days to months).

**Fix:**
1. Open Git Bash on your computer
2. Go to the backend folder:
   ```bash
   cd backend
   python auth_oauth.py
   ```
3. Follow the browser prompts to re-authorize
4. Upload the new `token.json` to your S3 token bucket:
   - S3 Console → Your token bucket → `credentials/token.json` → **Upload** → Replace
5. Lambda will download the fresh token on the next request

### Upload Fails for Large Files (Over 10MB)

**Problem:** API Gateway has a 10MB payload limit.

**Solutions:**
- Split large PDFs into smaller files (under 10MB each)
- Or use the S3 presigned URL method (more advanced — not covered in this guide)

### Lambda Cold Start is Slow

First request after inactivity takes 5-10 seconds.

**Why:** Python + large libraries (pypdfium2, Pillow) take time to load.

**Solutions:**
- **Free:** Just accept the 5s delay on cold start — subsequent requests are instant
- **Paid (~$0.50/mo):** Set **reserved concurrency** to 1 (keeps one instance warm)

---

## 12. Cleanup (To Avoid Charges)

When you're done or want to start over, delete everything.

### Step 12.1 — Delete CloudFront Distribution

1. CloudFront Console → Click your distribution
2. Click **"Disable"** (top right)
3. Wait for **"Deployed"** status (5-10 min)
4. Click **"Delete"** (appears after disabled)

### Step 12.2 — Empty and Delete S3 Buckets

1. S3 Console → Click each bucket
2. Click **"Empty"** button
   - Type `permanently delete` and click **"Empty"**
3. Click **"Delete"** button
   - Type the bucket name and click **"Delete bucket"**

**Delete order doesn't matter.** Just do all 4 buckets.

### Step 12.3 — Delete API Gateway

1. API Gateway Console → Click your API (`cowell-ocr-api`)
2. Click **"Actions"** → **"Delete API"**
3. Type `confirm` → Click **"Delete"**

### Step 12.4 — Delete Lambda Function

1. Lambda Console → Select `cowell-ocr-backend`
2. Click **"Actions"** → **"Delete"**
3. Type `confirm` → Click **"Delete"**

### Step 12.5 — Delete Lambda Layer

1. Lambda Console → Left menu → **"Layers"**
2. Select `pypdfium2-pillow`
3. Click **"Delete"** → **"Delete"**

### Step 12.6 — Delete CloudWatch Logs

1. Search for **"CloudWatch"** → Click it
2. Left menu → **"Log groups"**
3. Check the box next to `/aws/lambda/cowell-ocr-backend`
4. Click **"Actions"** → **"Delete log group"**
5. Type `confirm` → **"Delete"**

> ✅ All resources deleted. You won't be charged.

---

## Appendix A: Checklist

Before celebrating, verify everything:

- [ ] **Health check works:** `{API_URL}/api/health` returns `{"status":"ok"}`
- [ ] **Frontend loads:** CloudFront URL shows the upload page
- [ ] **Upload works:** Can upload a PDF
- [ ] **OCR works:** Processing completes showing extracted rows
- [ ] **Register works:** Google Sheet is created with data
- [ ] **No CORS errors:** Browser console is clean
- [ ] **HTTPS works:** Site loads on `https://`
- [ ] **Token not expired:** Registration doesn't fail with auth errors

## Appendix B: Quick Reference

```
═══════════════════════════════════════════════════════
                  QUICK REFERENCE
═══════════════════════════════════════════════════════

S3 Buckets (4 total):
  • cowell-uploads-{suffix}     — PDFs & photos (private)
  • cowell-sessions-{suffix}    — Session JSON (private)
  • cowell-token-{suffix}       — OAuth token.json (private)
  • cowell-frontend-{suffix}    — React static files (public)

Lambda:
  • Function name: cowell-ocr-backend
  • Runtime: Python 3.12
  • Handler: lambda_handler.handler
  • Memory: 512MB | Timeout: 5 min

API Gateway:
  • Type: REST API (Lambda proxy)
  • Stage: prod
  • Proxy: /{proxy+} (ANY) + / (ANY)

CloudFront:
  • Origin: S3 bucket (not website endpoint)
  • OAC: Signed requests
  • Error pages: 403→/index.html(200), 404→/index.html(200)

Lambda Environment Variables:
  GEMINI_API_KEY=
  S3_BUCKET_UPLOADS=cowell-uploads-{suffix}
  S3_BUCKET_SESSIONS=cowell-sessions-{suffix}
  S3_BUCKET_TOKEN=cowell-token-{suffix}
  S3_TOKEN_KEY=credentials/token.json

Estimated Cost: <$0.21/month ✅
═══════════════════════════════════════════════════════
```
