"""Row editing routes — get and update OCR results."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import SurveyRow
from ..sessions.memory import get_session, update_session

router = APIRouter()


@router.get("/rows/{session_id}")
async def get_rows(session_id: str):
    """Get current OCR rows for a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "status": session.status,
        "row_count": len(session.rows),
        "rows": session.rows,
    }


@router.put("/rows/{session_id}")
async def update_rows(session_id: str, rows: list[SurveyRow]):
    """Replace all rows for a session (after user editing)."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Re-index rows sequentially
    for i, row in enumerate(rows, start=1):
        row.id = i

    session.rows = rows
    update_session(session)

    return {
        "session_id": session_id,
        "row_count": len(rows),
        "message": "Rows updated successfully",
    }


@router.delete("/rows/{session_id}/{row_id}")
async def delete_row(session_id: str, row_id: int):
    """Delete a single row by ID."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    original_count = len(session.rows)
    session.rows = [r for r in session.rows if r.id != row_id]

    if len(session.rows) == original_count:
        raise HTTPException(status_code=404, detail=f"Row {row_id} not found")

    # Re-index remaining rows
    for i, row in enumerate(session.rows, start=1):
        row.id = i

    update_session(session)

    return {
        "session_id": session_id,
        "row_count": len(session.rows),
        "message": f"Row {row_id} deleted",
    }


@router.post("/rows/{session_id}")
async def add_row(session_id: str, row: SurveyRow):
    """Add a new row to the session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    new_id = len(session.rows) + 1
    row.id = new_id
    session.rows.append(row)
    update_session(session)

    return {
        "session_id": session_id,
        "row": row,
        "message": "Row added",
    }
