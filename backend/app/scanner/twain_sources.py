"""TWAIN-Quellenauflistung (64-bit) für GET /scanners."""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass, field

from ..models import Scanner
from .emulator_scan import VIRTUAL_SCANNER_NAME
from .twain_env import TwainEnvironment, probe_twain_environment, python_bitness
from .twain_lock import TwainBusy, twain_session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TwainSourceStatus:
    """Vollständiger TWAIN-Status inkl. Quellenliste."""

    environment: TwainEnvironment
    source_count: int
    sources: tuple[str, ...] = field(default_factory=tuple)


def _scanner_id(product_name: str) -> str:
    """TWAIN ProductName ist der Schlüssel für open_source(product_name=…)."""
    return product_name.strip()


def _is_normal_scanner(product_name: str) -> bool:
    """The emulator is an opt-in diagnostic source, never a normal default."""
    return _scanner_id(product_name).casefold() != VIRTUAL_SCANNER_NAME.casefold()


def is_emulator_running() -> bool:
    """The virtual source is selectable only while its separate server runs."""
    try:
        with socket.create_connection(("127.0.0.1", 8766), timeout=0.2):
            return True
    except OSError:
        return False


def visible_scanner_names(product_names: list[str]) -> list[str]:
    """Physical Windows scanners first, opt-in virtual scanner last."""
    normal = sorted(
        {_scanner_id(name) for name in product_names if _is_normal_scanner(name)},
        key=str.casefold,
    )
    has_virtual = any(
        _scanner_id(name).casefold() == VIRTUAL_SCANNER_NAME.casefold()
        for name in product_names
    )
    if has_virtual and is_emulator_running():
        normal.append(VIRTUAL_SCANNER_NAME)
    return normal


def list_twain_product_names(*, blocking: bool = True) -> tuple[list[str], str | None]:
    """Listet TWAIN ProductNames. Leere Liste bei Fehler; Fehlertext optional.

    ``blocking=False`` wirft ``TwainBusy``, wenn der DSM gerade scannt.
    """
    env = probe_twain_environment(blocking=blocking)
    if not env.dsm_available:
        return [], env.error

    try:
        import twain

        with twain_session(blocking=blocking):
            with twain.SourceManager() as sm:
                names = [n.strip() for n in sm.source_list if n and n.strip()]
        return names, None
    except TwainBusy:
        raise
    except Exception as exc:  # noqa: BLE001 - an API-Status weitergeben
        logger.exception("TWAIN source_list fehlgeschlagen")
        return [], str(exc)


def list_scanners() -> list[Scanner]:
    """Alle verfügbaren TWAIN-Quellen als Scanner-Modelle."""
    names, _error = list_twain_product_names()
    return [Scanner(id=name, name=name) for name in visible_scanner_names(names)]


def get_twain_status(*, blocking: bool = True) -> TwainSourceStatus:
    """Status für GET /scanners/status (``blocking=False`` → ``TwainBusy`` beim Scan)."""
    env = probe_twain_environment(blocking=blocking)
    hints = list(env.hints)

    if not env.dsm_available:
        return TwainSourceStatus(
            environment=env,
            source_count=0,
            sources=(),
        )

    names, list_error = list_twain_product_names(blocking=blocking)
    names = visible_scanner_names(names)
    if list_error:
        env = TwainEnvironment(
            platform=env.platform,
            python_bitness=env.python_bitness,
            twain_supported=env.twain_supported,
            dsm_available=env.dsm_available,
            pytwain_version=env.pytwain_version,
            error=list_error,
            hints=env.hints,
        )

    if env.dsm_available and not names and not env.error:
        hints.append(
            "Keine TWAIN-Quellen gefunden. Epson Scan 2 (64-bit) oder "
            "Nospe Virtual Scanner installieren; docs/TWAIN_SETUP.md"
        )
        if python_bitness() == 64:
            hints.append(
                "In 64-bit TWACKER prüfen, ob Quellen sichtbar sind."
            )

    return TwainSourceStatus(
        environment=env,
        source_count=len(names),
        sources=tuple(names),
    )
