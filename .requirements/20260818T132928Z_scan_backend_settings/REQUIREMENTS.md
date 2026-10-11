# Requirements

## As Is

- The frontend hides the backend's HTTP error detail and only shows a generic scan error.
- Tauri starts a backend sidecar unconditionally, so repeated app starts can create competing backend processes on port 8765.
- The selected scanner is only kept in React state and is not persisted as a default.
- Settings edits remain local to the settings sheet until the explicit save action; other app state does not receive every draft change.
- The filename preview uses the current timestamp only when React renders, and collision suffixes are `_001`, `_002`, etc.

## To Be

- Scan failures show the backend detail while retaining a clear fallback message.
- The app uses one healthy backend on port 8765 and starts a sidecar only when needed; startup waits until health is confirmed.
- The first available scanner is selected by default, while a user-selected scanner is persisted and reused when still available.
- Settings edits immediately update the current session and remain durable only after pressing Speichern.
- The preview timestamp updates continuously and existing files are never overwritten; collisions use `_1`, `_2`, etc.

## Requirements

1. Preserve and display useful scan/backend error details.
2. Make backend startup single-instance and health-checked.
3. Persist and restore the selected default scanner with first-available fallback.
4. Apply settings drafts immediately for the running session without implying durable save.
5. Keep filename timestamps current and allocate collision-free numeric suffixes.

## Acceptance Criteria

1. A scan error response containing `detail` is shown in the scan panel; HTTP status remains distinguishable.
2. A second app start does not spawn an additional backend when `/health` already responds; the app waits for health before using the API.
3. With no saved scanner, scanner 0 is selected; after selecting scanner N, reopening keeps scanner N if present, otherwise scanner 0 is selected. The selection is persisted through the backend settings contract.
4. Changing output directory, Paperless URL, token, or favorite fields updates the in-session draft immediately; only explicit Speichern calls durable settings persistence.
5. The displayed `Speichert als` timestamp changes as time advances. Existing `name.pdf` yields `name_1.pdf`, then `name_2.pdf`, without overwriting existing files.

## Testing Plan

- Backend unit tests for settings scanner persistence and collision allocation.
- FastAPI contract test for scanner selection in `/settings`.
- Frontend TypeScript/build verification and focused static checks for error parsing and timestamp interval.
- Existing backend pytest suite, frontend build, `git diff --check`, and a packaged app/backend health smoke test.

## Implementation Plan

1. Add failing backend tests for the settings field and `_1` collision suffix; implement the model/store/path changes.
2. Add failing frontend/API behavior checks where practical; implement backend error parsing, scanner persistence, session draft propagation, and live timestamp updates.
3. Harden Tauri sidecar startup to reuse a healthy endpoint and wait for health; build and smoke-test.
