"""Single OCR route — receives files and returns extracted rows."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import settings
from ..models import OCRResponse
from ..ocr.gemini import extract_rows_from_images_async
from ..ocr.image import compress_image, pdf_to_images

logger = logging.getLogger("cowell.routes.ocr")
router = APIRouter()

ALLOWED_SURVEY_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_INSTRUCTION_CHARS = 50_000


@router.post("/ocr", response_model=OCRResponse)
async def run_ocr(
    survey_files: list[UploadFile] = File(..., description="Survey PDFs or images"),
    instructions: str = Form(default="", description="Optional OCR instructions"),
):
    """Extract rows from surveys in one request without creating a session."""
    if not survey_files:
        raise HTTPException(status_code=400, detail="At least one survey file is required")

    try:
        all_images: list[bytes] = []
        max_size = settings.max_file_size_mb * 1024 * 1024

        for upload in survey_files:
            filename = upload.filename or ""
            suffix = Path(filename).suffix.lower()
            if suffix not in ALLOWED_SURVEY_SUFFIXES:
                raise HTTPException(status_code=400, detail=f"Unsupported survey file: {filename}")

            content = await upload.read()
            if len(content) > max_size:
                raise HTTPException(status_code=400, detail=f"File too large: {filename}")

            if suffix == ".pdf":
                with tempfile.NamedTemporaryFile(
                    dir=settings.upload_dir, suffix=".pdf", delete=False
                ) as temp_file:
                    temp_file.write(content)
                    temp_path = Path(temp_file.name)
                try:
                    all_images.extend(pdf_to_images(temp_path))
                finally:
                    temp_path.unlink(missing_ok=True)
            else:
                all_images.append(compress_image(content))

        if not all_images:
            raise HTTPException(status_code=400, detail="No processable images found")

        if len(instructions) > MAX_INSTRUCTION_CHARS:
            raise HTTPException(status_code=400, detail="Instructions are too long")

        batch_size = settings.ocr_batch_size
        batches = [all_images[i:i + batch_size] for i in range(0, len(all_images), batch_size)]
        logger.info("Processing %d pages in %d Gemini batches", len(all_images), len(batches))

        rows = await extract_rows_from_images_async(batches, instructions)
        logger.info("OCR complete: %d rows extracted", len(rows))
        return OCRResponse(row_count=len(rows), rows=rows)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("OCR failed")
        raise HTTPException(status_code=500, detail=f"OCR failed: {exc}") from exc
