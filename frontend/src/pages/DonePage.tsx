/**
 * DonePage — Step 4: Shows the Google Sheet link and summary.
 */

import { useLocation, Link } from "react-router-dom";

export function DonePage() {
  const location = useLocation();
  const state = location.state as { sheetUrl?: string; rowCount?: number } | null;

  const sheetUrl = state?.sheetUrl;
  const rowCount = state?.rowCount ?? 0;

  return (
    <div className="card" style={{ textAlign: "center", padding: "48px 24px" }}>
      <div style={{ fontSize: "3rem", marginBottom: 16 }}>✅</div>
      <h2 style={{ fontSize: "1.3rem", marginBottom: 8 }}>登録完了</h2>
      <p style={{ color: "#666", marginBottom: 24 }}>
        {rowCount} 行のデータを Google Sheet に登録しました
      </p>

      {sheetUrl ? (
        <a
          href={sheetUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="sheet-link"
        >
          📊 Google Sheet を開く
        </a>
      ) : (
        <p style={{ color: "#999" }}>Sheet URL is not available</p>
      )}

      <div style={{ marginTop: 32 }}>
        <Link to="/" className="btn btn-secondary">
          新しい調査を始める
        </Link>
      </div>
    </div>
  );
}
