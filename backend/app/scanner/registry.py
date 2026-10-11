"""Scanner-Registry: sammelt TWAIN-, WIA- und eSCL-Geräte an einer Stelle.

* Abfragen laufen im Hintergrund (je Backend eigenes Intervall); die API liest
  nur den Cache und blockiert nie auf dem DSM oder einem COM-Aufruf.
* Während eines Scans wird nichts abgefragt: weder TWAIN noch WIA mögen
  parallele Zugriffe auf ein Gerät.
* Dasselbe Gerät taucht oft in TWAIN *und* WIA auf. Es wird einmal angezeigt
  (TWAIN bevorzugt, da dort Einzug/Duplex am zuverlässigsten sind); die anderen
  Zugänge hängen als ``also_via`` daran.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field, replace
from typing import Callable, Sequence

from .scanner_types import KIND_ORDER, BackendBusy, DiscoveredScanner, ScannerBackend

logger = logging.getLogger(__name__)

_NOISE = re.compile(r"\b(epson|series|twain|wia|scanner|scan\s*2|driver|treiber|usb)\b", re.IGNORECASE)


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _NOISE.sub(" ", name.casefold()))


def _same_device(a: DiscoveredScanner, b: DiscoveredScanner) -> bool:
    na, nb = _normalize(a.name), _normalize(b.name)
    if len(na) < 4 or len(nb) < 4:
        return False
    return na in nb or nb in na


def merge_duplicates(scanners: Sequence[DiscoveredScanner]) -> list[DiscoveredScanner]:
    """Fasst Geräte zusammen, die über mehrere Zugänge sichtbar sind."""
    ordered = sorted(scanners, key=lambda s: (KIND_ORDER.get(s.kind, 99), s.name.casefold()))
    merged: list[DiscoveredScanner] = []
    for scanner in ordered:
        primary = next(
            (i for i, m in enumerate(merged) if m.kind != scanner.kind and _same_device(m, scanner)),
            None,
        )
        if primary is None:
            merged.append(scanner)
        else:
            merged[primary] = replace(merged[primary], also_via=(*merged[primary].also_via, scanner.id))
    return merged


@dataclass(frozen=True)
class Snapshot:
    scanners: list[DiscoveredScanner]
    errors: dict[str, str]
    updated_at: float | None
    scanning: bool


@dataclass
class _BackendState:
    found: list[DiscoveredScanner] = field(default_factory=list)
    error: str | None = None
    last_run: float = 0.0


class ScannerRegistry:
    def __init__(
        self,
        backends: Sequence[ScannerBackend],
        *,
        scan_active: Callable[[], bool] = lambda: False,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._backends = [b for b in backends if getattr(b, "available", lambda: True)()]
        self._state = {b.kind: _BackendState() for b in self._backends}
        self._scan_active = scan_active
        self._clock = clock
        self._state_lock = threading.Lock()
        self._refresh_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._updated_at: float | None = None

    # -- Lesen ---------------------------------------------------------------

    def snapshot(self) -> Snapshot:
        with self._state_lock:
            all_found = [s for st in self._state.values() for s in st.found]
            errors = {kind: st.error for kind, st in self._state.items() if st.error}
            updated = self._updated_at
        return Snapshot(merge_duplicates(all_found), errors, updated, self._scan_active())

    def resolve(self, scanner_id: str) -> DiscoveredScanner | None:
        """Findet einen Scanner per ID; reine Namen (alte Einstellungen) gelten als TWAIN."""
        if scanner_id.split(":", 1)[0] not in KIND_ORDER:
            scanner_id = f"twain:{scanner_id}"
        with self._state_lock:
            candidates = [s for st in self._state.values() for s in st.found]
        by_id = {s.id: s for s in candidates}
        return by_id.get(scanner_id)

    # -- Abfragen ------------------------------------------------------------

    def refresh(self, *, force: bool = False) -> bool:
        """Fragt fällige Backends ab. Gibt False zurück, wenn gerade ein Lauf aktiv ist."""
        if not self._refresh_lock.acquire(blocking=False):
            return False
        try:
            if self._scan_active():
                return True
            now = self._clock()
            for backend in self._backends:
                state = self._state[backend.kind]
                # Ereignisgesteuerte Backends (interval 0) sind billig: nur Cache lesen.
                due = (
                    force
                    or backend.interval == 0
                    or state.last_run == 0.0
                    or now - state.last_run >= backend.interval
                )
                if due:
                    self._run_backend(backend, now)
            with self._state_lock:
                self._updated_at = time.time()
            return True
        finally:
            self._refresh_lock.release()

    def _run_backend(self, backend: ScannerBackend, now: float) -> None:
        state = self._state[backend.kind]
        try:
            found = backend.discover()
        except BackendBusy:
            return  # alten Stand behalten, bald erneut versuchen
        except Exception as exc:  # noqa: BLE001 - ein defektes Backend darf die anderen nicht stoppen
            logger.warning("Scanner-Suche (%s) fehlgeschlagen: %s", backend.kind, exc)
            with self._state_lock:
                state.found, state.error, state.last_run = [], str(exc), now
            return
        with self._state_lock:
            state.found, state.error, state.last_run = list(found), None, now

    # -- Hintergrund ---------------------------------------------------------

    def start(self, tick: float = 1.0) -> None:
        if self._thread is not None:
            return
        for backend in self._backends:
            starter = getattr(backend, "start", None)
            if starter:
                starter()
        self._stop.clear()

        def loop() -> None:
            while not self._stop.is_set():
                try:
                    self.refresh()
                except Exception:  # noqa: BLE001
                    logger.exception("Scanner-Registry-Lauf fehlgeschlagen")
                self._stop.wait(tick)

        self._thread = threading.Thread(target=loop, name="scanner-registry", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        for backend in self._backends:
            stopper = getattr(backend, "stop", None)
            if stopper:
                stopper()

    def backend_for(self, kind: str) -> ScannerBackend | None:
        return next((b for b in self._backends if b.kind == kind), None)
