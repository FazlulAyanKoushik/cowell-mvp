"""
Test script: Create a Google Sheet programmatically using OAuth 2.0.

Uses your personal Google account (ayon15-7527@diu.edu.bd) via the
refresh token saved at backend/credentials/token.json, so the sheet
gets created in your Drive (which has storage quota).

Prerequisites:
1. Run `python auth_oauth.py` once to authorize and save token.json
2. The token must have these scopes:
   - https://www.googleapis.com/auth/spreadsheets
   - https://www.googleapis.com/auth/drive.file
"""

import logging
from pathlib import Path

import gspread
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ── Configuration ──────────────────────────────────────────────
TOKEN_PATH = Path(__file__).resolve().parent / "credentials" / "token.json"
FOLDER_ID = "1wRBVbj9PyC51Y6Mt3Fx0iuAkHRu93-r-"
# ───────────────────────────────────────────────────────────────

if not TOKEN_PATH.exists():
    raise SystemExit(
        f"❌ Token not found: {TOKEN_PATH}\n"
        "   Run `python auth_oauth.py` first to authorize."
    )

creds = Credentials.from_authorized_user_file(str(TOKEN_PATH))
log.info("Credentials loaded for: %s", creds.client_id)

# Refresh if expired (uses the refresh token from token.json)
if creds.expired and creds.refresh_token:
    from google.auth.transport.requests import Request
    creds.refresh(Request())
    TOKEN_PATH.write_text(creds.to_json())
    log.info("Token refreshed and re-saved")

# ── Step 1: Create sheet inside the shared folder ─────────────
drive = build("drive", "v3", credentials=creds)
file_metadata = {
    "name": "Cowell OCR Test - プログラム作成",
    "parents": [FOLDER_ID],
    "mimeType": "application/vnd.google-apps.spreadsheet",
}
drive_file = (
    drive.files()
    .create(body=file_metadata, fields="id,webViewLink")
    .execute()
)

sheet_id = drive_file["id"]
sheet_url = drive_file["webViewLink"]
log.info("✅ Sheet created: %s", sheet_url)

# ── Step 2: Write test data via gspread ───────────────────────
client = gspread.authorize(creds)
sheet = client.open_by_key(sheet_id)
ws = sheet.sheet1
ws.update_title("テストデータ")

test_data = [
    ["フロア", "設置場所", "器具品番", "既設商品名", "写真", "数量", "備考"],
    ["1F", "ロビー", "FR-42540-RS", "φ100DL E17 (L)", "", "36", "調光"],
    ["1F", "廊下", "88DJ-81YO-1", "FL40W (N) 8灯式", "", "5", ""],
    ["2F", "トイレ", "ADN950272ZA", "ダウンライト 12W", "", "12", "防水"],
    ["3F", "職員室", "FR-42540-RS", "φ100DL E17 (L)", "", "8", ""],
]

ws.update("A1", test_data)

# Format header
ws.format("A1:G1", {
    "textFormat": {"bold": True},
    "backgroundColor": {"red": 0.9, "green": 0.93, "blue": 0.97},
})

log.info("✅ Written %d rows of test data", len(test_data))
print(f"\n📊 Open it: {sheet_url}")
print(f"   Sheet ID: {sheet_id}")