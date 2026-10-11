# Requirements: Native folder picker and bundled runtime

## As Is

The React UI contains a custom folder-browser dialog backed by `/fs/list` and `/fs/mkdir`. The frontend API silently falls back to mock data when the backend is unavailable, and the UI exposes that state as “Mock-Modus”. The Tauri shell currently starts only the webview; the Python backend and scanner emulator are separate manual processes. The “Vertikal spiegeln” option uses a fixed-height single-line option row whose line height clips some glyphs.

## To Be

Selecting the scan destination opens the native Windows folder chooser and returns the selected path to the existing settings flow. The custom folder-browser implementation and its unused filesystem API surface are removed. The frontend has no mock data or mock mode; backend failures are shown as an offline/error state. The Tauri production configuration bundles the backend runtime as a sidecar and starts it with the application. A single local development command starts both the backend and scanner-emulator web server for end-to-end testing. The vertical mirror option has sufficient line height to render all label glyphs.

## Requirements

1. Replace the custom target-folder picker with a native directory chooser.
2. Remove frontend mock fallback behavior and mock-mode UI/state.
3. Bundle and start the backend with the desktop app, while providing a combined backend/emulator dev server command.
4. Fix the vertical-mirror label line height without changing the option semantics.

## Acceptance Criteria

1. Clicking “Zielordner” invokes the native Windows directory chooser; cancelling changes nothing; choosing a directory saves and displays its path. No custom folder-browser component remains in the scan flow.
2. With the backend unavailable, the UI does not display “Mock” and does not fabricate scanners, settings, scans, or Paperless results. It shows an explicit offline/error state and disables actions that require the backend.
3. The production Tauri configuration has a backend sidecar bundle target and startup path. A documented single command starts both `8765` (backend) and `8766` (scanner emulator), and both health/page endpoints respond.
4. “Vertikal spiegeln” renders the complete lowercase “g” and remains keyboard accessible.

## Testing Plan

- Add/adjust static contract tests for the frontend API and Tauri configuration where the existing test stack supports them.
- Run the backend pytest suite.
- Run the frontend TypeScript/build checks.
- Start the combined local servers, query `/health` and `/emulator`, then stop only the processes created for this task.
- Run `git diff --check` from the repository that owns the changed files, if available.

## Implementation Plan

1. Add the native dialog dependency/configuration and replace the custom picker call site; build the frontend.
2. Remove mock data, fallback responses, and mock-specific status branches; build the frontend and inspect remaining “mock” references.
3. Add a combined backend/emulator runner and Tauri sidecar configuration/startup wiring; run backend tests and a two-port smoke check.
4. Increase the option label line height; rebuild and verify the generated UI source contains the corrected class.
5. Update documentation and perform the full validation suite.
