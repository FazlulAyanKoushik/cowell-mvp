"""
Quick test script to verify Google service account credentials.

Usage:
    cd backend
    uv run python test_service_account.py
"""

import json
from pathlib import Path

SA_PATH = Path("credentials/service_account.json")


def main():
    # 1. Check file exists
    if not SA_PATH.exists():
        print(f"❌ File not found: {SA_PATH}")
        print("   Place your service_account.json in backend/credentials/")
        return

    print(f"✅ Found: {SA_PATH}")

    # 2. Check JSON structure
    with open(SA_PATH) as f:
        sa = json.load(f)

    required_keys = ["type", "project_id", "private_key", "client_email"]
    for key in required_keys:
        if key in sa:
            print(f"  ✅ {key}: {sa[key][:50]}...")
        else:
            print(f"  ❌ Missing: {key}")

    # 3. Test Sheets API
    print("\n--- Testing Sheets API ---")
    try:
        import gspread
        gc = gspread.service_account(filename=str(SA_PATH))
        # Create a test sheet (will be deleted)
        sheet = gc.create("cowell-ocr-test-delete-me")
        print(f"  ✅ Created test sheet: {sheet.url}")
        # Clean up
        gc.del_spreadsheet(sheet.id)
        print("  ✅ Deleted test sheet")
    except Exception as e:
        print(f"  ❌ Sheets API error: {e}")

    # 4. Test Drive API
    print("\n--- Testing Drive API ---")
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(
            str(SA_PATH),
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        service = build("drive", "v3", credentials=creds)

        # Check storage quota
        about = service.about().get(fields="storageQuota").execute()
        quota = about.get("storageQuota", {})
        used = int(quota.get("usage", 0))
        limit = int(quota.get("limit", 0))
        print(f"  Storage used: {used / (1024**2):.1f} MB")
        print(f"  Storage limit: {limit / (1024**2):.1f} MB")
        if limit > 0 and used >= limit:
            print("  ❌ Drive storage FULL — cannot upload photos")
            print("     Fix: Delete files from the service account's Drive,")
            print("     or use a shared folder approach instead")
        else:
            print("  ✅ Drive storage OK")
    except Exception as e:
        print(f"  ❌ Drive API error: {e}")

    print("\n--- Done ---")


if __name__ == "__main__":
    main()
