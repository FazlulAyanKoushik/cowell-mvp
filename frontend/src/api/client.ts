/**
 * API client — thin wrapper around fetch for the Cowell OCR backend.
 *
 * In dev mode (Vite), requests to /api are proxied to localhost:8000.
 * In Docker (production), nginx proxies /api to the backend service.
 */

import type {
  OCRResponse,
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

/** Upload surveys and optional text instructions, then return OCR rows. */
export async function runOCR(
  surveyFiles: File[],
  instructions: string
): Promise<OCRResponse> {
  const form = new FormData();
  for (const f of surveyFiles) {
    form.append("survey_files", f);
  }
  form.append("instructions", instructions);

  return apiFetch<OCRResponse>("/ocr", {
    method: "POST",
    body: form,
  });
}
