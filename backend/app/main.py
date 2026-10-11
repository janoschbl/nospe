"""Nospe FastAPI Backend.

Stellt die Endpunkte bereit, gegen die das Tauri/React-Frontend spricht.
Gesichert wird die API durch ``security.SecurityMiddleware`` (Secret-Header,
Host- und Origin-Prüfung); Details dort.

Start:  uv run python run_backend.py
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from . import security
from . import settings as settings_store
from .models import (
    AppSettings,
    HealthResponse,
    PaperlessTestResponse,
    ProfilesResponse,
    SaveSettingsRequest,
    ScanRequest,
    Scanner,
    ScannersResponse,
    ScanResponse,
    TwainStatusResponse,
)
from .paperless import client as paperless_client
from .scanner import profiles as scanner_profiles
from .scanner import scan_service, twain_scan
from .scanner import twain_sources as twain_sources_mod
from .scanner.escl_backend import EsclBackend
from .scanner.registry import ScannerRegistry
from .scanner.scanner_types import ScanError
from .scanner.twain_backend import TwainBackend
from .scanner.twain_lock import TwainBusy
from .scanner.wia_backend import WiaBackend

logger = logging.getLogger(__name__)

registry = ScannerRegistry(
    [TwainBackend(), WiaBackend(), EsclBackend()],
    scan_active=scan_service.scan_active,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    twain_scan.sweep_stale_scan_dirs()
    registry.start()
    try:
        yield
    finally:
        registry.stop()


# Keine automatische Doku (/docs, /openapi.json): unnötige Angriffsfläche.
app = FastAPI(
    title="Nospe Backend",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

# Reihenfolge: zuletzt hinzugefügt = außen. CORS beantwortet Preflights, bevor
# die Sicherheitsprüfung greift; jede echte Anfrage läuft danach durch sie.
app.add_middleware(security.SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        *security.RELEASE_ORIGINS,
        *(security.DEV_ORIGINS if security.dev_mode_enabled() else ()),
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", security.TOKEN_HEADER_CANONICAL],
)


def _scanner_model(scanner) -> Scanner:
    return Scanner(
        id=scanner.id,
        name=scanner.name,
        kind=scanner.kind,
        also_via=list(scanner.also_via),
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, version=__version__)


@app.get("/scanners", response_model=ScannersResponse)
def scanners(refresh: bool = False) -> ScannersResponse:
    """Aktuelle Geräteliste aus dem Cache der Registry.

    Beim allerersten Aufruf (oder mit ``?refresh=true``) wird einmal synchron
    gesucht; sonst antwortet der Endpunkt sofort, auch während eines Scans.
    """
    snapshot = registry.snapshot()
    if refresh or snapshot.updated_at is None:
        registry.refresh(force=True)
        snapshot = registry.snapshot()
    return ScannersResponse(
        scanners=[_scanner_model(s) for s in snapshot.scanners],
        updated_at=snapshot.updated_at,
        scanning=snapshot.scanning,
        errors=snapshot.errors,
    )


@app.get("/scanners/status", response_model=TwainStatusResponse)
def scanners_status() -> TwainStatusResponse:
    try:
        status = twain_sources_mod.get_twain_status(blocking=False)
    except TwainBusy:
        # Es wird gerade gescannt: nichts am DSM anfassen, Cache zeigen.
        snapshot = registry.snapshot()
        names = [s.name for s in snapshot.scanners if s.kind == "twain"]
        return TwainStatusResponse(
            platform="",
            python_bitness=64,
            twain_supported=True,
            dsm_available=True,
            source_count=len(names),
            sources=names,
        )
    env = status.environment
    return TwainStatusResponse(
        platform=env.platform,
        python_bitness=env.python_bitness,
        twain_supported=env.twain_supported,
        dsm_available=env.dsm_available,
        pytwain_version=env.pytwain_version,
        source_count=status.source_count,
        sources=list(status.sources),
        error=env.error,
        hints=list(env.hints),
    )


@app.get("/profiles", response_model=ProfilesResponse)
def profiles() -> ProfilesResponse:
    return ProfilesResponse(profiles=scanner_profiles.get_profiles())


@app.get("/settings", response_model=AppSettings)
def read_settings() -> AppSettings:
    return settings_store.get_settings()


@app.post("/settings", response_model=AppSettings)
def write_settings(request: SaveSettingsRequest) -> AppSettings:
    try:
        return settings_store.save_settings(request)
    except settings_store.SettingsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/paperless/test", response_model=PaperlessTestResponse)
def paperless_test() -> PaperlessTestResponse:
    raw = settings_store.get_raw_settings()
    try:
        url = settings_store.validate_paperless_url(raw.get("paperless_url", ""))
    except settings_store.SettingsError as exc:
        return PaperlessTestResponse(ok=False, message=str(exc))
    return paperless_client.test_connection(url=url, token=raw.get("paperless_token", ""))


@app.post("/scan", response_model=ScanResponse)
def scan(request: ScanRequest) -> ScanResponse:
    """Scan: Bilder erfassen, PDF schreiben, optional Paperless.

    Grundregel: Ein Paperless-Fehler darf den lokalen Scan nicht verlieren.
    """
    profile = scanner_profiles.find_profile(request.profile_id)
    if profile is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unbekanntes Profil: {request.profile_id}",
        )

    if request.color_mode is not None:
        profile = profile.model_copy(update={"color_mode": request.color_mode})

    scanner = registry.resolve(request.scanner_id)
    if scanner is None:
        raise HTTPException(
            status_code=400,
            detail=f"Scanner nicht verfügbar: {request.scanner_id}",
        )

    raw = settings_store.get_raw_settings()
    try:
        output_dir = Path(
            settings_store.validate_output_dir(raw.get("scan_output_dir", str(Path.home())))
        )
    except settings_store.SettingsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        pdf_path = scan_service.perform_scan(
            registry=registry,
            scanner=scanner,
            profile=profile,
            title=request.title,
            output_dir=output_dir,
        )
    except scan_service.ScanInProgress as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ScanError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Scan fehlgeschlagen")
        raise HTTPException(
            status_code=500,
            detail=f"Scan fehlgeschlagen: {exc}",
        ) from exc

    file_path = str(pdf_path.resolve())
    response = ScanResponse(
        ok=True,
        file_path=file_path,
        uploaded_to_paperless=False,
    )

    if request.push_to_paperless:
        try:
            doc_id = paperless_client.upload_document(
                url=settings_store.validate_paperless_url(raw.get("paperless_url", "")),
                token=raw.get("paperless_token", ""),
                file_path=file_path,
                title=request.title,
            )
            response.uploaded_to_paperless = True
            response.paperless_document_id = doc_id
        except Exception as exc:  # noqa: BLE001 - Fehler bewusst in Response
            response.uploaded_to_paperless = False
            response.paperless_error = str(exc)

    return response
