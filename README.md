# Cowell OCR — Phase 1 MVP

Convert handwritten Japanese building-survey sheets into an editable Google
Spreadsheet. The backend performs OCR only; review, editing, and Sheet creation
all happen in the browser.

## User Flow

1. Upload PDF/image survey sheets and optionally adjust the default LLM instruction text.
2. The single backend endpoint converts PDFs to images, compresses and batches pages, then returns structured OCR rows.
3. Review, edit, add, or delete rows locally in the frontend.
4. Sign in with Google in the browser and create a Sheet in the signed-in user's Drive.

## Architecture

```
React SPA (Vite)              FastAPI
  review/edit/export   -->    POST /api/ocr
       |                         |
       +--> Google Sheets        +--> Gemini OCR
```

- **Backend:** FastAPI, pypdfium2, Pillow, and the Google GenAI SDK. It does not store sessions or create Sheets.
- **Frontend:** React 19, TypeScript, and Google Identity Services. Rows exist in frontend state after OCR.
- **Google Sheets:** created directly by the signed-in browser user via the Google Sheets API.

## Configuration

### Backend

Create `backend/.env`:

```env
GEMINI_API_KEY=your-gemini-api-key
# Optional
GEMINI_MODEL=gemini-3.5-flash
```

### Frontend

Create `frontend/.env` from [frontend/.env.example](frontend/.env.example):

```env
VITE_GOOGLE_CLIENT_ID=your-web-oauth-client-id.apps.googleusercontent.com
```

Create a Google OAuth **Web application** client in Google Cloud Console (a
Desktop OAuth client cannot authorize a browser SPA). Register your frontend
origins, such as `http://localhost:3000`, and enable the Google Sheets API.
The client ID is safe to expose; never put a client secret in the frontend.

## Local Development

```bash
# Terminal 1
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Vite proxies `/api` to port 8000.

## Docker

Set `GEMINI_API_KEY` in `backend/.env` and `VITE_GOOGLE_CLIENT_ID` in
`frontend/.env`, then run:

```bash
docker compose up --build
```

- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`

## OCR API

`POST /api/ocr` as multipart form data:

- `survey_files`: one or more PDFs, JPG, PNG, WEBP, or GIF survey files (required)
- `instructions`: optional text entered in the Additional instructions for LLM field

Response:

```json
{
  "row_count": 1,
  "rows": [{
    "id": 1,
    "floor": "3F",
    "location": "ロビー",
    "fixture_model": "FR-42540-RS",
    "existing_product": "φ100DL E17 (L)",
    "photo_id": "",
    "quantity": "36",
    "notes": "調光"
  }]
}
```

The Sheet includes the original photo column for schema compatibility, but this
frontend-only workflow does not upload or attach photos.

## OCR Notes

Handwritten values, ditto marks, merged cells, and margin notes can still need
manual correction. The review table is therefore part of the intended workflow,
not a fallback.

## License

MIT
