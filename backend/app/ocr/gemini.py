"""Gemini OCR client — sends images to Gemini and parses structured JSON."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from google import genai
from google.genai import types

from ..config import settings
from ..models import SurveyRow
from .prompts import build_ocr_prompt, ROW_JSON_SCHEMA

logger = logging.getLogger("cowell.ocr.gemini")


def _get_client() -> genai.Client:
    """Create a Gemini client from the configured API key."""
    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY not set. Add it to .env or environment variables."
        )
    return genai.Client(api_key=settings.gemini_api_key)


def _parse_rows(raw_json: str) -> list[dict[str, str]]:
    """Parse Gemini's JSON response into row dicts.

    Handles common issues: markdown code fences, trailing commas, extra text.
    """
    text = raw_json.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        # Remove opening fence (possibly with language tag)
        first_newline = text.index("\n")
        text = text[first_newline + 1:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Try to find the JSON array if there's surrounding text
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON: %s\nRaw text (first 500 chars): %s", e, text[:500])
        raise ValueError(f"Gemini returned invalid JSON: {e}") from e

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data).__name__}")

    return data


def extract_rows_from_images(
    image_batches: list[list[bytes]],
) -> list[SurveyRow]:
    """Run OCR on batches of images and return merged SurveyRow list.

    Args:
        image_batches: List of batches, where each batch is a list of JPEG bytes.
                       Each batch is sent as one Gemini API call.

    Returns:
        Merged list of SurveyRow objects from all batches.
    """
    client = _get_client()
    all_rows: list[SurveyRow] = []
    row_id = 0

    for batch_idx, batch in enumerate(image_batches):
        page_start = batch_idx * settings.ocr_batch_size + 1
        page_end = page_start + len(batch) - 1
        page_numbers = list(range(page_start, page_end + 1))

        logger.info(
            "Processing batch %d/%d (pages %d-%d, %d images)",
            batch_idx + 1, len(image_batches), page_start, page_end, len(batch),
        )

        prompt = build_ocr_prompt(page_numbers)

        # Build multimodal content: text prompt + images
        parts: list[types.Part] = [
            types.Part.from_text(text=prompt),
        ]
        for img_bytes in batch:
            parts.append(
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
            )

        # Call Gemini with JSON output mode
        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=0,
                    max_output_tokens=settings.gemini_max_output_tokens,
                    response_mime_type="application/json",
                    response_json_schema=ROW_JSON_SCHEMA,
                ),
            )

            raw_text = response.text or "[]"
            logger.info("Gemini response received (%d chars)", len(raw_text))

        except Exception as e:
            logger.error("Gemini API call failed for batch %d: %s", batch_idx + 1, e)
            raise RuntimeError(f"Gemini OCR failed on batch {batch_idx + 1}: {e}") from e

        # Parse the response
        raw_rows = _parse_rows(raw_text)

        for raw_row in raw_rows:
            row_id += 1
            all_rows.append(
                SurveyRow(
                    id=row_id,
                    floor=raw_row.get("floor", "").strip(),
                    location=raw_row.get("location", "").strip(),
                    fixture_model=raw_row.get("fixture_model", "").strip(),
                    existing_product=raw_row.get("existing_product", "").strip(),
                    quantity=raw_row.get("quantity", "").strip(),
                    notes=raw_row.get("notes", "").strip(),
                )
            )

        logger.info(
            "Batch %d: extracted %d rows (total so far: %d)",
            batch_idx + 1, len(raw_rows), len(all_rows),
        )

    return all_rows


async def _process_batch_async(
    client: genai.Client,
    batch: list[bytes],
    batch_idx: int,
    page_start: int,
    page_end: int,
) -> list[dict[str, str]]:
    """Process a single batch asynchronously using Gemini's native async client.

    Args:
        client: Gemini client (uses client.aio for async calls).
        batch: List of JPEG image bytes for this batch.
        batch_idx: Batch index for logging.
        page_start: First page number in this batch.
        page_end: Last page number in this batch.

    Returns:
        List of raw row dicts from Gemini's response.
    """
    page_numbers = list(range(page_start, page_end + 1))
    prompt = build_ocr_prompt(page_numbers)

    parts: list[types.Part] = [
        types.Part.from_text(text=prompt),
    ]
    for img_bytes in batch:
        parts.append(
            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
        )

    logger.info(
        "Processing batch %d (pages %d-%d, %d images) [async]",
        batch_idx + 1, page_start, page_end, len(batch),
    )

    try:
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=settings.gemini_max_output_tokens,
                response_mime_type="application/json",
                response_json_schema=ROW_JSON_SCHEMA,
            ),
        )

        raw_text = response.text or "[]"
        logger.info("Gemini response received for batch %d (%d chars)", batch_idx + 1, len(raw_text))

    except Exception as e:
        logger.error("Gemini API call failed for batch %d: %s", batch_idx + 1, e)
        raise RuntimeError(f"Gemini OCR failed on batch {batch_idx + 1}: {e}") from e

    return _parse_rows(raw_text)


async def extract_rows_from_images_async(
    image_batches: list[list[bytes]],
) -> list[SurveyRow]:
    """Run OCR on batches of images in parallel and return merged SurveyRow list.

    All batches are processed concurrently using asyncio.gather(), significantly
    reducing total processing time compared to sequential execution.

    Args:
        image_batches: List of batches, where each batch is a list of JPEG bytes.

    Returns:
        Merged list of SurveyRow objects from all batches.
    """
    client = _get_client()

    # Build tasks for all batches
    tasks = []
    for batch_idx, batch in enumerate(image_batches):
        page_start = batch_idx * settings.ocr_batch_size + 1
        page_end = page_start + len(batch) - 1

        tasks.append(
            _process_batch_async(client, batch, batch_idx, page_start, page_end)
        )

    # Run all batches in parallel
    logger.info("Starting %d batches in parallel...", len(image_batches))
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge results and assign sequential row IDs
    all_rows: list[SurveyRow] = []
    row_id = 0

    for batch_idx, result in enumerate(batch_results):
        if isinstance(result, Exception):
            logger.error("Batch %d failed: %s", batch_idx + 1, result)
            raise RuntimeError(f"Gemini OCR failed on batch {batch_idx + 1}: {result}") from result

        for raw_row in result:
            row_id += 1
            all_rows.append(
                SurveyRow(
                    id=row_id,
                    floor=raw_row.get("floor", "").strip(),
                    location=raw_row.get("location", "").strip(),
                    fixture_model=raw_row.get("fixture_model", "").strip(),
                    existing_product=raw_row.get("existing_product", "").strip(),
                    quantity=raw_row.get("quantity", "").strip(),
                    notes=raw_row.get("notes", "").strip(),
                )
            )

    logger.info("All batches complete: %d rows extracted", len(all_rows))
    return all_rows
