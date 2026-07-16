"""FastAPI application — entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes import upload, ocr, rows, register

# ── Logging configuration ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cowell")

app = FastAPI(
    title="Cowell OCR API",
    description="Handwritten Japanese survey sheet → Google Sheets",
    version="0.1.0",
)

# CORS for local dev (frontend on port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route modules
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(ocr.router, prefix="/api", tags=["ocr"])
app.include_router(rows.router, prefix="/api", tags=["rows"])
app.include_router(register.router, prefix="/api", tags=["register"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "model": settings.gemini_model}


@app.on_event("startup")
def startup_log():
    logger.info("=" * 60)
    logger.info("Cowell OCR API starting up")
    logger.info("  Gemini model:    %s", settings.gemini_model)
    logger.info("  Upload dir:      %s", settings.upload_dir)
    logger.info("  SA path:         %s", settings.google_service_account_path)
    logger.info("  Gemini API key:  %s", "SET" if settings.gemini_api_key else "MISSING ⚠️")
    from pathlib import Path
    sa_exists = Path(settings.google_service_account_path).exists()
    logger.info("  SA file exists:  %s", "YES ✅" if sa_exists else "NO ❌")
    logger.info("=" * 60)
