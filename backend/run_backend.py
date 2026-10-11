"""Startskript für das Nospe-Backend.

Das Backend bindet nur an ``127.0.0.1``. Wie die UI es findet und sich
authentifiziert, hängt vom Start ab:

* **Von Tauri gestartet** (``NOSPE_HANDSHAKE_FILE`` gesetzt): Das Backend wählt
  einen zufälligen freien Port und erzeugt ein Secret. Beides schreibt es
  atomar in die Handshake-Datei (zwei Zeilen: Port, Secret); Tauri liest sie
  und löscht sie wieder. Der Socket ist schon gebunden, bevor Tauri den Port
  erfährt, es gibt also kein Rennen um den Port.
* **Manuell/Entwicklung**: Port aus ``NOSPE_API_PORT`` (Standard 8765), Secret
  aus ``NOSPE_API_SECRET`` oder frisch erzeugt und auf stderr ausgegeben.
  ``NOSPE_DEV=1`` erlaubt zusätzlich die Vite-Origins (localhost:5173).
"""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import uvicorn

from app import security
from app.main import app

HOST = "127.0.0.1"
DEFAULT_DEV_PORT = 8765


def bind_loopback_socket(port: int) -> socket.socket:
    """Bindet exklusiv an Loopback (Port 0 = zufällig freier Port)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if sys.platform == "win32":
        # SO_REUSEADDR würde unter Windows erlauben, dass ein fremder Prozess
        # denselben Port mitbenutzt; EXCLUSIVEADDRUSE verhindert das.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)  # type: ignore[attr-defined]
    else:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, port))
    sock.listen(128)
    return sock


def write_handshake(path: Path, port: int, secret: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(f"{port}\n{secret}\n", encoding="utf-8")
    os.replace(tmp, path)


def main() -> None:
    handshake = os.environ.get("NOSPE_HANDSHAKE_FILE", "").strip()
    secret = os.environ.get("NOSPE_API_SECRET", "").strip()
    generated = not secret
    if generated:
        secret = security.new_secret()
    default_port = 0 if handshake else DEFAULT_DEV_PORT
    port = int(os.environ.get("NOSPE_API_PORT", str(default_port)))

    sock = bind_loopback_socket(port)
    port = sock.getsockname()[1]
    security.configure(secret=secret, port=port, dev=security.dev_mode_enabled())

    if handshake:
        write_handshake(Path(handshake), port, secret)
    elif generated and sys.stderr is not None:
        print(f"Nospe-Backend: http://{HOST}:{port}  NOSPE_API_SECRET={secret}", file=sys.stderr)

    # PyInstaller builds the production sidecar without a console. In that
    # mode stdout/stderr are None and Uvicorn's default formatter crashes on
    # sys.stdout.isatty(). The sidecar has no interactive log console, so let
    # the host process manage logging instead of configuring Uvicorn's TTY
    # formatter.
    config = uvicorn.Config(app, log_config=None)
    uvicorn.Server(config).run(sockets=[sock])


if __name__ == "__main__":
    main()
