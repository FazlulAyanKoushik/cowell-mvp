"""
One-time OAuth 2.0 authorization script.

Run this once to authorize the backend to act on behalf of your personal
Google account. It will:
  1. Open a browser window for you to log in
  2. Ask you to grant permission to create/edit Google Sheets and Drive files
  3. Save a token.json file locally that the backend reuses

Prerequisites:
  - Create an OAuth 2.0 Client ID in Google Cloud Console
    (Application type: Desktop app)
  - Put the Client ID and Client Secret in your .env file:
        GOOGLE_CLIENT_ID=...
        GOOGLE_CLIENT_SECRET=...

Usage:
  cd backend
  python auth_oauth.py
"""

import json
import logging
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Read Client ID / Secret from .env
from dotenv import load_dotenv
import os
load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip().strip('"').strip("'")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip().strip('"').strip("'")

if not CLIENT_ID or not CLIENT_SECRET:
    raise SystemExit(
        "❌ GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env\n"
        "   Get them from: https://console.cloud.google.com/apis/credentials"
    )

# Scopes — what the backend can do on your behalf
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

TOKEN_PATH = Path(__file__).resolve().parent / "credentials" / "token.json"
TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)


def main():
    # Build client config from .env values
    client_config = {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["http://localhost"],
        }
    }

    log.info("🌐 Opening browser for Google login...")
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    # run_local_server opens a browser and listens on localhost
    creds = flow.run_local_server(port=0)

    # Save token for the backend to reuse
    TOKEN_PATH.write_text(creds.to_json())
    log.info("✅ Saved token to: %s", TOKEN_PATH)

    # Show what we got
    print()
    print("=" * 60)
    print("✅ Authorization successful!")
    print("=" * 60)
    print(f"   Token file: {TOKEN_PATH}")
    print()
    print("The backend will use this token to create Google Sheets")
    print("on your behalf. Delete this file to re-authorize.")
    print("=" * 60)


if __name__ == "__main__":
    main()
