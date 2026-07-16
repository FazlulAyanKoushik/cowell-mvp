/** TypeScript interfaces matching the backend Pydantic models */

export interface SurveyRow {
  id: number;
  floor: string;
  location: string;
  fixture_model: string;
  existing_product: string;
  photo_id: string;
  quantity: string;
  notes: string;
}

export type SessionStatus =
  | "uploaded"
  | "ocr_running"
  | "ocr_done"
  | "registering"
  | "registered"
  | "error";

export interface UploadResponse {
  session_id: string;
  file_count: number;
  photo_count: number;
}

export interface OCRResponse {
  session_id: string;
  row_count: number;
  rows: SurveyRow[];
}

export interface RowsResponse {
  session_id: string;
  status: SessionStatus;
  row_count: number;
  rows: SurveyRow[];
}

export interface RegisterResponse {
  session_id: string;
  sheet_url: string;
  row_count: number;
}

export interface HealthResponse {
  status: string;
  model: string;
}

export const COLUMN_LABELS: Record<keyof Omit<SurveyRow, "id" | "photo_id">, string> = {
  floor: "フロア",
  location: "設置場所",
  fixture_model: "器具品番",
  existing_product: "既設商品名",
  quantity: "数量",
  notes: "備考",
};
