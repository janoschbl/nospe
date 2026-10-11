# Folder Path Alignment

## As Is

The folder picker footer shows the current save path with right-aligned text. Its scroll container is moved to the path end on path changes, but the non-overflow state also appears right-aligned. The breadcrumb path in the picker header can overflow horizontally, but it does not explicitly scroll to the newest path tail when navigating deeper. Breadcrumb segment padding and separator spacing are compact, but still leave more space than desired between folder labels and chevrons.

## To Be

The footer save path should read as left-aligned in normal cases, while still automatically showing the path tail when the path overflows horizontally. The header breadcrumb should also keep the newest path tail visible after navigating deeper. Breadcrumb segments should be denser, with smaller label padding and tighter separator spacing.

## Requirements

1. The footer path text is left-aligned when it fits within its available width.
2. The footer path scroll container automatically shows the end of the path whenever the current folder changes.
3. The header breadcrumb scroll container automatically shows the newest path tail whenever the current folder changes.
4. Breadcrumb chevrons and folder labels use tighter spacing than before.

## Acceptance Criteria

1. A short current path starts at the left edge of the footer path area, not the right edge.
2. A long current path shows its final folder/file-system tail after navigating into deeper folders.
3. A long breadcrumb row shows the deepest visible segments after navigating into deeper folders.
4. The visual space between each `>` separator and adjacent folder labels is smaller than before.

## Testing Plan

- Run the frontend TypeScript/Vite build.
- Inspect `FolderPicker` for keyboard/focus behavior preservation.
- If a dev server is available, visually smoke-test opening the picker and navigating into nested folders.

## Implementation Plan

1. Add a ref for the breadcrumb scroll container and use layout-time scrolling for both breadcrumb and footer path containers. Test with frontend build.
2. Change the footer path text alignment from right to left while preserving selectable overflow. Test with frontend build.
3. Tighten breadcrumb text size, button padding, and separator sizing. Test with frontend build.
