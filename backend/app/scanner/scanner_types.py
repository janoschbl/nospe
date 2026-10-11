"""Gemeinsame Typen der Scanner-Backends (TWAIN, WIA, eSCL)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Protocol

from ..models import ScanProfile

KIND_ORDER = {"twain": 0, "wia": 1, "escl": 2}


class ScanError(Exception):
    """Scan fehlgeschlagen (für HTTP 400)."""


class BackendBusy(Exception):
    """Backend kann gerade nicht abgefragt werden (z. B. läuft ein Scan)."""


@dataclass(frozen=True)
class DiscoveredScanner:
    """Ein vom Betriebssystem/Netzwerk gemeldeter Scanner."""

    kind: str  # "twain" | "wia" | "escl"
    native_id: str  # TWAIN-Produktname, WIA-DeviceID oder eSCL-Basis-URL
    name: str
    extra: Mapping[str, str] = field(default_factory=dict)
    also_via: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return f"{self.kind}:{self.native_id}"


class ScannerBackend(Protocol):
    kind: str
    #: Sekunden zwischen zwei Abfragen; 0 = ereignisgesteuert, nie pollen.
    interval: float

    def discover(self) -> list[DiscoveredScanner]: ...

    def acquire(self, scanner: DiscoveredScanner, profile: ScanProfile, workdir: Path) -> list[Path]:
        """Scannt alle Seiten als Bilddateien nach ``workdir``."""
        ...
