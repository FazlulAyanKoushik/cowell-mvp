"""
Lambda entry point for Cowell OCR API.

FastAPI app wrapped with Mangum adapter for AWS Lambda + API Gateway.
Downloads the Google OAuth token from S3 on cold start.

Environment variables (set in Lambda configuration):
    GEMINI_API_KEY                  — Google Gemini API key
    S3_BUCKET_UPLOADS               — S3 bucket for temp file uploads
    S3_BUCKET_SESSIONS              — S3 bucket for session data (JSON)
    S3_BUCKET_TOKEN                 — S3 bucket containing the OAuth token.json
    S3_TOKEN_KEY                    — S3 object key for token.json (default: credentials/token.json)
    GOOGLE_OAUTH_TARGET_FOLDER_ID   — (optional) Google Drive folder ID for sheets/photos
"""

import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("cowell.lambda")

# ── Read configuration from environment ─────────────────────────
S3_BUCKET_TOKEN = os.environ.get("S3_BUCKET_TOKEN", "")
S3_TOKEN_KEY = os.environ.get("S3_TOKEN_KEY", "credentials/token.json")

# ── Download OAuth token from S3 on cold start ──────────────────
# Lambda /tmp is ephemeral storage, unique per instance.
token_dir = Path("/tmp/credentials")
token_dir.mkdir(parents=True, exist_ok=True)
token_path = token_dir / "token.json"

if S3_BUCKET_TOKEN and not token_path.exists():
    try:
        import boto3  # noqa: E402 — delayed import for clarity

        s3 = boto3.client("s3")
        s3.download_file(S3_BUCKET_TOKEN, S3_TOKEN_KEY, str(token_path))
        log.info("Downloaded OAuth token from s3://%s/%s", S3_BUCKET_TOKEN, S3_TOKEN_KEY)
    except Exception as exc:
        log.error("Failed to download OAuth token: %s", exc)
        log.warning(
            "Continuing without OAuth token — /api/register will fail. "
            "Make sure GOOGLE_OAUTH_TOKEN_PATH is set correctly."
        )
elif not S3_BUCKET_TOKEN:
    log.warning(
        "S3_BUCKET_TOKEN not set. Attempting to use local token at GOOGLE_OAUTH_TOKEN_PATH."
    )
else:
    log.info("OAuth token already present at %s (reusing)", token_path)

# Override the token path so config.py finds it
os.environ["GOOGLE_OAUTH_TOKEN_PATH"] = str(token_path)

# ── Now import the app (config runs at import time) ──────────────
# Pydantic-settings reads env vars when Settings() is constructed.
# We've set GOOGLE_OAUTH_TOKEN_PATH above, so config.py picks it up.
try:
    from app.main import app  # noqa: E402

    log.info("FastAPI app imported successfully")
except Exception as exc:
    log.critical("Failed to import FastAPI app: %s", exc, exc_info=True)
    raise

# ── Create the Mangum handler ───────────────────────────────────
try:
    from mangum import Mangum  # noqa: E402

    handler = Mangum(app, lifespan="off")
    log.info("Mangum handler created")
except ImportError:
    log.critical(
        "mangum is not installed. Add it to pyproject.toml: 'mangum>=0.17.0'"
    )
    sys.exit(1)


# ── Local development entry point ───────────────────────────────
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    log.info("Starting local dev server on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
