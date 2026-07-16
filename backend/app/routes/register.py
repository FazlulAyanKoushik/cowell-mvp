"""Registration route — creates Google Sheet from edited data."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..models import RegisterResponse, SessionStatus
from ..sessions.memory import get_session, update_session
from ..sheets.google_sheets import create_and_populate_sheet

logger = logging.getLogger("cowell.routes.register")
router = APIRouter()


@router.post("/register/{session_id}", response_model=RegisterResponse)
async def register_to_sheet(session_id: str):
    """Create a Google Sheet populated with the (edited) OCR data.

    Uploads photos to Drive, creates the Sheet, writes all rows,
    and returns the Sheet URL.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.rows:
        raise HTTPException(status_code=400, detail="No rows to register")

    if session.status == SessionStatus.REGISTERED and session.sheet_url:
        # Already registered — return existing URL
        return RegisterResponse(
            session_id=session_id,
            sheet_url=session.sheet_url,
            row_count=len(session.rows),
        )

    # Mark as registering
    session.status = SessionStatus.REGISTERING
    update_session(session)

    try:
        sheet_url = create_and_populate_sheet(
            rows=session.rows,
            photo_files=session.photo_files,
            session_id=session_id,
        )

        session.sheet_url = sheet_url
        session.status = SessionStatus.REGISTERED
        update_session(session)

        logger.info("Registration complete: %s → %s", session_id, sheet_url)

        return RegisterResponse(
            session_id=session_id,
            sheet_url=sheet_url,
            row_count=len(session.rows),
        )

    except FileNotFoundError as e:
        session.status = SessionStatus.ERROR
        session.error_message = f"Google credentials not found: {e}"
        update_session(session)
        raise HTTPException(
            status_code=500,
            detail=(
                "Google service account not configured. "
                "Place service_account.json in backend/credentials/ and restart. "
                f"Error: {e}"
            ),
        ) from e
    except Exception as e:
        session.status = SessionStatus.ERROR
        session.error_message = str(e)
        update_session(session)
        raise HTTPException(status_code=500, detail=f"Registration failed: {e}") from e
