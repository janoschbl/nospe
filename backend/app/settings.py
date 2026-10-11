"""Einfache lokale Settings-Persistenz (JSON-Datei).

Der Paperless-Token wird nur verschlüsselt (DPAPI, siehe ``secret_store``)
gespeichert und NIE an das Frontend zurückgegeben. `/settings` liefert nur
`paperless_token_set`. Der Token ist an den Origin der Paperless-URL gebunden,
unter der er eingegeben wurde: wird die URL auf einen anderen Server geändert,
muss der Token neu eingegeben werden. Sonst könnte ein manipulierter Request den
gespeicherten Token an einen fremden Server schicken.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from . import secret_store
from .models import AppSettings, FolderFavorite, SaveSettingsRequest

logger = logging.getLogger(__name__)


class SettingsError(ValueError):
    """Ungültige Einstellung (wird als HTTP 400 gemeldet)."""


# Im PyInstaller-Onefile-Build liegt das Paket in einem temporären Verzeichnis.
# Programmdateien werden bei Updates ersetzt; Einstellungen gehören daher in
# den Roaming-AppData-Ordner, nicht neben nospe.exe.
if getattr(sys, "frozen", False):
    _DATA_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "Nospe"
    _LEGACY_CONFIG_PATH = (
        Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Nospe" / "config.json"
    )
else:
    _DATA_DIR = Path(__file__).resolve().parent.parent / "data"
    _LEGACY_CONFIG_PATH: Path | None = None
_CONFIG_PATH = _DATA_DIR / "config.json"

_DEFAULTS: dict[str, Any] = {
    "scan_output_dir": str(Path.home() / "Documents" / "Scans"),
    "paperless_url": "",
    "paperless_token_enc": "",
    "paperless_token_origin": "",
    "folder_favorites": [],
    "selected_scanner_id": None,
}


def _read_raw() -> dict[str, Any]:
    """Liest die gespeicherte Konfiguration (Token nur verschlüsselt)."""
    source_path = _CONFIG_PATH
    if not source_path.exists() and _LEGACY_CONFIG_PATH and _LEGACY_CONFIG_PATH.exists():
        source_path = _LEGACY_CONFIG_PATH
    if not source_path.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(source_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULTS)
    if not isinstance(data, dict):
        return dict(_DEFAULTS)
    merged = dict(_DEFAULTS)
    merged.update({k: v for k, v in data.items() if k in _DEFAULTS})

    migrated = False
    legacy_token = data.get("paperless_token")
    if isinstance(legacy_token, str) and legacy_token:
        # Altbestand: Klartext-Token verschlüsseln und an die aktuelle URL binden.
        merged["paperless_token_enc"] = secret_store.protect(legacy_token)
        merged["paperless_token_origin"] = origin_of(str(merged.get("paperless_url", "")))
        migrated = True
    if migrated or source_path != _CONFIG_PATH:
        _write_raw(merged)
    return merged


def _write_raw(data: dict[str, Any]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _CONFIG_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, _CONFIG_PATH)


def _clean_favorites(value: Any) -> list[FolderFavorite]:
    if not isinstance(value, list):
        return []

    favorites: list[FolderFavorite] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip()
        if not path or path in seen:
            continue
        seen.add(path)
        label = str(item.get("label", "")).strip() or Path(path).name or path
        favorite_id = str(item.get("id", "")).strip() or f"favorite-{index + 1}"
        icon = str(item.get("icon", "folder")).strip() or "folder"
        favorites.append(
            FolderFavorite(id=favorite_id, label=label, path=path, icon=icon)
        )
    return favorites


def origin_of(url: str) -> str:
    """Normalisierter Origin (``scheme://host[:port]``) oder leer."""
    try:
        parts = urlsplit(url.strip())
        host = parts.hostname
        port = parts.port
    except ValueError:
        return ""
    if parts.scheme not in {"http", "https"} or not host:
        return ""
    default_port = 443 if parts.scheme == "https" else 80
    suffix = f":{port}" if port and port != default_port else ""
    return f"{parts.scheme}://{host.lower()}{suffix}"


def _is_local_host(host: str) -> bool:
    """Hosts, bei denen unverschlüsseltes HTTP vertretbar ist (LAN/Loopback)."""
    host = host.lower().rstrip(".")
    if host == "localhost" or host.endswith((".local", ".lan", ".internal", ".home.arpa")):
        return True
    if "." not in host and ":" not in host:
        return True  # Einzel-Label-Hostname, z. B. http://paperless:8000
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local


def validate_paperless_url(value: str) -> str:
    """Prüft die Paperless-URL und gibt sie normalisiert zurück (leer erlaubt)."""
    url = value.strip()
    if not url:
        return ""
    try:
        parts = urlsplit(url)
        host = parts.hostname
        parts.port  # noqa: B018 - löst ValueError bei ungültigem Port aus
    except ValueError as exc:
        raise SettingsError("Paperless-URL ist ungültig.") from exc
    if parts.scheme not in {"http", "https"} or not host:
        raise SettingsError("Paperless-URL muss mit http:// oder https:// beginnen.")
    if parts.username or parts.password:
        raise SettingsError("Paperless-URL darf keine Zugangsdaten enthalten.")
    if parts.query or parts.fragment:
        raise SettingsError("Paperless-URL darf keine Parameter oder Anker enthalten.")
    if parts.scheme == "http" and not _is_local_host(host):
        raise SettingsError(
            "Unverschlüsseltes http:// ist nur im lokalen Netz erlaubt. Bitte https:// verwenden."
        )
    return url.rstrip("/") if parts.path in {"", "/"} else url


def _forbidden_output_roots() -> list[Path]:
    roots: list[Path] = []
    if sys.platform == "win32":
        for name in ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "ProgramData"):
            value = os.environ.get(name)
            if value:
                roots.append(Path(value))
        appdata = os.environ.get("APPDATA")
        if appdata:
            roots.append(Path(appdata) / "Microsoft" / "Windows" / "Start Menu")
        programdata = os.environ.get("ProgramData")
        if programdata:
            roots.append(Path(programdata) / "Microsoft" / "Windows" / "Start Menu")
    else:
        roots.extend(Path(p) for p in ("/etc", "/usr", "/bin", "/sbin", "/boot", "/sys", "/proc", "/dev"))
    return roots


