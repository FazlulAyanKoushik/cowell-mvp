/**
 * App — top-level component with routing and step indicator.
 */

import { BrowserRouter, Routes, Route, useLocation, Link } from "react-router-dom";
import { UploadPage } from "./pages/UploadPage";
import { ProcessingPage } from "./pages/ProcessingPage";
import { EditPage } from "./pages/EditPage";
import { DonePage } from "./pages/DonePage";

const STEPS = [
  { path: "/", label: "① アップロード" },
  { path: "/process", label: "② OCR 処理" },
  { path: "/edit", label: "③ 編集" },
  { path: "/done", label: "④ 完了" },
];

function StepIndicator() {
  const location = useLocation();

  const activeIndex = STEPS.findIndex((step) => {
    if (step.path === "/") return location.pathname === "/";
    return location.pathname.startsWith(step.path);
  });

  return (
    <div className="steps">
      {STEPS.map((step, i) => (
        <div
          key={step.path}
          className={`step ${i === activeIndex ? "active" : ""} ${
            i < activeIndex ? "done" : ""
          }`}
        >
          {step.label}
        </div>
      ))}
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Link to="/" style={{ textDecoration: "none", color: "inherit" }}>
          <header className="app-header">
            <h1>📋 Cowell OCR</h1>
            <p>手書き調査シート → Google Spreadsheet</p>
          </header>
        </Link>

        <StepIndicator />

        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/process" element={<ProcessingPage />} />
          <Route path="/edit" element={<EditPage />} />
          <Route path="/done" element={<DonePage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
