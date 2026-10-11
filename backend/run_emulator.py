"""Start script for the standalone Nospe TWAIN PDF emulator."""

from __future__ import annotations

import uvicorn

from app.emulator.main import app

HOST = "127.0.0.1"
PORT = 8766


def main() -> None:
    # The packaged sidecar has no stdout/stderr console. Avoid Uvicorn's
    # default TTY formatter for the same reason as the main backend.
    uvicorn.run(app, host=HOST, port=PORT, reload=False, log_config=None)


if __name__ == "__main__":
    main()
