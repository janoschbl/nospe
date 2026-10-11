"""Startet Backend und Scanner-Emulator gemeinsam für lokale E2E-Tests."""

from __future__ import annotations

import signal
import subprocess
import sys
import threading
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    children = [
        subprocess.Popen([sys.executable, str(root / "run_backend.py")], cwd=root),
        subprocess.Popen([sys.executable, str(root / "run_emulator.py")], cwd=root),
    ]

    def stop(*_args: object) -> None:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            child.wait()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    stopped = threading.Event()
    try:
        while all(child.poll() is None for child in children):
            stopped.wait(1)
    finally:
        stop()


if __name__ == "__main__":
    main()
