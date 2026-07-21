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

export interface OCRResponse {
  row_count: number;
  rows: SurveyRow[];
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
