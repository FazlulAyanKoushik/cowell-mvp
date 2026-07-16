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
import { uploadFiles } from "../api/client";

export function UploadPage() {
  const navigate = useNavigate();
  const [surveyFiles, setSurveyFiles] = useState<File[]>([]);
  const [photoFiles, setPhotoFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalSizeKB =
    [...surveyFiles, ...photoFiles].reduce((sum, f) => sum + f.size, 0) / 1024;

  const handleRunOCR = async () => {
    if (!surveyFiles.length) {
      setError("Survey files are required");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await uploadFiles(surveyFiles, photoFiles);
      // Navigate to processing page with session info
      navigate(`/process/${result.session_id}`, {
        state: {
          fileCount: result.file_count,
          photoCount: result.photo_count,
        },
      });
    } catch (err: any) {
      setError(err.message || "Upload failed");
      setLoading(false);
    }
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

      <FileUploadZone
        label="現場写真（任意）"
        accept=".jpg,.jpeg,.png,.webp"
        hint="後で行に紐付ける写真をまとめてアップロード"
        files={photoFiles}
        onFilesChange={setPhotoFiles}
      />

      {totalSizeKB > 0 && (
        <div className="card" style={{ fontSize: "0.85rem", color: "#999", textAlign: "center" }}>
          送信データ: 約 {totalSizeKB.toFixed(0)} KB（{surveyFiles.length + photoFiles.length} ファイル）
        </div>
      )}

      {error && (
        <div className="status error">⚠️ {error}</div>
      )}

      <button
        className="btn btn-primary"
        disabled={!surveyFiles.length || loading}
        onClick={handleRunOCR}
      >
        {loading ? (
          <>
            <div className="spinner" /> アップロード中...
          </>
        ) : (
          `OCR を実行（${surveyFiles.length} ファイル）`
        )}
      </button>
    </div>
  );
}
