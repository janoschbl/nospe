# Separate Emulator Port Requirements

## As Is

The emulator routes are included in `app.main`, so the normal Nospe backend on `127.0.0.1:8765` also serves `/emulator` and `/emulator/upload`.

## To Be

The normal Nospe backend remains only the backend on `127.0.0.1:8765`. The PDF upload emulator runs as a separate local FastAPI app on `127.0.0.1:8766`.

## Requirements

1. `app.main` must not include emulator routes.
2. A separate emulator FastAPI app must include the existing emulator routes.
3. A new start script must run the emulator app on `127.0.0.1:8766`.
4. Tests must prove the backend and emulator route surfaces are separate.
5. Documentation must show the separate backend and emulator ports.

## Acceptance Criteria

1. `TestClient(app.main.app).get("/emulator")` returns 404.
2. `TestClient(app.emulator.main.app).get("/emulator")` returns 200.
3. Existing emulator upload/job tests pass against the separate emulator app.
4. `run_backend.py` still uses port 8765.
5. `run_emulator.py` uses port 8766.

## Testing Plan

- Update emulator tests to target `app.emulator.main.app`.
- Add one backend separation test for `/emulator` returning 404 on `app.main.app`.
- Run `uv run pytest -q`.
- Smoke-test both local ports after restarting processes.

## Implementation Plan

1. Update tests first and verify they fail because routes are still mounted on `app.main` and no separate app exists.
2. Create `app/emulator/main.py` with its own FastAPI app and router.
3. Remove `app.include_router(emulator_router)` from `app.main`.
4. Add `run_emulator.py` with port 8766.
5. Update README.
6. Restart local processes and smoke-test ports 8765 and 8766.
