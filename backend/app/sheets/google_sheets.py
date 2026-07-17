"""Google Sheets integration — create and populate spreadsheets."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import gspread
from googleapiclient.discovery import build

from ..config import settings
from ..models import SurveyRow, SURVEY_COLUMNS
from .google_drive import _get_credentials, upload_photo, get_photo_url

logger = logging.getLogger(__name__)

# MIME type for Google Sheets
SHEETS_MIME_TYPE = "application/vnd.google-apps.spreadsheet"


def _get_gspread_client() -> gspread.Client:
    """Create a gspread client from OAuth user credentials."""
    creds = _get_credentials()
    return gspread.authorize(creds)


def _create_sheet_via_drive_api(name: str, folder_id: str | None) -> tuple[str, str]:
    """Create a Google Sheet using the Drive API so it lands in the target folder.

    gspread's ``folder_id`` parameter is unreliable across versions — the Drive
    API ``parents`` + ``mimeType`` approach is bulletproof.

    Args:
        name: Display name for the spreadsheet.
        folder_id: ID of the Drive folder to create the sheet in, or ``None``
                   for root.

    Returns:
        Tuple of (sheet_id, sheet_url).
    """
    creds = _get_credentials()
    drive = build("drive", "v3", credentials=creds)

    file_metadata: dict = {
        "name": name,
        "mimeType": SHEETS_MIME_TYPE,
    }
    if folder_id:
        file_metadata["parents"] = [folder_id]

    drive_file = (
        drive.files()
        .create(body=file_metadata, fields="id,webViewLink")
        .execute()
    )
    return drive_file["id"], drive_file["webViewLink"]


def create_and_populate_sheet(
    rows: list[SurveyRow],
    photo_files: list[str],
    session_id: str,
) -> str:
    """Create a new Google Sheet, populate it with OCR data, and return the URL.

    Photo handling:
    - Upload each photo to Google Drive
    - Reference via IMAGE() formula in the 写真 column
    - Photos become publicly accessible via Drive link (tradeoff for MVP simplicity)

    Args:
        rows: List of SurveyRow objects from OCR
        photo_files: List of local file paths for photos
        session_id: Session ID for sheet naming

    Returns:
        URL of the created Google Sheet
    """
    gc = _get_gspread_client()

    # Create the spreadsheet via Drive API (reliably places it in the target folder)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet_name = f"Cowell OCR - {session_id[:8]} - {timestamp}"
    folder_id = settings.google_oauth_target_folder_id or None

    sheet_id, sheet_url = _create_sheet_via_drive_api(sheet_name, folder_id)
    spreadsheet = gc.open_by_key(sheet_id)
    worksheet = spreadsheet.sheet1
    worksheet.update_title("調査データ")

    logger.info("Created Google Sheet: %s  [folder=%s]", sheet_name, folder_id or "root")

    # Build header row
    headers = [col[1] for col in SURVEY_COLUMNS]  # Japanese column names

    # Build data rows
    data_rows = []
    photo_id_map = {}  # local_path → drive_file_id

    # Upload photos into the same target folder (if configured)
    for photo_path in photo_files:
        try:
            file_id = upload_photo(photo_path, Path(photo_path).name, folder_id=folder_id)
            photo_id_map[photo_path] = file_id
        except Exception as e:
            logger.warning("Failed to upload photo %s: %s", photo_path, e)

    for row in rows:
        # Build the photo cell value
        photo_cell = ""
        if row.photo_id and row.photo_id in photo_id_map:
            drive_url = get_photo_url(photo_id_map[row.photo_id])
            photo_cell = f'=IMAGE("{drive_url}", 1)'
        elif row.photo_id:
            # Try to find by local path reference
            for local_path, drive_id in photo_id_map.items():
                if row.photo_id in local_path or Path(local_path).stem in row.photo_id:
                    drive_url = get_photo_url(drive_id)
                    photo_cell = f'=IMAGE("{drive_url}", 1)'
                    break

        data_rows.append([
            row.floor,
            row.location,
            row.fixture_model,
            row.existing_product,
            photo_cell,
            row.quantity,
            row.notes,
        ])

    # Write data to sheet
    all_data = [headers] + data_rows
    worksheet.update(values=all_data, range_name="A1")

    # Format header row (bold)
    worksheet.format("A1:G1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.9, "green": 0.93, "blue": 0.97},
    })

    # Auto-resize columns (approximate)
    worksheet.columns_auto_resize(0, len(headers) - 1)

    # Set column widths and row heights via batch_update
    # (gspread 6.x dropped update_column_width / update_row_height in favour of
    # raw batchUpdate requests, which is the only way to set pixel sizes.)
    col_widths = [80, 150, 160, 250, 100, 60, 200]  # pixels
    dimension_requests = [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": worksheet.id,
                    "dimension": "COLUMNS",
                    "startIndex": i,
                    "endIndex": i + 1,
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize",
            }
        }
        for i, width in enumerate(col_widths)
    ]
    # Row heights: header 30, data 50
    dimension_requests.append({
        "updateDimensionProperties": {
            "range": {
                "sheetId": worksheet.id,
                "dimension": "ROWS",
                "startIndex": 0,
                "endIndex": 1,
            },
            "properties": {"pixelSize": 30},
            "fields": "pixelSize",
        }
    })
    if len(all_data) >= 2:
        dimension_requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": worksheet.id,
                    "dimension": "ROWS",
                    "startIndex": 1,
                    "endIndex": len(all_data),
                },
                "properties": {"pixelSize": 50},
                "fields": "pixelSize",
            }
        })
    if dimension_requests:
        spreadsheet.batch_update({"requests": dimension_requests})

    sheet_url = spreadsheet.url
    logger.info("Sheet populated with %d rows: %s", len(rows), sheet_url)

    return sheet_url
