"""Pydantic-Modelle für die Nospe-API.

Diese spiegeln exakt den Contract, gegen den das Frontend (frontend/src/types.ts)
und der API-Client (frontend/src/api.ts) arbeiten.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

ColorMode = Literal["gray", "color", "bw"]


class HealthResponse(BaseModel):
    ok: bool = True
    version: str = "0.1.0"


class Scanner(BaseModel):
    #: Eindeutig und stabil: ``twain:<Name>``, ``wia:<DeviceID>`` oder ``escl:<UUID>``.
    id: str
    name: str
    #: Zugangsart: "twain" | "wia" | "escl"
    kind: str = "twain"
    #: Weitere Zugänge zum selben Gerät (z. B. WIA-ID, wenn TWAIN bevorzugt wurde).
    also_via: list[str] = []


class ScannersResponse(BaseModel):
    scanners: list[Scanner]
    #: Unix-Zeit des letzten Suchlaufs; ``None`` solange noch nie gesucht wurde.
    updated_at: Optional[float] = None
    #: Läuft gerade ein Scan? Dann ist die Liste der Stand vor dem Scan.
    scanning: bool = False
    #: Fehler je Zugangsart, z. B. ``{"twain": "TWAIN DSM nicht ladbar"}``.
    errors: dict[str, str] = {}


class TwainStatusResponse(BaseModel):
    """TWAIN-Umgebung und Quellenliste (Phase 0/1 Diagnose)."""

    platform: str
    python_bitness: int
    twain_supported: bool
    dsm_available: bool
    pytwain_version: Optional[str] = None
    source_count: int = 0
    sources: list[str] = []
    error: Optional[str] = None
    hints: list[str] = []


class ScanProfile(BaseModel):
    id: str
    name: str
    duplex: bool
    adf: bool
    dpi: int
    color_mode: ColorMode


class ProfilesResponse(BaseModel):
    profiles: list[ScanProfile]


class ScanRequest(BaseModel):
    scanner_id: str
    profile_id: str
    title: str = ""
    # UI-Auswahl überschreibt nur für diesen Scan den Profil-Farbmodus.
    color_mode: Optional[ColorMode] = None
    push_to_paperless: bool = False


class ScanResponse(BaseModel):
    ok: bool
    file_path: str
    uploaded_to_paperless: bool = False
    paperless_document_id: Optional[str] = None
    paperless_error: Optional[str] = None


class AppSettings(BaseModel):
    """Wird an das Frontend zurückgegeben. Enthält NIE den Token-Klartext."""

    scan_output_dir: str
    paperless_url: str
    paperless_token_set: bool
    folder_favorites: list["FolderFavorite"] = []
    selected_scanner_id: Optional[str] = None


class SaveSettingsRequest(BaseModel):
    scan_output_dir: str
    paperless_url: str
    # Optional: nur gesetzt, wenn der User wirklich einen neuen Token eingibt.
    paperless_token: Optional[str] = None
    # Optional, damit schnelle Zielordnerwechsel bestehende Favoriten behalten.
    folder_favorites: Optional[list["FolderFavorite"]] = None
    selected_scanner_id: Optional[str] = None


class FolderFavorite(BaseModel):
    id: str
    label: str
    path: str
    icon: str = "folder"


class PaperlessTestResponse(BaseModel):
    ok: bool
    message: str
