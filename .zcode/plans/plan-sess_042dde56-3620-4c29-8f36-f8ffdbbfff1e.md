## 📋 Implementation Plan

### Objective
Build a Dockerized full-stack MVP (FastAPI backend + React/Vue SPA frontend) that OCRs handwritten Japanese survey sheets via Google Gemini, presents an editable confirmation UI, and registers results into a Google Sheet with photo references.

### Architecture

```
┌─────────────────────┐     ┌──────────────────────────┐
│   React SPA (Vite)  │────▶│   FastAPI Backend (Python) │
│   Port 3000         │◀────│   Port 8000                │
└─────────────────────┘     └──────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
             Gemini 2.5 Flash   Google Sheets    Google Drive
              (OCR engine)      (gspread)       (photo upload)
```

### Tech Stack
- **Backend:** FastAPI + uvicorn, Python 3.14, uv for deps
- **Frontend:** React 19 + TypeScript + Vite, served separately in dev, nginx in Docker
- **OCR:** Google Gemini 2.5 Flash via `google-genai` SDK
- **Sheets:** gspread (service account auth)
- **Photos:** Google Drive upload → IMAGE() formula in Sheets
- **PDF processing:** pypdfium2 (zero external deps)
- **Docker:** docker-compose with backend + frontend services

### File Structure

```
cowell-mvp/
├── backend/
│   ├── pyproject.toml              # uv project config + deps
│   ├── Dockerfile
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app, CORS, routes
│   │   ├── config.py               # Settings from env vars
│   │   ├── models.py               # Pydantic schemas (Row, Session, etc.)
│   │   ├── ocr/
│   │   │   ├── __init__.py
│   │   │   ├── gemini.py           # Gemini OCR client + extraction
│   │   │   ├── image.py            # PDF→image, image compression
│   │   │   └── prompts.py          # OCR prompt templates
│   │   ├── sheets/
│   │   │   ├── __init__.py
│   │   │   ├── google_sheets.py    # Create/populate Google Sheet
│   │   │   └── google_drive.py     # Upload photos to Drive
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py           # POST /api/upload — files in
│   │   │   ├── ocr.py              # POST /api/ocr/{session_id} — run OCR
│   │   │   ├── rows.py             # PUT /api/rows/{session_id} — edit rows
│   │   │   └── register.py         # POST /api/register/{session_id} — → Sheets
│   │   └── sessions/
│   │       ├── __init__.py
│   │       └── memory.py           # In-memory session store (dict)
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf                  # Production static file serving
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts           # Axios/fetch wrapper
│       ├── types/
│       │   └── index.ts            # TypeScript interfaces
│       ├── pages/
│       │   ├── UploadPage.tsx      # Step 1: Upload PDFs + photos
│       │   ├── ProcessingPage.tsx  # Step 2: OCR progress
│       │   ├── EditPage.tsx        # Step 3: Editable table + photo attach
│       │   └── DonePage.tsx        # Step 4: Sheet URL + success
│       └── components/
│           ├── FileUploadZone.tsx   # Drag-drop file upload
│           ├── EditableRow.tsx      # Single editable row
│           └── PhotoPreview.tsx     # Photo thumbnail + upload
├── docker-compose.yml
├── .env.example
└── .gitignore (updated)
```

### User Flow (4 screens)
1. **Upload** — Drag-drop PDFs + photos, click "Run OCR"
2. **Processing** — Progress display, auto-transitions when done
3. **Edit/Confirm** — Editable table (7 columns), attach photos to rows, click "Register"
4. **Done** — Link to Google Sheet

### API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload` | Upload PDFs/images + photos. Returns `session_id` |
| POST | `/api/ocr/{session_id}` | Trigger OCR. Returns OCR rows |
| GET | `/api/rows/{session_id}` | Get current rows |
| PUT | `/api/rows/{session_id}` | Update all rows (after editing) |
| POST | `/api/register/{session_id}` | Create Google Sheet + populate + attach photos |

### OCR Strategy
- Prompt Gemini to return JSON array of row objects matching the 7-column schema
- Convert PDF pages → images via pypdfium2
- Send images in batches of 5-10 per Gemini call
- Merge results from multiple calls
- Image compression: 1200px max dimension, JPEG quality 0.85

### Google Sheets Integration
- Upload photos to Google Drive, make publicly viewable
- Reference in Sheets via `=IMAGE("https://lh3.googleusercontent.com/d/{FILE_ID}", 1)`
- **Tradeoff:** Photos become publicly accessible via Drive link. For production, would need signed URLs or private sharing.

### Implementation Steps (12 steps)
1. Project scaffolding (pyproject.toml, package.json, Docker files)
2. Backend core (config, models, sessions, FastAPI app)
3. OCR pipeline (image processing, Gemini client, prompts)
4. Upload + OCR routes
5. Edit routes (GET/PUT rows)
6. Google Sheets integration (Drive upload, Sheet creation)
7. Frontend — Upload page
8. Frontend — Processing page
9. Frontend — Edit page with photo attachment
10. Frontend — Done page
11. Docker integration + testing
12. README + accuracy report

### Assumptions
1. Single-user local dev — no auth, no multi-tenancy
2. User provides Gemini API key via `.env` file
3. User provides Google service account JSON (Sheets + Drive APIs enabled)
4. All uploaded photos are session-level; user manually assigns to rows
5. In-memory sessions (lost on restart) — acceptable for MVP
6. No proposal/pricing columns — only 7 inventory columns per spec

### Out of Scope
- Login/auth, database, production infra, multi-tenant, pricing features, polished UI, photo auto-matching

⏳ Waiting for your approval. Reply with:
- ✅ "Approved" or "Go ahead" to proceed
- ✏️ Any modifications you want before I start