# Compact Window And Folder Favorites

## As Is

Nospe shows the main scan flow in a tall, 680px-wide app column. The scan panel has a dedicated destination-folder card between the filename controls and scan options, and the action bar is pinned to the bottom with `mt-auto`, which creates a large empty area on taller windows. The folder picker receives quick locations from the backend as fixed defaults: Home, Dokumente, Desktop, Downloads, and drives. Long paths in the picker footer are truncated at the start, so the most useful tail can be hidden and the full text is not selectable.

Settings currently contain a single `scan_output_dir` text field. That field is the default target folder used for scans and for the main-panel folder picker.

## To Be

The main window should feel physically smaller and denser while preserving the core scan flow. The destination folder should remain available, but not consume a full large row. The action bar should sit directly after the scan controls instead of leaving a large empty gulf.

The folder picker should make long paths easier to read: breadcrumb segment spacing should tighten as paths grow, the footer should show the path tail first, and the full path should be selectable in a scrollbar-hidden horizontal text area. Quick locations should be user-controlled favorites from settings, plus useful drive shortcuts. Settings should let the user add, remove, rename, pick icons for, and apply favorite folders.

## Requirements

1. Compact the main scan window width and height.
2. Remove the large vertical gap between option buttons and the scan button.
3. Preserve a clear way to inspect and change the target folder.
4. Keep the Settings "Speicherort" folder as the default scan output directory.
5. Add custom folder favorites to settings.
6. Use custom favorites in the folder picker instead of the fixed Home/Dokumente/Desktop/Downloads defaults.
7. Keep drive shortcuts in the folder picker for machines with multiple disks.
8. Improve long-path display in the folder picker breadcrumb and footer.
9. Preserve backend/frontend settings compatibility for existing config files without favorites.

## Acceptance Criteria

1. The app shell maximum width is smaller than before and the scan panel uses tighter spacing.
2. The action bar no longer uses bottom-pinning that creates a large empty area on taller windows.
3. The current target folder remains visible from the main scan screen and opens the folder picker.
4. Saving settings still updates `scan_output_dir` and scans still use that folder.
5. Settings include editable favorite rows with label, path, icon, add, remove, and "use as default" controls.
6. Folder picker quick chips show configured favorites and not the old Home/Dokumente/Desktop/Downloads defaults.
7. Windows drives still appear as quick chips.
8. Long breadcrumb labels get narrower and gaps shrink when there are many segments.
9. The picker footer shows the end of the current path and lets the user select the full path without a visible scrollbar.

## Testing Plan

- Run TypeScript build after frontend changes.
- Run backend smoke tests by importing settings and filesystem modules where practical.
- Use existing mock behavior to verify settings defaults still load without a `folder_favorites` field.
- Check edited files with IDE lints.

## Implementation Plan

1. Extend shared settings/favorite types in backend and frontend, then test type/build feedback.
2. Persist and return `folder_favorites` in backend settings, and feed favorites into `/fs/list`.
3. Update frontend API mock and save flow to carry favorites.
4. Compact `App` and `ScanPanel` layout, moving target-folder control into a smaller inline location.
5. Update `FolderPicker` quick chips, breadcrumb spacing, and selectable footer path.
6. Add favorite management UI to `SettingsSheet`.
7. Run build/lints and fix regressions.
