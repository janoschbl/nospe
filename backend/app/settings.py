"""Einfache lokale Settings-Persistenz (JSON-Datei).

Der Paperless-Token wird lokal gespeichert, aber NIE an das Frontend
zurückgegeben. `/settings` liefert nur `paperless_token_set`.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from .models import AppSettings, FolderFavorite, SaveSettingsRequest

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
    "paperless_token": "",
    "folder_favorites": [],
    "selected_scanner_id": None,
}


def _read_raw() -> dict[str, Any]:
    source_path = _CONFIG_PATH
    if not source_path.exists() and _LEGACY_CONFIG_PATH and _LEGACY_CONFIG_PATH.exists():
        source_path = _LEGACY_CONFIG_PATH
    if not source_path.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(source_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULTS)
    merged = dict(_DEFAULTS)
    merged.update({k: v for k, v in data.items() if k in _DEFAULTS})
    if source_path != _CONFIG_PATH:
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


def get_settings() -> AppSettings:
    raw = _read_raw()
    return AppSettings(
        scan_output_dir=raw["scan_output_dir"],
        paperless_url=raw["paperless_url"],
        paperless_token_set=bool(raw["paperless_token"]),
        folder_favorites=_clean_favorites(raw.get("folder_favorites")),
        selected_scanner_id=raw.get("selected_scanner_id"),
    )


def get_raw_settings() -> dict[str, Any]:
    """Interner Zugriff inkl. Token-Klartext (z.B. für /paperless/test)."""
    return _read_raw()


def save_settings(request: SaveSettingsRequest) -> AppSettings:
    raw = _read_raw()
    raw["scan_output_dir"] = request.scan_output_dir
    raw["paperless_url"] = request.paperless_url
    # Token nur überschreiben, wenn explizit ein neuer mitgegeben wurde.
    if request.paperless_token is not None and request.paperless_token != "":
        raw["paperless_token"] = request.paperless_token
    if request.folder_favorites is not None:
        raw["folder_favorites"] = [favorite.model_dump() for favorite in request.folder_favorites]
    if request.selected_scanner_id is not None:
        raw["selected_scanner_id"] = request.selected_scanner_id or None
    _write_raw(raw)
    return get_settings()
