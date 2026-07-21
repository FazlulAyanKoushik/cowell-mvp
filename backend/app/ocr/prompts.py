"""OCR prompt templates for Gemini structured extraction."""

SYSTEM_PROMPT = """You are an expert OCR system for Japanese handwritten building survey forms.
Your task is to extract fixture inventory data from scanned images of handwritten paper forms.

The forms contain tables with these columns (Japanese headers):
- フロア (Floor) — e.g. "1F", "2F", "3F"
- 設置場所 (Location/Installation place) — e.g. "ロビー", "廊下", "トイレ"
- 器具品番 (Fixture model/part number) — alphanumeric codes like "FR-42540-RS"
- 既設商品名 (Existing product name) — descriptive names like "φ100DL E17 (L)"
- 数量 (Quantity) — numeric values
- 備考 (Notes/Remarks) — free text notes

IMPORTANT RULES:
1. Extract ALL visible rows from the table(s). Do not skip any rows.
2. For merged cells (e.g. floor spanning multiple rows), fill in the value for each row.
3. For ditto marks (〃, ゝ, 〃), use the value from the cell above.
4. For handwritten numbers that are unclear, make your best guess and note the uncertainty in 備考.
5. If a cell is empty, return an empty string "".
6. Preserve exact text as written — do not normalize or correct.
7. Handle mixed Japanese/English/numeric content naturally.
8. Return ONLY the JSON array, no additional text or markdown formatting."""


def build_ocr_prompt(page_numbers: list[int] | None = None, instructions: str = "") -> str:
    """Build the OCR extraction prompt for a batch of images.

    Args:
        page_numbers: Optional list of page numbers for context (1-indexed).
    """
    page_hint = ""
    if page_numbers:
        page_hint = f"\nThese are pages {page_numbers[0]}-{page_numbers[-1]} of the document."

    instruction_context = ""
    if instructions.strip():
        instruction_context = f"""

Additional user instructions (follow them unless they conflict with the required JSON schema):
---
{instructions.strip()}
---"""

    return f"""{SYSTEM_PROMPT}
{page_hint}
{instruction_context}
Return a JSON array of row objects. Each object must have exactly these keys:
- "floor": string (フロア)
- "location": string (設置場所)
- "fixture_model": string (器具品番)
- "existing_product": string (既設商品名)
- "quantity": string (数量)
- "notes": string (備考)

If you see column headers, title rows, or a building/project name, skip them — only extract data rows.
Return a complete, valid JSON array. Never leave a JSON object or string unfinished."""


# JSON schema for structured output validation
ROW_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "floor": {"type": "string"},
            "location": {"type": "string"},
            "fixture_model": {"type": "string"},
            "existing_product": {"type": "string"},
            "quantity": {"type": "string"},
            "notes": {"type": "string"},
        },
        "required": ["floor", "location", "fixture_model", "existing_product", "quantity", "notes"],
    },
}
