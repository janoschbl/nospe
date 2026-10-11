# Nospe Virtual Scanner TWAIN Data Source

This folder contains the Windows x64 native TWAIN Data Source scaffold for the PDF emulator.

## Build

```powershell
cmake -S twain_ds -B twain_ds/build -A x64
cmake --build twain_ds/build --config Release
```

The build output is `NospeVirtualScanner.ds`.

## Install

Copy the release `.ds` file to the 64-bit TWAIN data source folder, usually:

```powershell
Copy-Item twain_ds/build/Release/NospeVirtualScanner.ds C:\Windows\twain_64\NospeVirtualScanner.ds
```

Run PowerShell as Administrator for the copy.

## Current Scope

- Exports `DS_Entry`.
- Reports identity as `Nospe Virtual Scanner`.
- Reads `%LOCALAPPDATA%\Nospe\twain-emulator\active\manifest.json` by default.
- Handles core open/close/status/identity calls.

The image memory transfer state machine still needs validation against the actual Nospe TWAIN client and TWAIN DSM before this can be called production-ready.
