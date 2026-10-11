// Zentrale Typen für Nospe.
// Diese müssen exakt zum Backend-API-Contract (FastAPI, Port 8765) passen,
// damit das echte Backend später ohne Frontend-Änderungen anschließbar ist.

export type ColorMode = "gray" | "color" | "bw";

export type ScannerKind = "twain" | "wia" | "escl";

export type Scanner = {
  /** Stabil und eindeutig, z. B. `twain:EPSON DS-410`, `wia:{…}`, `escl:<UUID>`. */
  id: string;
  name: string;
  kind: ScannerKind;
  /** Weitere Zugänge zum selben Gerät (z. B. WIA, wenn TWAIN bevorzugt wurde). */
  also_via: string[];
};

export type ScanProfile = {
  id: string;
  name: string;
  duplex: boolean;
  adf: boolean;
  dpi: number;
  color_mode: ColorMode;
};

export type ScanRequest = {
  scanner_id: string;
  profile_id: string;
  title: string;
  color_mode: ColorMode;
  push_to_paperless: boolean;
};

// Epson-inspirierte Scan-Optionen. Der Farbmodus wird an das Backend
// übergeben; weitere Optionen bleiben vorerst lokale UI-Einstellungen.
export type DocumentSource = "adf_simplex" | "adf_duplex" | "flatbed";
export type DocumentSize =
  | "auto"
  | "a4"
  | "a5"
  | "letter"
  | "legal";
export type ImageType = "color" | "gray" | "bw";
export type Resolution = 150 | 200 | 300 | 400 | 600;
export type Rotation = 0 | 90 | 180 | 270;
export type ImageFormat = "pdf" | "pdf_a" | "jpeg" | "png" | "webp";

export type ScanOptions = {
  source: DocumentSource;
  size: DocumentSize;
  imageType: ImageType;
  resolution: Resolution;
  rotation: Rotation;
  mirrorVertical: boolean;
  correctSkew: boolean;
  editAfterScan: boolean;
  format: ImageFormat;
  outputDir: string;
};

export type ScanResponse = {
  ok: boolean;
  file_path: string;
  uploaded_to_paperless: boolean;
  paperless_document_id?: string;
  paperless_error?: string;
};

export type AppSettings = {
  scan_output_dir: string;
  paperless_url: string;
  // Token wird nie an das Frontend zurückgegeben – nur ob einer gesetzt ist.
  paperless_token_set: boolean;
  folder_favorites: FolderFavorite[];
  selected_scanner_id?: string | null;
};

// Beim Speichern darf der Token optional mitgesendet werden.
export type SaveSettingsRequest = {
  scan_output_dir: string;
  paperless_url: string;
  paperless_token?: string;
  // Optional, damit schnelle Zielordnerwechsel Favoriten nicht überschreiben.
  folder_favorites?: FolderFavorite[];
  selected_scanner_id?: string | null;
};

export type FolderFavoriteIcon =
  | "folder"
  | "folder-check"
  | "briefcase"
  | "archive"
  | "star"
  | "hard-drive";

export type FolderFavorite = {
  id: string;
  label: string;
  path: string;
  icon: FolderFavoriteIcon;
};

export type HealthResponse = {
  ok: boolean;
  version: string;
};

export type ScannersResponse = {
  scanners: Scanner[];
  /** Unix-Zeit des letzten Suchlaufs; null, solange noch nie gesucht wurde. */
  updated_at: number | null;
  /** Während eines Scans ist die Liste der Stand davor. */
  scanning: boolean;
  /** Fehler je Zugangsart, z. B. { twain: "TWAIN DSM nicht ladbar" }. */
  errors: Record<string, string>;
};

export type TwainStatusResponse = {
  platform: string;
  python_bitness: number;
  twain_supported: boolean;
  dsm_available: boolean;
  pytwain_version?: string | null;
  source_count: number;
  sources: string[];
  error?: string | null;
  hints: string[];
};

export type ProfilesResponse = {
  profiles: ScanProfile[];
};

export type PaperlessTestResponse = {
  ok: boolean;
  message: string;
};

export type BackendStatus = "checking" | "online" | "offline";

export type LogLevel = "info" | "success" | "warn" | "error";

export type LogEntry = {
  id: number;
  time: string; // HH:MM:SS
  level: LogLevel;
  message: string;
};
