# Requirements

## As Is

- The UI color selection is not included in `ScanRequest`; the backend always uses the profile's gray color mode.
- Scanner state can remain empty during initial data load, leaving the scanner control on its placeholder despite an available scanner.
- The settings synchronization effect clears an unsaved Paperless token whenever the settings object changes.

## To Be

- The selected image mode is passed to the backend and used when setting the TWAIN pixel type.
- The first available scanner is always visible and selected when no valid saved scanner exists, and that fallback becomes the persisted default.
- A token can be typed, retained while editing settings, explicitly saved, and used with the supplied local Paperless URL.

## Requirements

1. Extend the scan API contract with `color_mode` and apply it to the active scan profile.
2. Resolve a valid scanner selection from saved preference or the first available source before rendering/scanning, and persist the fallback.
3. Do not clear unsaved token text during session synchronization; persist it only with Speichern.

## Acceptance Criteria

1. A `color_mode: color` scan passes a profile with `color_mode == color` to the TWAIN scanner.
2. With a scanner available and no saved preference, the scanner dropdown is not on "Kein Scanner" and settings save the first scanner ID.
3. The provided URL and token survive editing until Speichern, after which `/paperless/test` reports configured credentials without returning the token.

## Testing Plan

- Add backend endpoint test proving request color mode overrides the profile.
- Add scanner-default API/settings tests and TypeScript production build.
- Use the desktop app to enter credentials, save, and run Paperless connection test; verify the scan UI selection.

## Implementation Plan

1. Write scan request override test, extend models and scan endpoint, then run focused backend tests.
2. Make scanner fallback deterministic in app state and persist it through existing settings API.
3. Preserve token draft through settings synchronization, rebuild, and smoke-test the packaged desktop app.
