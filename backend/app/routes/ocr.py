"""OCR route — triggers Gemini extraction on uploaded files."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..models import OCRResponse, SessionStatus
from ..sessions.memory import get_session, update_session
from ..ocr.image import pdf_to_images, compress_image
from ..ocr.gemini import extract_rows_from_images_async

logger = logging.getLogger("cowell.routes.ocr")
router = APIRouter()


@router.post("/ocr/{session_id}", response_model=OCRResponse)
async def run_ocr(session_id: str):
    """Run Gemini OCR on all uploaded survey files in the session.

    Converts PDFs to images, compresses images, batches them,
    and sends to Gemini for structured JSON extraction.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.survey_files:
        raise HTTPException(status_code=400, detail="No survey files in session")

    if session.status == SessionStatus.OCR_DONE:
        # Already processed — return existing results
        return OCRResponse(
            session_id=session_id,
            row_count=len(session.rows),
            rows=session.rows,
        )

    # Mark as processing
    session.status = SessionStatus.OCR_RUNNING
    update_session(session)

    try:
        # Convert all files to image bytes
        all_images: list[bytes] = []

        for file_path_str in session.survey_files:
            file_path = Path(file_path_str)

            if file_path.suffix.lower() == ".pdf":
                # Convert PDF pages to images
                images = pdf_to_images(file_path)
                all_images.extend(images)
            elif file_path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                # Compress raw image
                raw_bytes = file_path.read_bytes()
                compressed = compress_image(raw_bytes)
                all_images.append(compressed)
            else:
                logger.warning("Skipping unsupported file: %s", file_path.name)

        if not all_images:
            raise HTTPException(status_code=400, detail="No processable images found")

        logger.info("Total images to process: %d", len(all_images))

        # Split into batches
        batch_size = settings.ocr_batch_size
        batches = [
            all_images[i:i + batch_size]
            for i in range(0, len(all_images), batch_size)
        ]
        logger.info("Split into %d batches of up to %d images each", len(batches), batch_size)

        # Run OCR on all batches in parallel
        rows = await extract_rows_from_images_async(batches)

        # Update session
        session.rows = rows
        session.status = SessionStatus.OCR_DONE
        update_session(session)

        logger.info("OCR complete: %d rows extracted", len(rows))

        return OCRResponse(
            session_id=session_id,
            row_count=len(rows),
            rows=rows,
        )

    except Exception as e:
        session.status = SessionStatus.ERROR
        session.error_message = str(e)
        update_session(session)
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}") from e
