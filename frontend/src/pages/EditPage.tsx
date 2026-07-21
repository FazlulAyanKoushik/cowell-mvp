/** EditPage — browser-owned review, editing, and Google Sheets export. */

import { useCallback, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { createGoogleSheet } from "../googleSheets";
import type { SurveyRow } from "../types";
import { COLUMN_LABELS } from "../types";

export function EditPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const initialRows = (location.state as { rows?: SurveyRow[] } | null)?.rows ?? [];
  const [rows, setRows] = useState<SurveyRow[]>(initialRows);
  const [error, setError] = useState<string | null>(null);
  const [registering, setRegistering] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const handleCellChange = useCallback((id: number, field: keyof SurveyRow, value: string) => {
    setRows((current) => current.map((row) => row.id === id ? { ...row, [field]: value } : row));
  }, []);

  const handleDelete = useCallback((id: number) => {
    setRows((current) => current.filter((row) => row.id !== id).map((row, index) => ({ ...row, id: index + 1 })));
  }, []);

  const handleAddRow = useCallback(() => {
    setRows((current) => [...current, {
      id: current.length + 1, floor: "", location: "", fixture_model: "", existing_product: "", photo_id: "", quantity: "", notes: "",
    }]);
  }, []);

  const handleRegister = async () => {
    if (!rows.length) return;
    setRegistering(true);
    setError(null);
    try {
      const sheetUrl = await createGoogleSheet(rows);
      navigate("/done", { state: { sheetUrl, rowCount: rows.length } });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Google Sheet registration failed");
      setRegistering(false);
    }
  };

  const fields = Object.keys(COLUMN_LABELS) as (keyof typeof COLUMN_LABELS)[];
  const filteredRows = rows.filter((row) => !searchTerm || Object.values(row).some(
    (value) => typeof value === "string" && value.toLowerCase().includes(searchTerm.toLowerCase()),
  ));

  if (!initialRows.length && !rows.length) {
    return <div className="status error">OCR data is not available. Please start a new upload.</div>;
  }

  return <div>
    <div className="card" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
      <span style={{ fontSize: "0.85rem", color: "#666" }}>{rows.length} 行</span>
      <input className="cell-input" placeholder="🔍 検索..." value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} style={{ width: 200 }} />
      <div style={{ flex: 1 }} />
      <button className="btn btn-secondary" onClick={handleAddRow}>＋ 行を追加</button>
      <button className="btn btn-success" onClick={handleRegister} disabled={registering || !rows.length}>
        {registering ? <><div className="spinner" style={{ borderTopColor: "white" }} /> 登録中...</> : "📊 Google Sheet に登録"}
      </button>
    </div>
    {error && <div className="status error">⚠️ {error}</div>}
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      <div className="table-wrap" style={{ maxHeight: "70vh", overflow: "auto" }}>
        <table><thead><tr><th style={{ width: 50 }}>#</th>{fields.map((field) => <th key={field}>{COLUMN_LABELS[field]}</th>)}<th style={{ width: 60 }} /></tr></thead>
          <tbody>{filteredRows.map((row) => <tr key={row.id}><td style={{ textAlign: "center", color: "#999" }}>{row.id}</td>
            {fields.map((field) => <td key={field}><input className="cell-input" value={row[field]} onChange={(event) => handleCellChange(row.id, field, event.target.value)} /></td>)}
            <td style={{ textAlign: "center" }}><button className="row-btn delete" onClick={() => handleDelete(row.id)} title="Delete row">🗑</button></td>
          </tr>)}{filteredRows.length === 0 && <tr><td colSpan={fields.length + 2} style={{ textAlign: "center", padding: 32, color: "#999" }}>検索結果がありません</td></tr>}</tbody>
        </table>
      </div>
    </div>
  </div>;
}
