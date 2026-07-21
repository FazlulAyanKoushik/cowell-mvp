# Task: Frontend-Owned OCR Review and Google Sheets Export

**Status:** Complete  
**Approved:** Yes — 2026-07-21

## Objective

Expose one backend OCR API and move row editing plus Google Sheets registration to the frontend.

## Checklist

- [x] Replace the session-based backend workflow with one multipart OCR endpoint
- [x] Accept optional plain-text LLM instructions with OCR uploads
- [x] Update the frontend upload and processing flow
- [x] Keep extracted-row editing entirely in frontend state
- [x] Add browser-side Google OAuth and Google Sheets export
- [x] Update documentation and verify builds
- [x] Replace instruction-file upload with an editable default instruction field
- [x] Retry malformed Gemini JSON and recover completed rows when necessary
- [x] Ensure Docker frontend builds load frontend/.env

## Notes

- Instruction uploads are plain-text `.txt` files only.
- Frontend Google OAuth requires a Google OAuth **Web application** client ID.
