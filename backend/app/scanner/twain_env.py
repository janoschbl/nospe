"""TWAIN-Umgebungsprüfung (64-bit, DSM, Plattform) für Nospe Phase 0/1."""

from __future__ import annotations

import platform
import struct
import sys
from dataclasses import dataclass, field
from typing import Literal

from .twain_lock import twain_session

PythonBitness = Literal[32, 64]


@dataclass(frozen=True)
class TwainEnvironment:
    """Ergebnis einer TWAIN-Umgebungsprüfung ohne Quellenauflistung."""

    platform: str
    python_bitness: PythonBitness
    twain_supported: bool
    dsm_available: bool
    pytwain_version: str | None = None
    error: str | None = None
    hints: tuple[str, ...] = field(default_factory=tuple)


def python_bitness() -> PythonBitness:
    return 64 if struct.calcsize("P") * 8 == 64 else 32


def is_windows() -> bool:
    return sys.platform == "win32"


_ready_cache: TwainEnvironment | None = None


def reset_probe_cache() -> None:
    global _ready_cache
    _ready_cache = None


def probe_twain_environment(*, blocking: bool = True) -> TwainEnvironment:
    """Prüft Plattform, Python-Bitness und ob der TWAIN DSM geladen werden kann.

    Ein erfolgreiches Ergebnis wird gemerkt (der DSM verschwindet nicht mehr),
    Fehler werden jedes Mal neu geprüft, damit eine Nachinstallation greift.
    ``blocking=False`` wirft ``TwainBusy``, wenn gerade gescannt wird.
    """
    global _ready_cache
    if _ready_cache is not None:
        return _ready_cache
    with twain_session(blocking=blocking):
        result = _probe_uncached()
    if result.dsm_available:
        _ready_cache = result
    return result


def _probe_uncached() -> TwainEnvironment:
    bitness = python_bitness()
    plat = platform.platform()

    if not is_windows():
        return TwainEnvironment(
            platform=plat,
            python_bitness=bitness,
            twain_supported=False,
            dsm_available=False,
            error="TWAIN wird von Nospe nur unter Windows unterstützt.",
            hints=(
                "Backend auf Windows 64-bit starten.",
            ),
        )

    if bitness != 64:
        return TwainEnvironment(
            platform=plat,
            python_bitness=bitness,
            twain_supported=True,
            dsm_available=False,
            error="Nospe erwartet 64-bit Python für echte 64-bit TWAIN-Auswahl.",
            hints=(
                "64-bit Python installieren und Backend mit uv auf 64-bit umstellen.",
                "32-bit Python sieht 64-bit TWAIN-Treiber nicht.",
            ),
        )

    try:
        import twain  # pytwain-Paket

        version = getattr(twain, "version", lambda: None)()
    except ImportError as exc:
        return TwainEnvironment(
            platform=plat,
            python_bitness=bitness,
            twain_supported=True,
            dsm_available=False,
            error=f"pytwain nicht installiert: {exc}",
            hints=("Im backend-Verzeichnis: uv sync",),
        )

    try:
        from twain.exceptions import SMLoadFileFailed

        with twain.SourceManager() as _sm:
            pass
    except SMLoadFileFailed as exc:
        return TwainEnvironment(
            platform=plat,
            python_bitness=bitness,
            twain_supported=True,
            dsm_available=False,
            pytwain_version=version,
            error=f"TWAIN DSM nicht ladbar: {exc}",
            hints=(
                "64-bit TWAINDSM.dll nach %SystemRoot%\\System32 kopieren "
                "(GitHub: twain/twain-dsm Release v2.5.1, Asset dsm_020501.zip).",
                "Siehe docs/TWAIN_SETUP.md",
            ),
        )
    except Exception as exc:  # noqa: BLE001 - Diagnose für Status-Endpoint
        return TwainEnvironment(
            platform=plat,
            python_bitness=bitness,
            twain_supported=True,
            dsm_available=False,
            pytwain_version=version,
            error=str(exc),
            hints=("TWACKER 64-bit oder scripts/verify_twain.py ausführen.",),
        )

    return TwainEnvironment(
        platform=plat,
        python_bitness=bitness,
        twain_supported=True,
        dsm_available=True,
        pytwain_version=version,
    )
