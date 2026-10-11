# TWAIN PDF Emulator Requirements

## As Is

Nospe has a FastAPI backend with scanner, settings, filesystem, scan, and Paperless stub endpoints. The scanner list is mocked as `EPSON DS-410`; there is no upload spool, no PDF rasterization, no minimal emulator upload page, and no native TWAIN Data Source module.

## To Be

Nospe exposes a local PDF emulator spool. A user opens a minimal backend-served web page, drops or selects one PDF, and the backend stores exactly one active scan job under the local app data directory. The PDF is rendered to grayscale page images at 300 DPI immediately after upload. A Windows x64 TWAIN Data Source module can be built separately and installed as `Nospe Virtual Scanner`; it reads the manifest/pages prepared by the backend.

## Requirements

1. `POST /emulator/upload` accepts one multipart PDF file and rejects empty files, non-PDF files, and files larger than the configured maximum.
2. Successful upload atomically replaces the active job only when no active job is in `transferring` state.
3. Successful upload writes `original.pdf`, page images, and `manifest.json` to `%LOCALAPPDATA%\Nospe\twain-emulator\active` by default.
4. `GET /emulator/job` returns a typed active-job status or `active: false`.
5. `POST /emulator/job/consume` marks the active job consumed and removes the active spool.
6. The backend serves a minimal upload page at `/emulator` with only an icon-style drop target, click-select upload, and drag-and-drop upload behavior.
7. A Windows x64 native TWAIN module scaffold exports `DS_Entry`, names itself `Nospe Virtual Scanner`, and reads the JSON manifest path configured for the spool.

## Acceptance Criteria

1. Multipart PDF upload returns JSON with `active: true`, `job_id`, `page_count`, `dpi: 300`, `color_mode: "gray"`, and page image paths.
2. Uploading a text file returns HTTP 400; uploading an empty PDF returns HTTP 400; uploading beyond max bytes returns HTTP 413.
3. When `manifest.json` has status `transferring`, another upload returns HTTP 409 and does not overwrite existing files.
4. `GET /emulator/job` returns `active: false` after consume.
5. The upload page source contains one file input accepting PDFs and JavaScript handlers for click, change, dragover, drop, and upload.
6. The native module source and CMake project can be configured on Windows x64 when TWAIN headers are supplied.

## Testing Plan

- Add backend pytest tests first using FastAPI `TestClient` and a temporary spool directory.
- Unit-test the spool service directly for active/transferring/consume behavior.
- Integration-test upload validation, generated manifest shape, and minimal HTML content.
- Build-test the frontend TypeScript app unchanged enough to ensure existing Nospe UI still compiles.
- Configure-test the native CMake project only if CMake and TWAIN headers are available; otherwise report it as an external verification gap.

## Implementation Plan

1. Add backend tests for upload, job status, consume, rejection, and transferring conflict; run them and confirm they fail because endpoints are missing.
2. Add emulator Pydantic models and a focused spool service that validates file bytes, renders pages, writes atomically, reads status, and consumes jobs.
3. Wire FastAPI routes and minimal HTML page; run backend tests until they pass.
4. Add Python dependencies for multipart upload, PDF rendering, images, and pytest/test client support.
5. Add a native `twain_ds` CMake/C++ scaffold with exported `DS_Entry`, product identity constants, manifest loading, and install documentation.
6. Run backend tests and frontend build. Run native configure/build only when local prerequisites exist.
