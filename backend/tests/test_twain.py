from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.models import Scanner
from app.scanner import twain_env, twain_sources


def test_python_bitness_is_int():
    assert twain_env.python_bitness() in (32, 64)


def test_list_scanners_from_mocked_source_list():
    mock_sm = MagicMock()
    mock_sm.source_list = ["EPSON DS-410", "Nospe Virtual Scanner"]
    mock_sm.__enter__ = MagicMock(return_value=mock_sm)
    mock_sm.__exit__ = MagicMock(return_value=False)

    ready = twain_env.TwainEnvironment(
        platform="Windows",
        python_bitness=64,
        twain_supported=True,
        dsm_available=True,
        pytwain_version="2.3.0",
    )

    with (
        patch.object(twain_sources, "probe_twain_environment", return_value=ready),
        patch.object(twain_sources, "is_emulator_running", return_value=False),
        patch("twain.SourceManager", return_value=mock_sm),
    ):
        scanners = twain_sources.list_scanners()

    assert scanners == [Scanner(id="EPSON DS-410", name="EPSON DS-410")]


def test_status_excludes_virtual_scanner_when_emulator_is_stopped():
    mock_sm = MagicMock()
    mock_sm.source_list = ["Nospe Virtual Scanner", "EPSON DS-410"]
    mock_sm.__enter__ = MagicMock(return_value=mock_sm)
    mock_sm.__exit__ = MagicMock(return_value=False)
    ready = twain_env.TwainEnvironment(
        platform="Windows",
        python_bitness=64,
        twain_supported=True,
        dsm_available=True,
    )

    with (
        patch.object(twain_sources, "probe_twain_environment", return_value=ready),
        patch.object(twain_sources, "is_emulator_running", return_value=False),
        patch("twain.SourceManager", return_value=mock_sm),
    ):
        status = twain_sources.get_twain_status()

    assert status.sources == ("EPSON DS-410",)
    assert status.source_count == 1


def test_virtual_scanner_is_visible_only_when_separate_emulator_runs():
    names = ["Nospe Virtual Scanner", "EPSON DS-410"]

    with patch.object(twain_sources, "is_emulator_running", return_value=False):
        assert twain_sources.visible_scanner_names(names) == ["EPSON DS-410"]

    with patch.object(twain_sources, "is_emulator_running", return_value=True):
        assert twain_sources.visible_scanner_names(names) == [
            "EPSON DS-410",
            "Nospe Virtual Scanner",
        ]


def test_list_scanners_empty_when_dsm_unavailable():
    blocked = twain_env.TwainEnvironment(
        platform="Windows",
        python_bitness=64,
        twain_supported=True,
        dsm_available=False,
        error="DSM missing",
    )
    with patch.object(twain_sources, "probe_twain_environment", return_value=blocked):
        assert twain_sources.list_scanners() == []


def test_scanners_status_endpoint():
    ready = twain_env.TwainEnvironment(
        platform="Windows-10",
        python_bitness=64,
        twain_supported=True,
        dsm_available=True,
        pytwain_version="2.3.0",
    )
    status = twain_sources.TwainSourceStatus(
        environment=ready,
        source_count=1,
        sources=("EPSON DS-410",),
    )
    with patch.object(twain_sources, "get_twain_status", return_value=status):
        client = TestClient(app)
        response = client.get("/scanners/status")

    assert response.status_code == 200
    body = response.json()
    assert body["python_bitness"] == 64
    assert body["dsm_available"] is True
    assert body["source_count"] == 1
    assert body["sources"] == ["EPSON DS-410"]


def test_scanners_endpoint_uses_list_scanners():
    with patch(
        "app.scanner.profiles.list_scanners",
        return_value=[Scanner(id="Test DS", name="Test DS")],
    ):
        client = TestClient(app)
        response = client.get("/scanners")

    assert response.status_code == 200
    assert response.json()["scanners"] == [{"id": "Test DS", "name": "Test DS"}]
