/**
 * ProcessingPage — Step 2: Shows OCR progress, auto-transitions when done.
 *
 * Polls the backend or waits for the OCR result, then navigates to EditPage.
 */

import { useEffect, useState, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { runOCR } from "../api/client";

export function ProcessingPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<"converting" | "ocr" | "done" | "error">("converting");
  const [message, setMessage] = useState("PDF ページを画像に変換中...");
  const [progress, setProgress] = useState(0);
  const startTime = useRef(Date.now());
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!sessionId) return;

    // Simulate conversion progress
    const progressTimer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime.current) / 1000));
      setProgress((prev) => Math.min(prev + 2, 40));
    }, 200);

    // After a brief "converting" phase, start OCR
    const convertTimer = setTimeout(() => {
      setStatus("ocr");
      setMessage("Gemini に送信中...");
      setProgress(50);

      runOCR(sessionId)
        .then((result) => {
          setProgress(100);
          setStatus("done");
          setMessage(`完了！ ${result.row_count} 行を抽出しました`);

          // Navigate to edit page after brief pause
          setTimeout(() => {
            navigate(`/edit/${sessionId}`);
          }, 1200);
        })
        .catch((err: any) => {
          setStatus("error");
          setMessage(`OCR エラー: ${err.message}`);
          clearInterval(progressTimer);
        });
    }, 1500);

    return () => {
      clearInterval(progressTimer);
      clearTimeout(convertTimer);
    };
  }, [sessionId, navigate]);

  return (
    <div className="card" style={{ textAlign: "center", padding: "48px 24px" }}>
      {status !== "error" && (
        <div className="spinner" style={{ width: 36, height: 36, margin: "0 auto 20px" }} />
      )}

      <div
        className={`status ${status === "error" ? "error" : status === "done" ? "success" : "loading"}`}
        style={{ justifyContent: "center" }}
      >
        {message}
      </div>

      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>

      <p style={{ fontSize: "0.85rem", color: "#999", marginTop: 8 }}>
        {elapsed}s 経過
      </p>

      {status === "error" && (
        <button
          className="btn btn-secondary"
          style={{ marginTop: 16 }}
          onClick={() => navigate("/")}
        >
          トップに戻る
        </button>
      )}
    </div>
  );
}
