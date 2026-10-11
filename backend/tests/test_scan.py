from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from conftest import make_client
from PIL import Image
import pytest
from twain.lowlevel import constants as twain_constants

from app.main import app
from app.models import ScanProfile, ScanRequest
from app.scanner.scanner_types import DiscoveredScanner
from app.scanner import twain_scan
from app.scanner.pdf_builder import images_to_pdf

VIRTUAL = DiscoveredScanner(kind="twain", native_id="Nospe Virtual Scanner", name="Nospe Virtual Scanner")


def test_resolve_output_path_avoids_collisions(tmp_path: Path):
    first = twain_scan.resolve_output_path(tmp_path, "Rechnung")
    first.write_bytes(b"%PDF-1.4")
    second = twain_scan.resolve_output_path(tmp_path, "Rechnung")
    assert first.name == "Rechnung.pdf"
    assert second.name == "Rechnung_1.pdf"


def test_resolve_output_path_increments_numeric_suffix(tmp_path: Path):
    for name in ("Rechnung.pdf", "Rechnung_1.pdf"):
        (tmp_path / name).write_bytes(b"%PDF-1.4")

    assert twain_scan.resolve_output_path(tmp_path, "Rechnung").name == "Rechnung_2.pdf"


def test_scan_endpoint_writes_pdf(tmp_path: Path):
    profile = ScanProfile(
        id="duplex_gray_300",
        name="Duplex Grau 300 DPI",
        duplex=True,
        adf=True,
        dpi=300,
        color_mode="gray",
    )
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")

    with (
        patch("app.scanner.profiles.find_profile", return_value=profile),
        patch("app.main.registry.resolve", return_value=VIRTUAL),
        patch("app.main.scan_service.perform_scan", return_value=pdf_path),
        patch("app.settings.get_raw_settings", return_value={"scan_output_dir": str(tmp_path)}),
    ):
        client = make_client()
        response = client.post(
            "/scan",
            json=ScanRequest(
                scanner_id="Nospe Virtual Scanner",
                profile_id="duplex_gray_300",
                title="Test Scan",
                push_to_paperless=False,
            ).model_dump(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["file_path"].endswith("scan.pdf")


def test_scan_endpoint_uses_requested_color_mode(tmp_path: Path):
    profile = ScanProfile(
        id="duplex_gray_300",
        name="Duplex Grau 300 DPI",
        duplex=True,
        adf=True,
        dpi=300,
        color_mode="gray",
    )
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")

    with (
        patch("app.scanner.profiles.find_profile", return_value=profile),
        patch("app.main.registry.resolve", return_value=VIRTUAL),
        patch("app.main.scan_service.perform_scan", return_value=pdf_path) as perform_scan,
        patch("app.settings.get_raw_settings", return_value={"scan_output_dir": str(tmp_path)}),
    ):
        response = make_client().post(
            "/scan",
            json={
                "scanner_id": "Nospe Virtual Scanner",
                "profile_id": "duplex_gray_300",
                "title": "Farbscan",
                "color_mode": "color",
            },
        )

    assert response.status_code == 200
    assert perform_scan.call_args.kwargs["profile"].color_mode == "color"


def test_images_to_pdf_multipage(tmp_path: Path):
    one = tmp_path / "one.png"
    two = tmp_path / "two.png"
    Image.new("L", (32, 32), color=200).save(one)
    Image.new("L", (32, 32), color=80).save(two)

    output = tmp_path / "out.pdf"
    images_to_pdf([one, two], output)
    assert output.exists()
    assert output.stat().st_size > 0


@pytest.mark.parametrize(
    ("color_mode", "expected_pixel_type", "expected_bit_depth"),
    [
        ("color", 2, 24),
        ("gray", 1, 8),
        ("bw", 0, 1),
    ],
)
def test_apply_profile_sets_matching_pixel_type_and_depth(
    color_mode: str,
    expected_pixel_type: int,
    expected_bit_depth: int,
):
    source = MagicMock()
    profile = ScanProfile(
        id="test",
        name="Test",
        duplex=False,
        adf=False,
        dpi=300,
        color_mode=color_mode,
    )

    twain_scan._apply_profile(source, profile)

    assert any(call.args == (
        twain_constants.ICAP_PIXELTYPE,
        twain_constants.TWTY_UINT16,
        expected_pixel_type,
    ) for call in source.set_capability.call_args_list)
    assert any(call.args == (
        twain_constants.ICAP_BITDEPTH,
        twain_constants.TWTY_UINT16,
        expected_bit_depth,
    ) for call in source.set_capability.call_args_list)


def test_apply_profile_fails_when_requested_color_cannot_be_enabled():
    source = MagicMock()
    source.set_capability.side_effect = RuntimeError("RGB unsupported")
    profile = ScanProfile(
        id="color",
        name="Farbe",
        duplex=False,
        adf=False,
        dpi=300,
        color_mode="color",
    )

    with pytest.raises(twain_scan.ScanError, match="Farbe"):
        twain_scan._apply_profile(source, profile)
