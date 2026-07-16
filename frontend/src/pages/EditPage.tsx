/**
 * EditPage — Step 3: Editable table with inline editing and photo attachment.
 *
 * Displays OCR results in a table where every cell is an editable input.
 * Users can add/delete rows and attach photos to individual rows.
 * "Register" button sends the (edited) data to create a Google Sheet.
 */

import { useEffect, useState, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { SurveyRow } from "../types";
import { COLUMN_LABELS } from "../types";
import { getRows, updateRows, addRow, deleteRow, registerToSheet } from "../api/client";
import { EditableRow } from "../components/EditableRow";

export function EditPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [rows, setRows] = useState<SurveyRow[]>([]);
  const [photoFiles, setPhotoFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [registering, setRegistering] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  // Load rows on mount
  useEffect(() => {
    if (!sessionId) return;
    getRows(sessionId)
      .then((data) => {
        setRows(data.rows);
        setLoading(false);
      })
      .catch((err: any) => {
        setError(err.message);
        setLoading(false);
      });
  }, [sessionId]);

  // Cell editing handler
  const handleCellChange = useCallback(
    (id: number, field: keyof SurveyRow, value: string) => {
      setRows((prev) =>
        prev.map((r) => (r.id === id ? { ...r, [field]: value } : r))
      );
    },
    []
  );

  // Attach photo to a row
  const handleAttachPhoto = useCallback(
    (rowId: number, file: File) => {
      // Add to photo files list
      setPhotoFiles((prev) => {
        if (!prev.find((f) => f.name === file.name)) {
          return [...prev, file];
        }
        return prev;
      });

      // Update the row's photo_id
      setRows((prev) =>
        prev.map((r) => (r.id === rowId ? { ...r, photo_id: file.name } : r))
      );
    },
    []
  );

  // Delete a row
  const handleDelete = useCallback((id: number) => {
    setRows((prev) => prev.filter((r) => r.id !== id));
  }, []);

  // Add a new empty row
  const handleAddRow = useCallback(() => {
    setRows((prev) => [
      ...prev,
      {
        id: prev.length + 1,
        floor: "",
        location: "",
        fixture_model: "",
        existing_product: "",
        photo_id: "",
        quantity: "",
        notes: "",
      },
    ]);
  }, []);

  // Register to Google Sheet
  const handleRegister = async () => {
    if (!sessionId) return;
    setRegistering(true);
    setError(null);

    try {
      // First, save the edited rows to the backend
      await updateRows(sessionId, rows);

      // Then trigger registration
      const result = await registerToSheet(sessionId);
      navigate(`/done/${sessionId}`, {
        state: { sheetUrl: result.sheet_url, rowCount: result.row_count },
      });
    } catch (err: any) {
      setError(err.message);
      setRegistering(false);
    }
  };

  // Filter rows by search term
  const filteredRows = rows.filter((row) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return Object.values(row).some(
      (val) => typeof val === "string" && val.toLowerCase().includes(term)
    );
  });

  const fields = Object.keys(COLUMN_LABELS) as (keyof typeof COLUMN_LABELS)[];

  if (loading) {
    return (
      <div className="status loading" style={{ justifyContent: "center" }}>
        <div className="spinner" /> データを読み込み中...
      </div>
    );
  }

  return (
    <div>
      {/* Toolbar */}
      <div className="card" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ fontSize: "0.85rem", color: "#666" }}>
          {rows.length} 行
        </span>
        <input
          className="cell-input"
          placeholder="🔍 検索..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ width: 200 }}
        />
        <div style={{ flex: 1 }} />
        <button className="btn btn-secondary" onClick={handleAddRow}>
          ＋ 行を追加
        </button>
        <button
          className="btn btn-success"
          onClick={handleRegister}
          disabled={registering || !rows.length}
        >
          {registering ? (
            <>
              <div className="spinner" style={{ borderTopColor: "white" }} /> 登録中...
            </>
          ) : (
            "📊 Google Sheet に登録"
          )}
        </button>
      </div>

      {error && (
        <div className="status error">⚠️ {error}</div>
      )}

      {/* Editable Table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div className="table-wrap" style={{ maxHeight: "70vh", overflow: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ width: 50 }}>#</th>
                {fields.map((field) => (
                  <th key={field}>{COLUMN_LABELS[field]}</th>
                ))}
                <th style={{ width: 60 }}>写真</th>
                <th style={{ width: 60 }}></th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row) => (
                <EditableRow
                  key={row.id}
                  row={row}
                  photoFiles={photoFiles}
                  onChange={handleCellChange}
                  onAttachPhoto={handleAttachPhoto}
                  onDelete={handleDelete}
                />
              ))}
              {filteredRows.length === 0 && (
                <tr>
                  <td colSpan={fields.length + 3} style={{ textAlign: "center", padding: 32, color: "#999" }}>
                    {rows.length === 0 ? "データがありません" : "検索結果がありません"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
