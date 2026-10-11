"""Scan ausführen: Gerät wählen, scannen, PDF schreiben.

Es läuft immer nur ein Scan zugleich (ein Benutzer, ein Gerät); die Registry
pausiert währenddessen ihre Abfragen.
"""

from __future__ import annotations

import logging
import tempfile
import threading
from pathlib import Path

from ..models import ScanProfile
from . import twain_scan
from .pdf_builder import images_to_pdf
from .registry import ScannerRegistry
from .scanner_types import DiscoveredScanner, ScanError

logger = logging.getLogger(__name__)

_SCAN_LOCK = threading.Lock()


class ScanInProgress(ScanError):
    """Es läuft bereits ein Scan."""


def scan_active() -> bool:
    return _SCAN_LOCK.locked()


def perform_scan(
    *,
    registry: ScannerRegistry,
    scanner: DiscoveredScanner,
    profile: ScanProfile,
    title: str,
    output_dir: Path,
) -> Path:
    if not _SCAN_LOCK.acquire(blocking=False):
        raise ScanInProgress("Es läuft bereits ein Scan.")
    try:
        if scanner.kind == "twain":
            return twain_scan.perform_scan(
                scanner_id=scanner.native_id,
                profile=profile,
                title=title,
                output_dir=output_dir,
            )

        backend = registry.backend_for(scanner.kind)
        if backend is None:
            raise ScanError(f"Scanner-Typ „{scanner.kind}“ wird nicht unterstützt.")
        output_path = twain_scan.resolve_output_path(output_dir, title)
        with tempfile.TemporaryDirectory(prefix=twain_scan.TEMP_PREFIX, ignore_cleanup_errors=True) as tmp:
            pages = backend.acquire(scanner, profile, Path(tmp))
            try:
                images_to_pdf(pages, output_path)
            except Exception:
                output_path.unlink(missing_ok=True)
                raise
        return output_path
    finally:
        _SCAN_LOCK.release()
