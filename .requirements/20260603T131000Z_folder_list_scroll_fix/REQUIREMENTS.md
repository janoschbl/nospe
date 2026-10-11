# Folder List Scroll Fix

## As Is

The folder picker renders folder rows inside a virtualized scroll container. The list area is a flex child with `min-h-[180px] flex-1`, so it can lose a concrete viewport height and the inner folder list may grow instead of becoming scrollable.

## To Be

The folder list should always have a real bounded viewport. When a folder contains more rows than fit, users should be able to scroll through those rows with mouse wheel, trackpad, scrollbar, or keyboard focus interactions.

## Requirements

1. Keep the folder list area height bounded inside the picker dialog.
2. Preserve virtualization for large folders.
3. Keep the existing empty and loading states.

## Acceptance Criteria

1. A folder with many subfolders scrolls vertically inside the folder list area.
2. The picker footer and header remain visible while scrolling folders.
3. The frontend build succeeds.

## Testing Plan

- Run `npm run build` in `frontend`.
- Inspect the folder list sizing classes to confirm the scrollable element has a concrete parent height.

## Implementation Plan

1. Give the folder list wrapper a concrete responsive height instead of relying on flex growth.
2. Let the virtualized list fill that bounded wrapper with `h-full overflow-y-auto`.
3. Build the frontend.
