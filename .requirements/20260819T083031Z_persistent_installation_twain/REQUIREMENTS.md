# Requirements

## As Is

- The installed app at `%LOCALAPPDATA%\\Nospe` is an older build; the release-folder build did not update it.
- The frozen backend stores `config.json` beside program files, so installation updates can replace settings.
- App startup requests `/scanners` and `/scanners/status` concurrently, opening TWAIN source managers in parallel and producing an access violation.
- The emulator is a separately launched Python process rather than part of the desktop startup.

## To Be

- Program binaries live in the installed Nospe directory while persistent user configuration lives in `%APPDATA%\\Nospe\\config.json`, with migration from the legacy path.
- App startup performs one TWAIN discovery request and uses it both for scanner selection and diagnostics.
- Launching Nospe starts its backend and bundled emulator automatically, and closing Nospe stops the children it owns.
- The installer upgrades the existing installed app.

## Requirements

1. Separate persistent config from program installation and preserve existing config on migration.
2. Eliminate parallel TWAIN enumeration on app load and serialize source listing.
3. Bundle and launch emulator as a managed sidecar alongside the backend.
4. Build and install the updated Windows package.

## Acceptance Criteria

1. Settings survive an app restart and are found in `%APPDATA%\\Nospe\\config.json`.
2. Startup makes one scanner-status query rather than concurrent source-manager calls.
3. Starting the installed app yields healthy backend port 8765 and emulator port 8766.
4. The existing installed Nospe folder contains current binaries after upgrade.

## Testing Plan

- Backend tests, frontend production build, and Rust check.
- Verify configuration migration path with a focused settings test.
- Launch installed app and check health, emulator response, scanner source count, and persisted settings after restart.

## Implementation Plan

1. Add migration-safe config directory selection and tests.
2. Change frontend startup to one TWAIN status call and add backend source-manager serialization.
3. Add emulator PyInstaller sidecar and managed Tauri startup/shutdown.
4. Build NSIS installer, upgrade local installation, and smoke-test the installed executable.
