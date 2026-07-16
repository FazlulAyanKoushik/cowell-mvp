/**
 * FileUploadZone — drag-and-drop or click-to-upload area.
 * Supports multiple files and shows a file list with remove buttons.
 */

import { useRef, useState, useCallback } from "react";

interface Props {
  label: string;
  accept: string;
  hint: string;
  files: File[];
  onFilesChange: (files: File[]) => void;
}

export function FileUploadZone({ label, accept, hint, files, onFilesChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = useCallback(
    (newFiles: FileList | null) => {
      if (!newFiles) return;
      const added = Array.from(newFiles);
      onFilesChange([...files, ...added]);
    },
    [files, onFilesChange]
  );

  const removeFile = useCallback(
    (index: number) => {
      onFilesChange(files.filter((_, i) => i !== index));
    },
    [files, onFilesChange]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  return (
    <div className="card">
      <h2>{label}</h2>
      <div
        className={`upload-zone ${dragOver ? "drag-over" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple
          style={{ display: "none" }}
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div className="icon">📄</div>
        <p>
          <strong>クリックまたはドラッグ</strong>してファイルを選択
        </p>
        <p className="hint">{hint}</p>
      </div>
      {files.length > 0 && (
        <div className="file-list">
          {files.map((f, i) => (
            <div key={`${f.name}-${i}`} className="file-item">
              <span className="file-item-name">{f.name}</span>
              <span className="file-item-size">
                {(f.size / 1024).toFixed(1)} KB
              </span>
              <button className="file-remove" onClick={() => removeFile(i)}>
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
