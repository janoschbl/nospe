"""Echter TWAIN-Scan (pytwain) und PDF-Erzeugung."""

from __future__ import annotations

import logging
import os
import re
import sys
import tempfile
from pathlib import Path

from ..models import ScanProfile
from . import emulator_scan
from .pdf_builder import images_to_pdf
from .twain_env import probe_twain_environment

logger = logging.getLogger(__name__)

_FILENAME_SAFE = re.compile(r"[^\w\-.]+", re.UNICODE)


class ScanError(Exception):
    """Scan fehlgeschlagen (für HTTP 400/503)."""


def _sanitize_title(title: str) -> str:
    cleaned = _FILENAME_SAFE.sub("_", title.strip())
    return cleaned.strip("._") or "scan"


def resolve_output_path(output_dir: Path, title: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    base = _sanitize_title(title)
    candidate = output_dir / f"{base}.pdf"
    if not candidate.exists():
        return candidate
    for index in range(1, 1000):
        numbered = output_dir / f"{base}_{index}.pdf"
        if not numbered.exists():
            return numbered
    raise ScanError("Zielordner enthält zu viele Dateien mit gleichem Namen.")


def _try_set_capability(source, cap: int, type_id: int, value) -> None:
    try:
        source.set_capability(cap, type_id, value)
    except Exception as exc:  # noqa: BLE001 - optionale Caps
        logger.debug("TWAIN capability %s nicht gesetzt: %s", cap, exc)


def _set_required_capability(
    source,
    cap: int,
    type_id: int,
    value,
    *,
    mode_label: str,
) -> None:
    try:
        source.set_capability(cap, type_id, value)
    except Exception as exc:  # noqa: BLE001 - TWAIN-Treiberfehler weitergeben
        raise ScanError(
            f"Der Scanner unterstützt den angeforderten Farbmodus „{mode_label}“ nicht: {exc}"
        ) from exc


def _apply_profile(source, profile: ScanProfile) -> None:
    import twain
    from twain.lowlevel import constants as cap

    resolution = float(profile.dpi)
    _try_set_capability(source, cap.ICAP_XRESOLUTION, cap.TWTY_FIX32, resolution)
    _try_set_capability(source, cap.ICAP_YRESOLUTION, cap.TWTY_FIX32, resolution)

    pixel_type, bit_depth, mode_label = {
        "gray": (cap.TWPT_GRAY, 8, "Grau"),
        "bw": (cap.TWPT_BW, 1, "Schwarzweiß"),
        "color": (cap.TWPT_RGB, 24, "Farbe"),
    }[profile.color_mode]
    # ICAP_PIXELTYPE alone is not sufficient for many drivers: RGB needs
    # 24 bits per pixel. Do not silently fall back to gray when this is
    # explicitly requested by the user.
    _set_required_capability(
        source,
        cap.ICAP_PIXELTYPE,
        cap.TWTY_UINT16,
        pixel_type,
        mode_label=mode_label,
    )
    _set_required_capability(
        source,
        cap.ICAP_BITDEPTH,
        cap.TWTY_UINT16,
        bit_depth,
        mode_label=mode_label,
    )

    if profile.duplex:
        _try_set_capability(source, cap.CAP_DUPLEXENABLED, cap.TWTY_BOOL, True)
    else:
        _try_set_capability(source, cap.CAP_DUPLEXENABLED, cap.TWTY_BOOL, False)

    if profile.adf:
        _try_set_capability(source, cap.CAP_FEEDERENABLED, cap.TWTY_BOOL, True)


def _acquire_images(
    product_name: str,
    profile: ScanProfile,
    *,
    show_ui: bool = False,
) -> list[Path]:
    import twain

    images: list[Path] = []
    temp_dir = Path(tempfile.mkdtemp(prefix="nospe-scan-"))

    def after(image, remaining: int) -> None:
        page_index = len(images) + 1
        bmp_path = temp_dir / f"page-{page_index:04d}.bmp"
        image.save(str(bmp_path))
        image.close()
        images.append(bmp_path)
        logger.info(
            "TWAIN-Seite %s übernommen (%s verbleibend)",
            page_index,
            remaining,
        )

    with twain.SourceManager() as sm:
        source = sm.open_source(product_name=product_name)
        if source is None:
            raise ScanError(f'TWAIN-Quelle „{product_name}" nicht gefunden.')

        try:
            _apply_profile(source, profile)
            source.acquire_natively(after=after, show_ui=show_ui, modal=False)
        finally:
            source.close()

    if not images:
        raise ScanError("TWAIN-Scan lieferte keine Seiten.")

    return images


def _scan_via_twain(
    scanner_id: str,
    profile: ScanProfile,
    output_path: Path,
) -> Path:
    env = probe_twain_environment()
    if not env.dsm_available:
        raise ScanError(env.error or "TWAIN DSM nicht verfügbar.")

    show_ui = os.environ.get("NOSPE_TWAIN_SHOW_UI", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }

    page_files: list[Path] = []
    try:
        page_files = _acquire_images(scanner_id, profile, show_ui=show_ui)
        images_to_pdf(page_files, output_path)
    finally:
        if page_files:
            temp_dir = page_files[0].parent
            for path in page_files:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            try:
                temp_dir.rmdir()
            except OSError:
                pass

    if emulator_scan.is_virtual_scanner(scanner_id):
        try:
            from ..emulator import spool as emulator_spool

            emulator_spool.consume_job()
        except Exception:
            logger.debug("Emulator-Spool nach TWAIN-Scan nicht geleert", exc_info=True)

    return output_path


def perform_scan(
    *,
    scanner_id: str,
    profile: ScanProfile,
    title: str,
    output_dir: Path,
) -> Path:
    """Führt einen Scan aus und gibt den Pfad der erzeugten PDF zurück."""
    if sys.platform != "win32":
        raise ScanError("Scannen wird nur unter Windows unterstützt.")

    output_path = resolve_output_path(output_dir, title)

    if emulator_scan.is_virtual_scanner(scanner_id):
        if emulator_scan.prefer_direct_emulator_scan():
            return emulator_scan.scan_from_emulator_spool(output_path)

        try:
            return _scan_via_twain(scanner_id, profile, output_path)
        except ScanError:
            raise
        except Exception as exc:
            logger.warning(
                "TWAIN-Scan über Nospe Virtual Scanner fehlgeschlagen, "
                "Fallback auf Emulator-Spool: %s: %s",
                type(exc).__name__,
                exc or repr(exc),
            )
            if output_path.exists():
                output_path.unlink(missing_ok=True)
            return emulator_scan.scan_from_emulator_spool(output_path)

    return _scan_via_twain(scanner_id, profile, output_path)
