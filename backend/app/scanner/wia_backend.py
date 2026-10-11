"""WIA-2.0-Backend (Windows Image Acquisition).

WIA ist Windows' eigener Scanner-Katalog. Er kennt auch Geräte ohne TWAIN-Treiber
(z. B. WSD-Netzwerkscanner) und braucht keinen zusätzlichen DSM. Zugriff über die
COM-Automatisierung ``WIA.DeviceManager`` (wiaaut.dll, ab Windows Vista).

Property-IDs stammen aus wiadef.h. Eigenschaften werden über ihre numerische ID
gesucht; fehlt eine, wird sie übersprungen — außer sie wurde ausdrücklich
verlangt (Duplex, Farbmodus), dann bricht der Scan mit einer klaren Meldung ab.
"""

from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from ..models import ScanProfile
from .scanner_types import DiscoveredScanner, ScanError

logger = logging.getLogger(__name__)

WIA_DEVICE_TYPE_SCANNER = 1
WIA_FORMAT_BMP = "{B96B3CAB-0728-11D3-9D7B-0000F81EF32E}"

# Item-Eigenschaften
IPA_DATATYPE = 4103  # 0 = S/W, 1 = Grau, 2 = Farbe
IPA_DEPTH = 4104
IPS_XRES = 6147
IPS_YRES = 6148
IPS_XEXTENT = 6151
IPS_YEXTENT = 6152
# Geräte-Eigenschaften
DPS_DOCUMENT_HANDLING_SELECT = 3088
DPS_PAGES = 3096

HANDLING_FEEDER = 1
HANDLING_FLATBED = 2
HANDLING_DUPLEX = 4

DATATYPE_BY_MODE = {"bw": (0, 1), "gray": (1, 8), "color": (2, 24)}
MODE_LABEL = {"bw": "Schwarzweiß", "gray": "Grau", "color": "Farbe"}

_HRESULT_MESSAGES = {
    0x80210002: "Papierstau im Scanner.",
    0x80210004: "Problem mit dem Papier im Scanner.",
    0x80210005: "Der Scanner ist offline.",
    0x80210006: "Der Scanner ist beschäftigt.",
    0x80210007: "Der Scanner wärmt noch auf.",
    0x80210008: "Am Scanner ist ein Eingriff nötig.",
    0x8021000A: "Kommunikationsfehler mit dem Scanner.",
    0x8021000D: "Der Scanner wird von einem anderen Programm benutzt.",
    0x80210016: "Die Scannerabdeckung ist offen.",
    0x80210021: "Mehrfacheinzug erkannt.",
}
HRESULT_PAPER_EMPTY = 0x80210003


def _hresult(exc: BaseException) -> int | None:
    """Liefert den vorzeichenlosen HRESULT einer COM-Ausnahme, falls vorhanden."""
    value = getattr(exc, "hresult", None)
    if value is None and exc.args and isinstance(exc.args[0], int):
        value = exc.args[0]
    return value & 0xFFFFFFFF if isinstance(value, int) else None


def _find_property(properties: Any, property_id: int) -> Any | None:
    for index in range(1, int(properties.Count) + 1):
        prop = properties.Item(index)
        if int(prop.PropertyID) == property_id:
            return prop
    return None


def _set_property(properties: Any, property_id: int, value: Any, *, required: str | None = None) -> bool:
    prop = _find_property(properties, property_id)
    if prop is None:
        if required:
            raise ScanError(f"Der Scanner unterstützt über WIA nicht: {required}.")
        return False
    try:
        prop.Value = value
    except Exception as exc:  # noqa: BLE001 - COM-Fehler des Treibers
        if required:
            raise ScanError(f"Der Scanner unterstützt über WIA nicht: {required} ({exc}).") from exc
        logger.debug("WIA-Property %s nicht gesetzt: %s", property_id, exc)
        return False
    return True


def _default_dispatch() -> Callable[[str], Any]:
    import win32com.client  # type: ignore[import-not-found]

    return win32com.client.Dispatch


@contextmanager
def _com_apartment(enabled: bool) -> Iterator[None]:
    """COM muss in jedem Threadpool-Thread initialisiert werden."""
    if not enabled:
        yield
        return
    import pythoncom  # type: ignore[import-not-found]

    pythoncom.CoInitialize()
    try:
        yield
    finally:
        pythoncom.CoUninitialize()


