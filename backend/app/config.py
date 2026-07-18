"""Application configuration from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings


def _default_upload_dir() -> Path:
    """Pick upload dir: /app/uploads in Docker, ./uploads locally."""
    docker_path = Path("/app/uploads")
    if docker_path.parent.exists():
        return docker_path
    return Path(__file__).resolve().parent.parent / "uploads"


def _default_token_path() -> str:
    """Pick OAuth token path: Docker path or local ./credentials/."""
    docker_path = "/app/credentials/token.json"
    if Path(docker_path).exists():
        return docker_path
    local = Path(__file__).resolve().parent.parent / "credentials" / "token.json"
    return str(local)


class Settings(BaseSettings):
    """App settings loaded from environment / .env file."""

    gemini_api_key: str = ""
    google_oauth_token_path: str = ""
    # Folder in your Drive where new Sheets will be created.
    # Get this from the folder URL: drive.google.com/drive/folders/<THIS>
    google_oauth_target_folder_id: str = ""

    # Image processing
    max_image_dimension: int = 1200
    jpeg_quality: int = 85
    max_file_size_mb: int = 20

    # Gemini
    gemini_model: str = "gemini-2.5-flash"
    gemini_max_output_tokens: int = 32768
    ocr_batch_size: int = 8  # pages per Gemini API call

    # Upload directory (for temp file storage)
    upload_dir: Path = Path(".")

    # ── S3 / Serverless settings ─────────────────────────────────
    # When set, the backend reads/writes session data from S3 instead of memory.
    s3_bucket_sessions: str = ""
    s3_bucket_uploads: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()

# Apply smart defaults (must come after Settings() construction)
if not settings.google_oauth_token_path:
    settings.google_oauth_token_path = _default_token_path()
if settings.upload_dir == Path("."):
    settings.upload_dir = _default_upload_dir()

# Ensure upload dir exists
settings.upload_dir.mkdir(parents=True, exist_ok=True)
