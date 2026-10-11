# Separate emulator and color scan

## As Is

The release bundle starts and ships `nospe-emulator.exe`. The virtual TWAIN data source can therefore become the first selected source. Its spool rasterizer unconditionally renders uploaded PDFs as grayscale. Physical TWAIN scans set `ICAP_PIXELTYPE`, but do not set the matching bit depth and silently ignore failures to apply color capabilities.

## To Be

The normal Nospe installer contains and starts only the backend and lists the Windows-installed TWAIN sources. The emulator remains an opt-in, separately built and manually started diagnostic tool. A color scan must request RGB plus 24-bit depth; if a driver cannot provide RGB, the scan must fail clearly instead of saving an unexpected grayscale document. The standalone emulator must preserve uploaded PDF colors.

## Requirements

1. Exclude the emulator sidecar and its automatic lifecycle from the production Tauri bundle.
2. Keep a documented, separately buildable and launchable emulator executable.
3. Set TWAIN color mode with `ICAP_PIXELTYPE=TWPT_RGB` and `ICAP_BITDEPTH=24`; use 8-bit gray and 1-bit black/white equivalents.
4. Treat inability to apply the requested color capability as a visible scan error.
5. Render standalone-emulator uploads in RGB and declare the emulator job as `color`.

## Acceptance Criteria

1. `tauri.conf.json` includes only `nospe-backend` in `externalBin`, and the Rust app contains no emulator startup or shutdown state.
2. The standalone emulator build script produces `nospe-emulator.exe` outside the Tauri bundle and its documentation gives a direct start command.
3. Unit tests assert the color, gray, and black/white TWAIN capability values and an RGB rendering path for emulator uploads.
4. A failing required color capability raises a `ScanError` naming the color mode; optional scanner capabilities remain best effort.
5. Backend tests, frontend build, Rust check, and an installer inspection confirm no `nospe-emulator.exe` is installed with Nospe.

## Testing Plan

- Add focused unit tests before changing TWAIN profile application and emulator rendering.
- Run the affected backend tests, then the full backend suite.
- Build the frontend, run `cargo check`, build the Tauri installer, and inspect installed files after upgrade.
- Start the standalone emulator separately and verify its job reports `color` after a color-PDF upload where practical.

## Implementation Plan

1. Add failing tests for required pixel type/depth application and color emulator rendering; run them.
2. Implement strict image-mode capability handling and RGB emulator rendering; rerun the focused tests.
3. Remove emulator wiring from Tauri configuration/runtime and add an emulator-only build/start script plus documentation; run build checks.
4. Rebuild/install Nospe, inspect sidecars, then smoke-test backend and TWAIN source discovery.
