/**
 * API client — thin wrapper around fetch for the Cowell OCR backend.
 *
 * In dev mode (Vite), requests to /api are proxied to localhost:8000.
 * In Docker (production), nginx proxies /api to the backend service.
 */

import type {
  UploadResponse,
  OCRResponse,
  RowsResponse,
  RegisterResponse,
  SurveyRow,
} from "../types";

const API_BASE = "/api";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

/** Upload survey files + photos, returns a new session ID */
export async function uploadFiles(
  surveyFiles: File[],
  photoFiles: File[]
): Promise<UploadResponse> {
  const form = new FormData();

  for (const f of surveyFiles) {
    form.append("survey_files", f);
  }
  for (const f of photoFiles) {
    form.append("photo_files", f);
  }

  return apiFetch<UploadResponse>("/upload", {
    method: "POST",
    body: form,
  });
}

/** Trigger OCR on a session's uploaded files */
export async function runOCR(sessionId: string): Promise<OCRResponse> {
  return apiFetch<OCRResponse>(`/ocr/${sessionId}`, {
    method: "POST",
  });
}

/** Get current rows for a session */
export async function getRows(sessionId: string): Promise<RowsResponse> {
  return apiFetch<RowsResponse>(`/rows/${sessionId}`);
}

/** Update all rows (after user editing) */
export async function updateRows(
  sessionId: string,
  rows: SurveyRow[]
): Promise<{ row_count: number; message: string }> {
  return apiFetch(`/rows/${sessionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rows),
  });
}

/** Add a single new row */
export async function addRow(
  sessionId: string,
  row: Omit<SurveyRow, "id">
): Promise<{ row: SurveyRow; message: string }> {
  return apiFetch(`/rows/${sessionId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(row),
  });
}

/** Delete a single row */
export async function deleteRow(
  sessionId: string,
  rowId: number
): Promise<{ message: string }> {
  return apiFetch(`/rows/${sessionId}/${rowId}`, {
    method: "DELETE",
  });
}

/** Register to Google Sheet */
export async function registerToSheet(
  sessionId: string
): Promise<RegisterResponse> {
  return apiFetch<RegisterResponse>(`/register/${sessionId}`, {
    method: "POST",
  });
}
