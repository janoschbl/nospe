"""Startskript für das Nospe-Backend.

Startet Uvicorn auf 127.0.0.1:8765. Wird später auch von Tauri als
gebündelte EXE aufgerufen (PyInstaller, siehe Plan Phase 4).
"""

from __future__ import annotations

import uvicorn

from app.main import app

HOST = "127.0.0.1"
PORT = 8765


def main() -> None:
    # PyInstaller builds the production sidecar without a console. In that
    # mode stdout/stderr are None and Uvicorn's default formatter crashes on
    # sys.stdout.isatty(). The sidecar has no interactive log console, so let
    # the host process manage logging instead of configuring Uvicorn's TTY
    # formatter.
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        reload=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
