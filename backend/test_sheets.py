"""
Test Google Sheets integration — verifies service account can create and populate sheets.

Usage:
    cd backend
    uv run python test_sheets.py
"""

import json
from pathlib import Path

SA_PATH = Path("credentials/service_account.json")


def main():
    print("=" * 60)
    print("Google Sheets Integration Test")
    print("=" * 60)

    # 1. Check service account file
    if not SA_PATH.exists():
        print(f"❌ File not found: {SA_PATH}")
        print("   Place your service_account.json in backend/credentials/")
        return

    with open(SA_PATH) as f:
        sa = json.load(f)

    print(f"\n📧 Service account email: {sa.get('client_email', 'N/A')}")
    print(f"📁 Project ID: {sa.get('project_id', 'N/A')}")

    # 2. Test Sheets API — create a sheet
    print("\n--- Test 1: Create Google Sheet ---")
    try:
        import gspread
        gc = gspread.service_account(filename=str(SA_PATH))

        sheet = gc.create("Cowell OCR Test - DELETE ME")
        print(f"✅ Sheet created: {sheet.url}")

        # Populate with test data
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

        print(f"✅ Written {len(test_data)} rows (1 header + {len(test_data)-1} data)")
        print(f"📊 Open it: {sheet.url}")

        # 3. Test Drive upload (may fail if quota exceeded)
        print("\n--- Test 2: Drive Photo Upload ---")
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            creds = service_account.Credentials.from_service_account_file(
                str(SA_PATH),
                scopes=["https://www.googleapis.com/auth/drive"],
            )
            drive = build("drive", "v3", credentials=creds)

            # Check quota
            about = drive.about().get(fields="storageQuota").execute()
            quota = about.get("storageQuota", {})
            used = int(quota.get("usage", 0))
            limit = int(quota.get("limit", 0))
            print(f"  Storage: {used / (1024**2):.1f} MB / {limit / (1024**2):.1f} MB")

            if used >= limit:
                print("  ❌ Drive storage FULL — photo upload will fail")
                print("  💡 Fix: Go to drive.google.com and delete files")
            else:
                print("  ✅ Drive storage OK — photo upload should work")

        except Exception as e:
            print(f"  ⚠️ Drive check failed: {e}")

        # Clean up
        print("\n--- Cleanup ---")
        gc.del_spreadsheet(sheet.id)
        print("✅ Test sheet deleted")

    except gspread.exceptions.APIError as e:
        print(f"❌ Sheets API error: {e}")
        print("\nCommon fixes:")
        print("  1. Enable Google Sheets API in Cloud Console")
        print("  2. Enable Google Drive API in Cloud Console")
        print("  3. Check service account has correct permissions")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
