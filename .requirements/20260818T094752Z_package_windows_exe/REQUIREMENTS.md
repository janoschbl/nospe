# Package Windows EXE

## As Is

Nospe is a Tauri 2 desktop application with a React/Vite frontend in `frontend/`.
The Tauri configuration enables bundling and declares Windows bundle targets as `all`.
The Python FastAPI backend is a separate process and is not currently bundled into the desktop application.

## To Be

Produce a verified Windows desktop build from the existing Tauri configuration, including a runnable `.exe` artifact and any configured installer bundle. Preserve the existing application behavior and do not change backend architecture as part of this packaging request.

## Requirements

1. Build the frontend and Tauri Windows release application using the repository's existing scripts and configuration.
2. Produce at least one Windows `.exe` artifact in the Tauri release bundle output.
3. Verify that the generated executable exists, is a Windows PE executable, and can launch without an immediate process failure.
4. Report the exact artifact path and the backend prerequisite/limitation.

## Acceptance Criteria

1. The Tauri release build completes successfully.
2. A `.exe` file is present under `frontend/src-tauri/target/release/bundle`.
3. The artifact has an `MZ` PE header and a successful launch smoke check.
4. The final response links to the artifact and states that the Python backend remains separate unless additionally bundled.

## Testing Plan

- Run the frontend production build as part of `tauri build`.
- Run the Tauri Windows release bundle build.
- Inspect the output directory and verify the `.exe` header.
- Launch the executable briefly, then close it and verify no immediate startup error.

## Implementation Plan

1. Run the existing Tauri release build from `frontend/`; test by checking the command exit status and output files.
2. If packaging configuration prevents the build, make only the smallest configuration correction required; test by rerunning the release build.
3. Perform the artifact and launch smoke checks; test by inspecting the binary and process behavior.
