from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

from .models import EmulatorInactiveJob, EmulatorJob, EmulatorJobResponse, EmulatorPage

DPI = 300
COLOR_MODE = "color"
DEFAULT_MAX_BYTES = 50 * 1024 * 1024


class EmulatorSpoolError(Exception):
    status_code = 400


class EmulatorUploadConflict(EmulatorSpoolError):
    status_code = 409


class EmulatorUploadTooLarge(EmulatorSpoolError):
    status_code = 413


def spool_root() -> Path:
    configured = os.environ.get("NOSPE_EMULATOR_SPOOL_DIR")
    if configured:
        return Path(configured)

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Nospe" / "twain-emulator"

    return Path.home() / "AppData" / "Local" / "Nospe" / "twain-emulator"


def max_upload_bytes() -> int:
    raw = os.environ.get("NOSPE_EMULATOR_MAX_BYTES")
    if not raw:
        return DEFAULT_MAX_BYTES
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MAX_BYTES


def active_dir() -> Path:
    return spool_root() / "active"


def manifest_path() -> Path:
    return active_dir() / "manifest.json"


def get_job() -> EmulatorJobResponse:
    path = manifest_path()
    if not path.exists():
        return EmulatorInactiveJob()
    try:
        return EmulatorJob.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return EmulatorInactiveJob()


def consume_job() -> EmulatorInactiveJob:
    active = active_dir()
    if active.exists():
        shutil.rmtree(active)
    return EmulatorInactiveJob()


def create_job(filename: str, content_type: str | None, data: bytes) -> EmulatorJob:
    _validate_upload(filename, content_type, data)

    current = get_job()
    if current.active and current.status == "transferring":
        raise EmulatorUploadConflict("Ein Scantransfer ist aktiv.")

    root = spool_root()
    root.mkdir(parents=True, exist_ok=True)
    job_id = uuid.uuid4().hex
    tmp = root / f".incoming-{job_id}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    try:
        original = tmp / "original.pdf"
        original.write_bytes(data)
        final_active = active_dir()
        pages = _render_pdf(original, tmp, final_active)
        if not pages:
            raise EmulatorSpoolError("Die PDF enthält keine Seiten.")

        job = EmulatorJob(
            job_id=job_id,
            status="ready",
            original_pdf=str((final_active / "original.pdf").resolve()),
            page_count=len(pages),
            dpi=DPI,
            color_mode=COLOR_MODE,
            pages=pages,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        (tmp / "manifest.json").write_text(
            job.model_dump_json(indent=2),
            encoding="utf-8",
        )

        active = active_dir()
        if active.exists():
            shutil.rmtree(active)
        tmp.replace(active)
        return EmulatorJob.model_validate_json(
            manifest_path().read_text(encoding="utf-8"),
        )
    except Exception:
        if tmp.exists():
            shutil.rmtree(tmp)
        raise


def _validate_upload(filename: str, content_type: str | None, data: bytes) -> None:
    if not data:
        raise EmulatorSpoolError("Die hochgeladene PDF ist leer.")
    if len(data) > max_upload_bytes():
        raise EmulatorUploadTooLarge("Die hochgeladene PDF ist zu groß.")
    lower_name = (filename or "").lower()
    looks_like_pdf = lower_name.endswith(".pdf") or content_type == "application/pdf"
    if not looks_like_pdf or not data.startswith(b"%PDF-"):
        raise EmulatorSpoolError("Es wird genau eine PDF-Datei erwartet.")


def _render_pdf(pdf_path: Path, job_dir: Path, final_active: Path) -> list[EmulatorPage]:
    pages_dir = job_dir / "pages"
    pages_dir.mkdir()
    rendered: list[EmulatorPage] = []

    try:
        pdf = pdfium.PdfDocument(str(pdf_path))
        scale = DPI / 72
        for index in range(len(pdf)):
            page = pdf[index]
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil()
            if image.mode != "RGB":
                image = image.convert("RGB")
            page_path = pages_dir / f"page-{index + 1:04d}.png"
            image.save(page_path)
            rendered.append(
                EmulatorPage(
                    index=index,
                    path=str((final_active / "pages" / page_path.name).resolve()),
                    width_px=image.width,
                    height_px=image.height,
                ),
            )
            image.close()
            page.close()
        pdf.close()
    except Exception as exc:
        raise EmulatorSpoolError(f"PDF konnte nicht gerendert werden: {exc}") from exc

    return rendered
