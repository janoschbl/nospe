"""Ein Prozess-weites Schloss für alles, was den TWAIN-DSM anfasst.

Der DSM ist pro Prozess global und nicht nebenläufig sicher. FastAPI führt
synchrone Routen im Threadpool aus, daher dürfen Umgebungsprüfung,
Quellenauflistung und Scan niemals parallel laufen. Das Schloss ist re-entrant,
damit verschachtelte Aufrufe im selben Thread (z. B. Liste → Umgebungsprüfung)
nicht verklemmen.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator

TWAIN_LOCK = threading.RLock()


class TwainBusy(Exception):
    """Der DSM wird gerade benutzt (z. B. läuft ein Scan)."""


@contextmanager
def twain_session(*, blocking: bool = True) -> Iterator[None]:
    """Reserviert den DSM; ``blocking=False`` wirft ``TwainBusy`` statt zu warten."""
    if not TWAIN_LOCK.acquire(blocking=blocking):
        raise TwainBusy("TWAIN wird gerade benutzt.")
    try:
        yield
    finally:
        TWAIN_LOCK.release()
