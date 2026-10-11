"""TWAIN als Scanner-Backend (Quellenliste über den 64-bit-DSM)."""

from __future__ import annotations

import sys
from pathlib import Path

from ..models import ScanProfile
from . import twain_scan, twain_sources
from .scanner_types import BackendBusy, DiscoveredScanner
from .twain_lock import TwainBusy


class TwainBackend:
    kind = "twain"
    # Die Quellenliste lädt Treiber-DLLs; deshalb deutlich seltener als WIA abfragen.
    interval = 30.0

    def available(self) -> bool:
        return sys.platform == "win32"

    def discover(self) -> list[DiscoveredScanner]:
        try:
            names, error = twain_sources.list_twain_product_names(blocking=False)
        except TwainBusy as exc:
            raise BackendBusy(str(exc)) from exc
        if error and not names:
            raise RuntimeError(error)
        return [
            DiscoveredScanner(kind=self.kind, native_id=name, name=name)
            for name in twain_sources.visible_scanner_names(names)
        ]

    def acquire(self, scanner: DiscoveredScanner, profile: ScanProfile, workdir: Path) -> list[Path]:
        return twain_scan._acquire_images(scanner.native_id, profile, workdir)
