"""Google Sheets integration — create and populate spreadsheets."""

from __future__ import annotations

import logging
from datetime import datetime

import gspread

from ..config import settings
from ..models import SurveyRow, SURVEY_COLUMNS
from .google_drive import _get_credentials, upload_photo, get_photo_url

logger = logging.getLogger(__name__)


def _get_gspread_client() -> gspread.Client:
    """Create a gspread client from service account credentials."""
    creds = _get_credentials()
    return gspread.authorize(creds)


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

    # Create the spreadsheet
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet_name = f"Cowell OCR - {session_id[:8]} - {timestamp}"
    spreadsheet = gc.create(sheet_name)
    worksheet = spreadsheet.sheet1
    worksheet.update_title("調査データ")

    logger.info("Created Google Sheet: %s", sheet_name)

    # Build header row
    headers = [col[1] for col in SURVEY_COLUMNS]  # Japanese column names

    # Build data rows
    data_rows = []
    photo_id_map = {}  # local_path → drive_file_id

    # Upload photos first
    for photo_path in photo_files:
        try:
            file_id = upload_photo(photo_path, Path(photo_path).name)
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
    worksheet.update("A1", all_data)

    # Format header row (bold)
    worksheet.format("A1:G1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.9, "green": 0.93, "blue": 0.97},
    })

    # Auto-resize columns (approximate)
    worksheet.columns_auto_resize(0, len(headers) - 1)

    # Set column widths for readability
    col_widths = [80, 150, 160, 250, 100, 60, 200]  # pixels
    for i, width in enumerate(col_widths):
        worksheet.update_column_width(i, width)

    # Set row heights for photo rows
    worksheet.update_row_height(1, 30)  # Header row
    for i in range(2, len(all_data) + 1):
        worksheet.update_row_height(i, 50)  # Data rows (room for photo thumbnails)

    sheet_url = spreadsheet.url
    logger.info("Sheet populated with %d rows: %s", len(rows), sheet_url)

    return sheet_url
