"""Google Drive integration — upload photos and make them accessible."""

from __future__ import annotations

import logging
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from ..config import settings

logger = logging.getLogger("cowell.sheets")

# Scopes needed for Drive upload
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]


def _get_credentials():
    """Load service account credentials."""
    sa_path = settings.google_service_account_path
    if not Path(sa_path).exists():
        raise FileNotFoundError(
            f"Service account file not found: {sa_path}\n"
            "Download it from Google Cloud Console and place it at the configured path."
        )
    return service_account.Credentials.from_service_account_file(
        sa_path, scopes=SCOPES
    )


def _get_drive_service():
    """Get Google Drive API service."""
    creds = _get_credentials()
    return build("drive", "v3", credentials=creds)


def upload_photo(file_path: str, filename: str) -> str:
    """Upload a photo to Google Drive and return the file ID.

    The file is made publicly viewable so it can be referenced
    via IMAGE() formula in Google Sheets.

    Returns empty string on failure (quota exceeded, etc.) so
    the sheet creation can continue without photos.
    """
    service = _get_drive_service()

    file_metadata = {
        "name": filename,
        "parents": [],  # Root of service account's Drive
    }

    media = MediaFileUpload(
        file_path,
        mimetype="image/jpeg",
        resumable=True,
    )

    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
        ).execute()
    except Exception as e:
        logger.warning("⚠️ Failed to upload photo %s: %s", filename, e)
        return ""

    file_id = file.get("id", "")
    if not file_id:
        logger.warning("⚠️ No file ID returned for %s", filename)
        return ""

    logger.info("✅ Uploaded photo to Drive: %s → %s", filename, file_id)

    # Make publicly accessible
    try:
        service.permissions().create(
            fileId=file_id,
            body={
                "type": "anyone",
                "role": "reader",
            },
            fields="id",
        ).execute()
        logger.info("✅ Made photo publicly accessible: %s", file_id)
    except Exception as e:
        logger.warning("⚠️ Failed to set permissions on %s: %s", file_id, e)

    return file_id


def get_photo_url(file_id: str) -> str:
    """Get a direct URL for a Drive-hosted image (works with IMAGE())."""
    return f"https://lh3.googleusercontent.com/d/{file_id}"


def check_drive_quota() -> dict:
    """Check the service account's Drive storage quota."""
    try:
        service = _get_drive_service()
        about = service.about().get(fields="storageQuota").execute()
        quota = about.get("storageQuota", {})
        used = int(quota.get("usage", 0))
        limit = int(quota.get("limit", 0))
        return {"used_mb": used / (1024**2), "limit_mb": limit / (1024**2), "ok": used < limit}
    except Exception as e:
        logger.error("Failed to check Drive quota: %s", e)
        return {"used_mb": 0, "limit_mb": 0, "ok": False, "error": str(e)}
