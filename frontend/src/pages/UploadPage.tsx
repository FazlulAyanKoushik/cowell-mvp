/**
 * UploadPage — Step 1: Upload survey PDFs/images + photos.
 *
 * Two upload zones: one for survey documents (PDFs/images),
 * one for photos (to be attached to rows later).
 * "Run OCR" button triggers processing and navigates to ProcessingPage.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileUploadZone } from "../components/FileUploadZone";

const DEFAULT_LLM_INSTRUCTIONS = `Extract every visible fixture inventory row. Carefully carry values through merged cells and ditto marks. Preserve handwritten text exactly; use notes for uncertainty.`;

export function UploadPage() {
  const navigate = useNavigate();
  const [surveyFiles, setSurveyFiles] = useState<File[]>([]);
  const [instructions, setInstructions] = useState(DEFAULT_LLM_INSTRUCTIONS);
  const [error, setError] = useState<string | null>(null);

  const totalSizeKB =
    surveyFiles.reduce((sum, f) => sum + f.size, 0) / 1024;

  const handleRunOCR = async () => {
    if (!surveyFiles.length) {
      setError("Survey files are required");
      return;
    }

    setError(null);
    navigate("/process", { state: { surveyFiles, instructions } });
  };

  return (
    <div>
      <FileUploadZone
        label="調査シート（必須）"
        accept=".pdf,.jpg,.jpeg,.png,.webp,.gif"
        hint="PNG / JPG / WEBP / GIF / PDF — 複数ファイル対応"
        files={surveyFiles}
        onFilesChange={setSurveyFiles}
      />

      <div className="card">
        <label htmlFor="llm-instructions" style={{ display: "block", fontWeight: 700, marginBottom: 8 }}>
          Additional instructions for LLM (optional)
        </label>
        <textarea
          id="llm-instructions"
          className="cell-input"
          value={instructions}
          onChange={(event) => setInstructions(event.target.value)}
          rows={4}
          style={{ width: "100%", resize: "vertical" }}
        />
      </div>

      {totalSizeKB > 0 && (
        <div className="card" style={{ fontSize: "0.85rem", color: "#999", textAlign: "center" }}>
          送信データ: 約 {totalSizeKB.toFixed(0)} KB（{surveyFiles.length} ファイル）
        </div>
      )}

      {error && (
        <div className="status error">⚠️ {error}</div>
      )}

      <button
        className="btn btn-primary"
        disabled={!surveyFiles.length}
        onClick={handleRunOCR}
      >
        {`OCR を実行（${surveyFiles.length} ファイル）`}
      </button>
    </div>
  );
}
