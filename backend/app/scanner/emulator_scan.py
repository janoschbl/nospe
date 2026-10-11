"""Scan über den Nospe TWAIN-PDF-Emulator-Spool (ohne vollständigen DS-Transfer)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from ..emulator import spool as emulator_spool
from ..emulator.models import EmulatorJob
from .pdf_builder import images_to_pdf

VIRTUAL_SCANNER_NAME = "Nospe Virtual Scanner"


class EmulatorScanError(Exception):
    """Emulator-Spool nicht scanbereit."""


def is_virtual_scanner(scanner_id: str) -> bool:
    return scanner_id.strip() == VIRTUAL_SCANNER_NAME


def prefer_direct_emulator_scan() -> bool:
    """Erzwingt Spool-Scan statt TWAIN (Debug / wenn .ds noch alt ist)."""
    return os.environ.get("NOSPE_EMULATOR_DIRECT_SCAN", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _mark_transferring(job: EmulatorJob) -> None:
    manifest = emulator_spool.manifest_path()
    payload = job.model_dump()
    payload["status"] = "transferring"
    manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def scan_from_emulator_spool(output_path: Path) -> Path:
    """Baut eine PDF aus den gerenderten Emulator-Seiten."""
    job_response = emulator_spool.get_job()
    if not job_response.active:
        raise EmulatorScanError(
            "Kein aktiver Emulator-Job. PDF unter http://127.0.0.1:8766/emulator hochladen."
        )

    job = job_response
    if job.status == "transferring":
        raise EmulatorScanError("Emulator-Job wird bereits übertragen.")
    if job.status != "ready":
        raise EmulatorScanError(f"Emulator-Job hat Status „{job.status}“, erwartet „ready“.")

    page_paths = [Path(page.path) for page in job.pages]
    missing = [str(path) for path in page_paths if not path.is_file()]
    if missing:
        raise EmulatorScanError(
            f"Emulator-Seiten fehlen auf der Platte: {', '.join(missing[:3])}"
        )

    _mark_transferring(job)
    try:
        images_to_pdf(page_paths, output_path)
    except Exception:
        # Status zurück auf ready, damit ein erneuter Versuch möglich ist.
        ready_payload = job.model_dump()
        ready_payload["status"] = "ready"
        emulator_spool.manifest_path().write_text(
            json.dumps(ready_payload, indent=2),
            encoding="utf-8",
        )
        raise
    finally:
        emulator_spool.consume_job()

    return output_path
