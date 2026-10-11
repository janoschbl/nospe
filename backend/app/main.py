"""Nospe FastAPI Backend.

Stellt die Endpunkte bereit, gegen die das Tauri/React-Frontend spricht.
TWAIN-Quellenauflistung und Scan/PDF sind implementiert; Paperless-Upload ist noch Stub.

Start:  uv run python run_backend.py
        (oder: uv run uvicorn app.main:app --host 127.0.0.1 --port 8765)
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .models import (
    AppSettings,
    HealthResponse,
    PaperlessTestResponse,
    ProfilesResponse,
    SaveSettingsRequest,
    ScanRequest,
    ScannersResponse,
    ScanResponse,
    TwainStatusResponse,
)
from .paperless import client as paperless_client
from .scanner import profiles as scanner_profiles
from .scanner import twain_scan
from .scanner import twain_sources as twain_sources_mod
from . import settings as settings_store

app = FastAPI(title="Nospe Backend", version=__version__)

# CORS: Vite-Dev (5173) und Tauri-WebView (tauri://, http://tauri.localhost).
# Im MVP großzügig, damit Entwicklung nicht blockiert wird.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "tauri://localhost",
        "http://tauri.localhost",
        "https://tauri.localhost",
    ],
    allow_origin_regex=r"^(https?://localhost(:\d+)?|https?://127\.0\.0\.1(:\d+)?|tauri://localhost)$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, version=__version__)


@app.get("/scanners", response_model=ScannersResponse)
def scanners() -> ScannersResponse:
    return ScannersResponse(scanners=scanner_profiles.get_scanners())


@app.get("/scanners/status", response_model=TwainStatusResponse)
def scanners_status() -> TwainStatusResponse:
    status = twain_sources_mod.get_twain_status()
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
    return settings_store.save_settings(request)


@app.post("/paperless/test", response_model=PaperlessTestResponse)
def paperless_test() -> PaperlessTestResponse:
    raw = settings_store.get_raw_settings()
    return paperless_client.test_connection(
        url=raw.get("paperless_url", ""),
        token=raw.get("paperless_token", ""),
    )


@app.post("/scan", response_model=ScanResponse)
def scan(request: ScanRequest) -> ScanResponse:
    """TWAIN-Scan: Bilder erfassen, PDF schreiben, optional Paperless.

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

    scanner_ids = {scanner.id for scanner in scanner_profiles.get_scanners()}
    if request.scanner_id not in scanner_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Scanner nicht verfügbar: {request.scanner_id}",
        )

    raw = settings_store.get_raw_settings()
    output_dir = Path(raw.get("scan_output_dir", str(Path.home())))

    try:
        pdf_path = twain_scan.perform_scan(
            scanner_id=request.scanner_id,
            profile=profile,
            title=request.title,
            output_dir=output_dir,
        )
    except twain_scan.ScanError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
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
                url=raw.get("paperless_url", ""),
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
