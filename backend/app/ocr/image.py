"""PDF → image conversion and image compression utilities."""

from __future__ import annotations

import io
import logging
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

from ..config import settings

logger = logging.getLogger("cowell.ocr.image")


def pdf_to_images(pdf_path: str | Path, dpi: int = 200) -> list[bytes]:
    """Convert a multi-page PDF to a list of JPEG image bytes.

    Uses pypdfium2 for zero-dependency PDF rendering.
    Each page is rendered at the given DPI and compressed to JPEG.
    """
    pdf_path = Path(pdf_path)
    logger.info("Converting PDF to images: %s", pdf_path.name)

    pdf = pdfium.PdfDocument(str(pdf_path))
    page_count = len(pdf)
    images: list[bytes] = []

    for i in range(page_count):
        page = pdf[i]
        # Render at specified DPI (200 gives good OCR quality)
        scale = dpi / 72.0
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()

        # Convert to RGB if needed (RGBA → RGB for JPEG)
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        # Compress to JPEG bytes
        buf = io.BytesIO()
        pil_image.save(buf, format="JPEG", quality=settings.jpeg_quality, optimize=True)
        images.append(buf.getvalue())

        logger.info("  Page %d/%d: %dx%d → %d KB", i + 1, page_count,
                     pil_image.width, pil_image.height, len(buf.getvalue()) // 1024)

    pdf.close()
    logger.info("Converted %d pages to images", len(images))
    return images


def compress_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> bytes:
    """Compress an uploaded image to JPEG with max dimension constraints.

    Mimics the JS canvas compression from the HTML prototype:
    scale down so neither dimension exceeds max_image_dimension,
    then save as JPEG at jpeg_quality.
    """
    img = Image.open(io.BytesIO(image_bytes))

    # Convert palette/RGBA to RGB for JPEG
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif img.mode == "L":
        img = img.convert("RGB")

    # Scale down if needed
    max_dim = settings.max_image_dimension
    if img.width > max_dim or img.height > max_dim:
        if img.width >= img.height:
            new_h = int(img.height * max_dim / img.width)
            img = img.resize((max_dim, new_h), Image.LANCZOS)
        else:
            new_w = int(img.width * max_dim / img.height)
            img = img.resize((new_w, max_dim), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=settings.jpeg_quality, optimize=True)
    return buf.getvalue()


def image_to_jpeg_bytes(image_bytes: bytes) -> bytes:
    """Ensure image is JPEG bytes (convert if needed)."""
    return compress_image(image_bytes)