class WiaBackend:
    kind = "wia"
    interval = 5.0

    def __init__(self, dispatch: Callable[[str], Any] | None = None, *, init_com: bool | None = None) -> None:
        self._dispatch = dispatch
        self._init_com = dispatch is None if init_com is None else init_com

    def available(self) -> bool:
        return self._dispatch is not None or sys.platform == "win32"

    def _client(self) -> Callable[[str], Any]:
        if self._dispatch is None:
            self._dispatch = _default_dispatch()
        return self._dispatch

    def discover(self) -> list[DiscoveredScanner]:
        if not self.available():
            return []
        with _com_apartment(self._init_com):
            manager = self._client()("WIA.DeviceManager")
            infos = manager.DeviceInfos
            found: list[DiscoveredScanner] = []
            for index in range(1, int(infos.Count) + 1):
                info = infos.Item(index)
                if int(info.Type) != WIA_DEVICE_TYPE_SCANNER:
                    continue
                name = str(info.Properties("Name").Value).strip()
                device_id = str(info.DeviceID)
                if name and device_id:
                    found.append(DiscoveredScanner(kind=self.kind, native_id=device_id, name=name))
            return found

    def acquire(self, scanner: DiscoveredScanner, profile: ScanProfile, workdir: Path) -> list[Path]:
        with _com_apartment(self._init_com):
            return self._acquire(scanner, profile, workdir)

    def _acquire(self, scanner: DiscoveredScanner, profile: ScanProfile, workdir: Path) -> list[Path]:
        manager = self._client()("WIA.DeviceManager")
        infos = manager.DeviceInfos
        device = None
        for index in range(1, int(infos.Count) + 1):
            info = infos.Item(index)
            if str(info.DeviceID) == scanner.native_id:
                try:
                    device = info.Connect()
                except Exception as exc:  # noqa: BLE001
                    raise ScanError(_describe(exc, "Verbindung zum Scanner fehlgeschlagen")) from exc
                break
        if device is None:
            raise ScanError(f"WIA-Scanner „{scanner.name}“ ist nicht mehr verbunden.")

        use_feeder = profile.adf
        if profile.duplex and not use_feeder:
            raise ScanError("Duplex-Scan benötigt den Dokumenteneinzug.")
        selection = (HANDLING_FEEDER | (HANDLING_DUPLEX if profile.duplex else 0)) if use_feeder else HANDLING_FLATBED
        _set_property(
            device.Properties,
            DPS_DOCUMENT_HANDLING_SELECT,
            selection,
            required="Dokumenteneinzug/Duplex" if use_feeder else None,
        )
        if use_feeder:
            _set_property(device.Properties, DPS_PAGES, 0)  # 0 = alle Seiten im Einzug

        item = device.Items(1)
        datatype, depth = DATATYPE_BY_MODE[profile.color_mode]
        label = MODE_LABEL[profile.color_mode]
        _set_property(item.Properties, IPA_DATATYPE, datatype, required=f"Farbmodus „{label}“")
        _set_property(item.Properties, IPA_DEPTH, depth)
        _set_property(item.Properties, IPS_XRES, profile.dpi)
        _set_property(item.Properties, IPS_YRES, profile.dpi)
        _maximize_extent(item.Properties, IPS_XEXTENT)
        _maximize_extent(item.Properties, IPS_YEXTENT)

        pages: list[Path] = []
        while True:
            try:
                image = item.Transfer(WIA_FORMAT_BMP)
            except Exception as exc:  # noqa: BLE001 - COM-Fehler
                if _hresult(exc) == HRESULT_PAPER_EMPTY:
                    if not pages:
                        raise ScanError("Kein Papier im Dokumenteneinzug.") from exc
                    break  # Einzug leer = Ende des Stapels
                raise ScanError(_describe(exc, "WIA-Scan fehlgeschlagen")) from exc
            path = workdir / f"page-{len(pages) + 1:04d}.bmp"
            image.SaveFile(str(path))
            pages.append(path)
            if not use_feeder:
                break
        if not pages:
            raise ScanError("WIA-Scan lieferte keine Seiten.")
        return pages


def _maximize_extent(properties: Any, property_id: int) -> None:
    """Scanbereich auf das Maximum setzen (viele Treiber starten mit einem kleinen Fenster)."""
    prop = _find_property(properties, property_id)
    if prop is None:
        return
    try:
        maximum = prop.SubTypeMax
        if maximum:
            prop.Value = maximum
    except Exception as exc:  # noqa: BLE001
        logger.debug("WIA-Scanbereich nicht maximiert: %s", exc)


def _describe(exc: BaseException, fallback: str) -> str:
    code = _hresult(exc)
    return _HRESULT_MESSAGES.get(code, f"{fallback}: {exc}") if code else f"{fallback}: {exc}"
