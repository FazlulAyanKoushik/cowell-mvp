/**
 * PhotoPreview — displays a photo thumbnail or an empty placeholder.
 * Clicking triggers a file picker to attach a photo to a row.
 */

import { useRef } from "react";

interface Props {
  photoId: string;
  photoFiles: File[];
  onAttach: (file: File) => void;
}

export function PhotoPreview({ photoId, photoFiles, onAttach }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  // Find the file if photoId matches a filename
  const matchedFile = photoFiles.find(
    (f) => f.name === photoId || f.name.includes(photoId)
  );
  const previewUrl = matchedFile ? URL.createObjectURL(matchedFile) : null;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    inputRef.current?.click();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onAttach(file);
    }
  };

  if (previewUrl) {
    return (
      <img
        src={previewUrl}
        className="photo-thumb"
        alt="Photo"
        onClick={handleClick}
        title="Click to change photo"
      />
    );
  }

  return (
    <>
      <div className="photo-empty" onClick={handleClick} title="Click to attach photo">
        📷
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        style={{ display: "none" }}
        onChange={handleChange}
      />
    </>
  );
}
