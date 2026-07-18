"""Google Drive integration — upload photos and make them accessible."""

from __future__ import annotations

import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from ..config import settings

logger = logging.getLogger("cowell.sheets")

# Scopes needed for Drive upload
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]


def _get_credentials() -> Credentials:
    """Load OAuth 2.0 user credentials from the saved token file.

    The token file is created once by `python auth_oauth.py` and contains
    a refresh token that auto-refreshes the access token when expired.

    Returns:
        google.oauth2.credentials.Credentials
    """
    token_path = settings.google_oauth_token_path
    if not Path(token_path).exists():
        raise FileNotFoundError(
            f"OAuth token not found: {token_path}\n"
            "Run `python auth_oauth.py` once to authorize your Google account.\n"
            "It will open a browser for you to log in and save token.json."
        )

    creds = Credentials.from_authorized_user_file(token_path, scopes=SCOPES)

    # Auto-refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Persist the refreshed token so we don't refresh on every request.
        # If the configured path is read-only (Docker :ro volume, Lambda /app),
        # fall back to /tmp and update the settings path for subsequent reads.
        try:
            Path(token_path).write_text(creds.to_json())
            logger.info("Refreshed OAuth access token and saved to %s", token_path)
        except (OSError, PermissionError):
            fallback = Path("/tmp/cowell_oauth_token.json")
            fallback.write_text(creds.to_json())
            # Update settings so next call reads from the writable path
            settings.google_oauth_token_path = str(fallback)
            logger.info(
                "Could not write to %s (read-only). Saved to %s and updated path.",
                token_path, fallback,
            )

    return creds


def _get_drive_service():
    """Get Google Drive API service."""
    creds = _get_credentials()
    return build("drive", "v3", credentials=creds)


def upload_photo(file_path: str, filename: str, folder_id: str | None = None) -> str:
    """Upload a photo to Google Drive and return the file ID.

    The file is made publicly viewable so it can be referenced
    via IMAGE() formula in Google Sheets.

    Args:
        file_path: Local path to the photo file.
        filename: Display name in Drive.
        folder_id: If set, places the photo inside this Drive folder.
                   If ``None``, uploads to the root of My Drive.

    Returns empty string on failure (quota exceeded, etc.) so
    the sheet creation can continue without photos.
    """
    service = _get_drive_service()

    file_metadata: dict[str, object] = {
        "name": filename,
    }
    if folder_id:
        file_metadata["parents"] = [folder_id]

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
