/**
 * EditableRow — a single table row with inline-editable cells.
 */

import type { SurveyRow } from "../types";
import { PhotoPreview } from "./PhotoPreview";

interface Props {
  row: SurveyRow;
  photoFiles: File[];
  onChange: (id: number, field: keyof SurveyRow, value: string) => void;
  onAttachPhoto: (id: number, file: File) => void;
  onDelete: (id: number) => void;
}

const EDITABLE_FIELDS: (keyof Omit<SurveyRow, "id" | "photo_id">)[] = [
  "floor",
  "location",
  "fixture_model",
  "existing_product",
  "quantity",
  "notes",
];

export function EditableRow({
  row,
  photoFiles,
  onChange,
  onAttachPhoto,
  onDelete,
}: Props) {
  return (
    <tr>
      <td style={{ width: 50, textAlign: "center", color: "#999", fontSize: "0.8rem" }}>
        {row.id}
      </td>
      {EDITABLE_FIELDS.map((field) => (
        <td key={field}>
          <input
            className="cell-input"
            value={row[field]}
            onChange={(e) => onChange(row.id, field, e.target.value)}
          />
        </td>
      ))}
      <td style={{ textAlign: "center" }}>
        <PhotoPreview
          photoId={row.photo_id}
          photoFiles={photoFiles}
          onAttach={(file) => onAttachPhoto(row.id, file)}
        />
      </td>
      <td style={{ width: 60, textAlign: "center" }}>
        <button
          className="row-btn delete"
          onClick={() => onDelete(row.id)}
          title="Delete row"
        >
          🗑
        </button>
      </td>
    </tr>
  );
}
