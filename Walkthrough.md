# Walkthrough: Frontend-Owned OCR Review and Google Sheets Export

**Completed:** 2026-07-21  
**Related Task:** Task.md

## Summary

The backend now exposes one stateless OCR endpoint. The browser owns the OCR
rows after extraction, supports review and editing locally, and creates Google
Sheets directly in the signed-in user's account.

## Changes Made

### Backend OCR API

- Replaced the routed upload/session/OCR sequence with `POST /api/ocr`.
- The endpoint accepts survey PDFs/images plus optional instruction text,
  renders/compresses/batches the surveys, and returns rows.
- Gemini receives the text instructions as additional extraction context.

### Frontend workflow

- The upload screen now has survey upload and an editable default instruction field.
- Processing sends the files to the single OCR endpoint and transfers returned
  rows to the edit screen.
- Editing, adding, deleting, filtering, and row numbering happen entirely in
  frontend state.

### Google Sheets export

- Added browser-side Google Identity Services OAuth and direct Google Sheets
  API calls.
- The user authorizes with their own Google account; no backend token or
  service account is used for registration.
- The generated Sheet writes the Japanese headers and reviewed rows.

### Configuration and docs

- Added `frontend/.env.example` for `VITE_GOOGLE_CLIENT_ID`.
- Docker builds the frontend with its `frontend/.env` configuration.
- Updated README with the new architecture and OAuth Web-client requirement.

## How to Test

1. Set `GEMINI_API_KEY` in `backend/.env`.
2. Create a Google OAuth **Web application** client, add `http://localhost:3000`
   as an authorized JavaScript origin, enable the Sheets API, then set its ID in
   `frontend/.env` as `VITE_GOOGLE_CLIENT_ID`.
3. Start backend and frontend using the README commands.
4. Upload a survey PDF/image and review or edit the default LLM instruction text.
5. Edit rows, click Google Sheet registration, approve Google consent, and
   verify the created Sheet in the signed-in user's Drive.

## Known Limitations / Follow-ups

- The former photo-upload feature is not part of this frontend-only workflow;
  the output keeps an empty photo column for schema compatibility.
- OCR results are browser state, so refreshing the edit page discards them.
- The legacy backend session/Google Drive modules remain in the repository but
  are no longer mounted or used by the active API.
- Gemini JSON is retried once if malformed. If both attempts are truncated, the
  API returns only fully completed rows and logs the recovery count.
