# Cowell OCR — Phase 1 MVP

Handwritten Japanese building survey sheets → structured Google Spreadsheet.

Upload PDFs/images of handwritten fixture inventories, OCR them via Google
Gemini, edit the extracted rows in a web UI, and register the results into a
new Google Sheet with photo references.

---

## Quick Start (Docker)

### 1. Prerequisites

- **Docker** + **Docker Compose**
- A **Google Gemini API key** ([get one here](https://aistudio.google.com/apikey))
- A **Google Cloud service account** with Sheets API + Drive API enabled
  ([setup guide](#google-service-account-setup))

### 2. Configure

```bash
cp .env.example .env
# Edit .env and fill in your GEMINI_API_KEY

mkdir -p backend/credentials
# Place your service_account.json in backend/credentials/
```

### 3. Run

```bash
docker compose up --build
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs

---

## Local Development (no Docker)

### Backend

```bash
cd backend
uv sync
# Create .env with GEMINI_API_KEY=...
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000, proxies /api to localhost:8000
```

---

## Google Service Account Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use an existing one)
3. Enable these APIs:
   - **Google Sheets API**
   - **Google Drive API**
4. Go to **IAM & Admin → Service Accounts**
5. Create a service account, skip roles (not needed for Sheets/Drive)
6. Click the service account → **Keys → Add Key → Create new key → JSON**
7. Download the JSON file and place it at:
   ```
   backend/credentials/service_account.json
   ```

**Note:** The service account must share ownership of any Google Sheet it
creates. For the first run, the service account creates the sheet itself so
no sharing is needed.

---

## User Flow

1. **Upload** — Drag-drop PDFs/images of survey sheets + optional photos
2. **OCR Processing** — Gemini 2.5 Flash extracts table rows as structured JSON
3. **Edit / Confirm** — Inline-editable table with 7 columns, attach photos
4. **Register** — Creates a Google Sheet, populates data, attaches photo URLs via IMAGE()

---

## Output Schema

| Column | Japanese | Example |
|--------|----------|---------|
| フロア | Floor | 3F |
| 設置場所 | Location | ロビー |
| 器具品番 | Fixture Model # | FR-42540-RS |
| 既設商品名 | Existing Product | φ100DL E17 (L) |
| 写真 | Photo | =IMAGE("https://lh3.googleusercontent.com/d/...") |
| 数量 | Quantity | 36 |
| 備考 | Notes | 調光 |

---

## Architecture

```
React SPA (Vite)  ─── FastAPI Backend (Python)
     Port 3000              Port 8000
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              Gemini 2.5   Google Sheets  Google Drive
               Flash OCR    (gspread)    (photo upload)
```

- **Backend**: FastAPI + pypdfium2 (PDF→image) + Pillow (compression) + google-genai SDK
- **Frontend**: React 19 + TypeScript + Vite
- **OCR**: Google Gemini 2.5 Flash with structured JSON output
- **Sheets**: gspread with service account auth
- **Photos**: Uploaded to Google Drive, referenced via `IMAGE()` formula

---

## Project Structure

```
cowell-mvp/
├── backend/
│   ├── pyproject.toml          # uv dependencies
│   ├── Dockerfile
│   ├── credentials/            # Place service_account.json here
│   ├── uploads/                # Temp file storage (auto-created)
│   └── app/
│       ├── main.py             # FastAPI app entry point
│       ├── config.py           # Environment-based settings
│       ├── models.py           # Pydantic schemas
│       ├── ocr/
│       │   ├── gemini.py       # Gemini API client + extraction
│       │   ├── image.py        # PDF→image + compression
│       │   └── prompts.py      # OCR prompt templates
│       ├── sheets/
│       │   ├── google_sheets.py # Sheet creation + population
│       │   └── google_drive.py  # Photo upload to Drive
│       ├── routes/
│       │   ├── upload.py       # POST /api/upload
│       │   ├── ocr.py          # POST /api/ocr/{id}
│       │   ├── rows.py         # GET/PUT/POST/DELETE /api/rows/{id}
│       │   └── register.py     # POST /api/register/{id}
│       └── sessions/
│           └── memory.py       # In-memory session store
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf              # SPA routing + API proxy
│   ├── package.json
│   └── src/
│       ├── App.tsx             # Router + step indicator
│       ├── api/client.ts       # API client
│       ├── types/index.ts      # TypeScript interfaces
│       ├── pages/              # 4 pages: Upload → Process → Edit → Done
│       ├── components/         # FileUploadZone, EditableRow, PhotoPreview
│       └── styles/app.css      # Global styles
├── docker-compose.yml
├── .env.example
└── Requiremnts/                # Original spec documents
```

---

## OCR Accuracy Report (Phase 1 Feasibility)

### Approach Tested
- **Model**: Gemini 2.5 Flash (structured JSON output)
- **Strategy**: Multi-page PDF → images (200 DPI) → batched (8 pages/batch) → JSON extraction
- **Prompt**: Schema-enforced JSON output with ditto mark / merged cell handling

### Expected Strengths
1. **Structured JSON output** eliminates fragile TSV/markdown parsing
2. **Multi-page batching** reduces API calls (8 pages per call)
3. **Image compression** (1200px max, JPEG 85%) balances quality vs. token cost
4. **Schema validation** ensures all 7 columns are present in every row

### Known Failure Patterns (from prototype testing)
1. **Ditto marks (〃/ゝ)** — Gemini sometimes misses these; requires prompt reinforcement
2. **Merged cells** — Floor values spanning multiple rows may not propagate correctly
3. **Messy handwriting** — Particularly poor on numerals (quantity field) and mixed kanji/kana
4. **Notes outside ruled cells** — Handwritten margin notes may be lost or misplaced
5. **Inconsistent table structure** — Different pages have different column layouts

### Recommendations for Production
1. **Two-pass OCR**: First pass extracts, second pass validates + fills gaps
2. **Confidence scoring**: Add confidence field per cell, flag low-confidence for manual review
3. **Pre-processing**: Deskew, binarize, and normalize images before sending to Gemini
4. **Model comparison**: Test Gemini 2.5 Pro (higher accuracy, higher cost) for difficult pages
5. **Template matching**: Learn the specific form layout to improve column alignment

### Photo-in-Sheet Tradeoffs
| Method | Pros | Cons |
|--------|------|------|
| Drive upload + IMAGE() (current) | Simple, works in Sheets | Photos publicly accessible via Drive URL |
| Signed URLs (S3/GCS) | Private, controllable | More complex auth, URL expiry |
| Base64 in cell | No external hosting | Huge cell content, Sheets limitations |
| QR code → private URL | Clean cell, private | Extra click for user |

---

## Assumptions

1. **Single-user local dev** — no authentication, no multi-tenancy
2. **In-memory sessions** — lost on server restart (acceptable for MVP)
3. **Gemini 2.5 Flash** — default model, configurable via `GEMINI_MODEL` env var
4. **Service account auth** — simplest for automated sheet creation
5. **Public photo URLs** — tradeoff for simplicity; production should use signed URLs
6. **Japanese field names** — column headers match the specified schema exactly

---

## License

MIT
