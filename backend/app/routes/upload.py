"""File upload route — receives PDFs, images, and photos."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException

from ..config import settings
from ..models import UploadResponse
from ..sessions.memory import create_session, get_session, update_session

logger = logging.getLogger("cowell.routes.upload")
router = APIRouter()

ALLOWED_SURVEY_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
ALLOWED_PHOTO_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    survey_files: list[UploadFile] = File(default=[], description="Survey PDFs/images"),
    photo_files: list[UploadFile] = File(default=[], description="Survey photos"),
):
    """Upload survey documents and photos, creating a new session.

    - survey_files: PDFs or images of the handwritten survey sheets
    - photo_files: Optional photos to attach to rows later
    """
    if not survey_files:
        raise HTTPException(status_code=400, detail="No survey files provided")

    session_id = uuid.uuid4().hex[:12]
    session = create_session(session_id)

    # Create session upload directory
    session_dir = settings.upload_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "photos").mkdir(exist_ok=True)

    # Save survey files
    for f in survey_files:
        if f.content_type not in ALLOWED_SURVEY_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {f.content_type} ({f.filename})",
            )

        file_path = session_dir / f.filename
        content = await f.read()

        if len(content) > settings.max_file_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {f.filename} (max {settings.max_file_size_mb}MB)",
            )

        file_path.write_bytes(content)
        session.survey_files.append(str(file_path))
        logger.info("Saved survey file: %s (%d KB)", f.filename, len(content) // 1024)

    # Save photo files
    for f in photo_files:
        if f.content_type not in ALLOWED_PHOTO_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported photo type: {f.content_type} ({f.filename})",
            )

        photo_path = session_dir / "photos" / f.filename
        content = await f.read()
        photo_path.write_bytes(content)
        session.photo_files.append(str(photo_path))
        logger.info("Saved photo: %s (%d KB)", f.filename, len(content) // 1024)

    update_session(session)

    return UploadResponse(
        session_id=session_id,
        file_count=len(session.survey_files),
        photo_count=len(session.photo_files),
    )
