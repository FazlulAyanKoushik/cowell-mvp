"""Pydantic schemas for request/response models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SurveyRow(BaseModel):
    """A single line item from the handwritten survey."""

    id: int = 0
    floor: str = Field(default="", alias="floor", description="フロア")
    location: str = Field(default="", alias="location", description="設置場所")
    fixture_model: str = Field(default="", alias="fixture_model", description="器具品番")
    existing_product: str = Field(default="", alias="existing_product", description="既設商品名")
    photo_id: str = Field(default="", description="Attached photo ID (empty if none)")
    quantity: str = Field(default="", alias="quantity", description="数量")
    notes: str = Field(default="", alias="notes", description="備考")

    model_config = {"populate_by_name": True}


class SessionStatus(str, Enum):
    UPLOADED = "uploaded"
    OCR_RUNNING = "ocr_running"
    OCR_DONE = "ocr_done"
    REGISTERING = "registering"
    REGISTERED = "registered"
    ERROR = "error"


class SessionData(BaseModel):
    """In-memory session state."""

    session_id: str
    status: SessionStatus = SessionStatus.UPLOADED
    created_at: datetime = Field(default_factory=datetime.now)

    # File paths on disk
    survey_files: list[str] = Field(default_factory=list)
    photo_files: list[str] = Field(default_factory=list)

    # OCR results
    rows: list[SurveyRow] = Field(default_factory=list)

    # Registration result
    sheet_url: str | None = None
    error_message: str | None = None


# Column schema for the output
SURVEY_COLUMNS = [
    ("floor", "フロア"),
    ("location", "設置場所"),
    ("fixture_model", "器具品番"),
    ("existing_product", "既設商品名"),
    ("photo_id", "写真"),
    ("quantity", "数量"),
    ("notes", "備考"),
]


class UploadResponse(BaseModel):
    session_id: str
    file_count: int
    photo_count: int


class OCRResponse(BaseModel):
    row_count: int
    rows: list[SurveyRow]


class RegisterResponse(BaseModel):
    session_id: str
    sheet_url: str
    row_count: int


class ErrorResponse(BaseModel):
    detail: str
