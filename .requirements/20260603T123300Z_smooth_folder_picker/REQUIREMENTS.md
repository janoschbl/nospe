# Smooth Folder Picker

## As Is

The folder picker replaces the entire folder list with a centered spinner whenever a directory is loaded. Once the backend returns, every child folder is rendered as a DOM node immediately. Large directories can therefore produce a visible flash and a heavy re-render.

## To Be

Directory changes should feel calm and continuous. The previous list should stay visible while the next directory is loading, a subtle loading indicator should communicate progress, and large directory listings should render only the visible rows plus a small buffer.

## Requirements

1. Keep the picker layout stable while a new directory is loading.
2. Avoid rendering every folder row for large listings at once.
3. Preserve existing interactions: click opens a folder, double-click selects it, breadcrumbs and quick locations still navigate, and the save button still selects the current path.
4. Preserve the manual path fallback when the backend is unavailable.

## Acceptance Criteria

1. During a directory load, the existing list area is not replaced by a blank spinner-only state after an initial listing has already loaded.
2. For large `entries` arrays, the DOM contains only the visible folder rows plus overscan rows.
3. Folder row click and double-click behavior remains unchanged.
4. If `listDirectory` returns no data, the manual fallback remains available.

## Testing Plan

- Type-check and production-build the frontend with `npm run build`.
- Manually inspect the folder picker implementation for large-list virtualization, loading overlay behavior, and existing interaction preservation.

## Implementation Plan

1. Add a lightweight virtualized list component inside `FolderPicker.tsx`.
2. Change loading presentation so the initial load can show a spinner, but later navigation keeps the prior list visible with a subtle overlay.
3. Route the existing folder row behavior through the virtualized list without changing API contracts.
4. Run the frontend build to catch TypeScript and bundling regressions.