def validate_output_dir(value: str) -> str:
    """Zielordner muss absolut sein und darf nicht in Systembereichen liegen."""
    text = value.strip()
    if not text or "\x00" in text:
        raise SettingsError("Zielordner fehlt oder ist ungültig.")
    path = Path(text)
    if not path.is_absolute():
        raise SettingsError("Zielordner muss ein absoluter Pfad sein.")
    resolved = Path(os.path.normpath(os.path.abspath(text)))
    for root in _forbidden_output_roots():
        root_norm = Path(os.path.normpath(os.path.abspath(root)))
        a, b = str(resolved).casefold(), str(root_norm).casefold()
        if a == b or a.startswith(b.rstrip("\\/") + os.sep):
            raise SettingsError("In diesen Systemordner darf Nospe nicht speichern.")
    return text


def _token_for_current_url(raw: dict[str, Any]) -> str:
    """Token im Klartext, aber nur wenn er zum aktuellen URL-Origin gehört."""
    stored = str(raw.get("paperless_token_enc") or "")
    if not stored:
        return ""
    origin = origin_of(str(raw.get("paperless_url", "")))
    if not origin or origin != raw.get("paperless_token_origin"):
        return ""
    try:
        return secret_store.unprotect(stored)
    except secret_store.SecretStoreError:
        logger.warning("Gespeicherter Paperless-Token ist nicht lesbar und wird ignoriert.")
        return ""


def get_settings() -> AppSettings:
    raw = _read_raw()
    return AppSettings(
        scan_output_dir=raw["scan_output_dir"],
        paperless_url=raw["paperless_url"],
        paperless_token_set=bool(_token_for_current_url(raw)),
        folder_favorites=_clean_favorites(raw.get("folder_favorites")),
        selected_scanner_id=raw.get("selected_scanner_id"),
    )


def get_raw_settings() -> dict[str, Any]:
    """Interner Zugriff inkl. Token-Klartext (nur für Paperless-Client, nie an die UI)."""
    raw = _read_raw()
    result = {k: v for k, v in raw.items() if k not in {"paperless_token_enc", "paperless_token_origin"}}
    result["paperless_token"] = _token_for_current_url(raw)
    return result


def save_settings(request: SaveSettingsRequest) -> AppSettings:
    output_dir = validate_output_dir(request.scan_output_dir)
    url = validate_paperless_url(request.paperless_url)

    raw = _read_raw()
    new_token = request.paperless_token or ""
    new_origin = origin_of(url)
    old_origin = str(raw.get("paperless_token_origin") or "")

    if new_token:
        if not new_origin:
            raise SettingsError("Für einen Token wird zuerst eine Paperless-URL benötigt.")
        raw["paperless_token_enc"] = secret_store.protect(new_token)
        raw["paperless_token_origin"] = new_origin
    elif raw.get("paperless_token_enc") and new_origin != old_origin:
        if new_origin:
            raise SettingsError(
                "Die Paperless-URL zeigt auf einen anderen Server. "
                "Bitte den Token für diesen Server neu eingeben."
            )
        # URL wurde geleert: gespeicherten Token nicht weiter vorhalten.
        raw["paperless_token_enc"] = ""
        raw["paperless_token_origin"] = ""

    raw["scan_output_dir"] = output_dir
    raw["paperless_url"] = url
    if request.folder_favorites is not None:
        raw["folder_favorites"] = [favorite.model_dump() for favorite in request.folder_favorites]
    if request.selected_scanner_id is not None:
        raw["selected_scanner_id"] = request.selected_scanner_id or None
    _write_raw(raw)
    return get_settings()
