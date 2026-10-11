# Rebrand Nospe and uv Backend

## As Is

The project is branded as Nospe across README, frontend metadata, Tauri metadata, UI copy, Python package docstrings, and backend comments. The backend is a FastAPI stub started with `python run_backend.py` after manually creating a virtual environment and installing `requirements.txt`.

## To Be

The product-facing project name should be Nospe. The backend should be runnable through `uv` from the `backend/` directory without manual virtualenv setup, while preserving the existing FastAPI API contract and local development port.

## Requirements

1. Rename product/project branding from Nospe to Nospe in user-facing app metadata, visible UI labels, and backend documentation comments.
2. Keep existing scanner, Paperless, and endpoint behavior unchanged.
3. Add `uv` project metadata for the backend with the current runtime dependencies.
4. Document backend setup and start commands using `uv`.
5. Verify that the backend app imports and that its health endpoint returns the expected shape.

## Acceptance Criteria

1. App title, Tauri product/window title, package names/descriptions, README heading, and relevant visible UI footer/header labels use Nospe.
2. No API field names, endpoint paths, scanner IDs, or Paperless-specific names are renamed.
3. `backend/pyproject.toml` declares the backend package, Python requirement, and FastAPI/Uvicorn/Pydantic dependencies.
4. README shows `uv sync` and `uv run` backend commands.
5. A backend smoke test using `uv run` can import `app.main:app` and call `/health`.

## Testing Plan

Run a backend import and TestClient smoke check through `uv run`. If available, run the frontend TypeScript build to catch metadata or UI compile issues.

## Implementation Plan

1. Add backend `pyproject.toml` and keep `requirements.txt` as a legacy compatibility file.
2. Rebrand exact Nospe/nospe references that are product/package metadata or visible copy.
3. Update README backend instructions to use `uv`.
4. Run focused backend smoke checks and frontend build/lint checks where practical.
