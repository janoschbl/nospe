from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app import settings as settings_store


def test_backend_does_not_serve_emulator_page():
    client = TestClient(app)

    response = client.get("/emulator")

    assert response.status_code == 404


def test_settings_persist_selected_scanner(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(settings_store, "_CONFIG_PATH", config_path)
    monkeypatch.setattr(settings_store, "_DATA_DIR", tmp_path)
    client = TestClient(app)

    response = client.post(
        "/settings",
        json={
            "scan_output_dir": str(tmp_path),
            "paperless_url": "",
            "selected_scanner_id": "scanner-b",
        },
    )

    assert response.status_code == 200
    assert response.json()["selected_scanner_id"] == "scanner-b"
    assert client.get("/settings").json()["selected_scanner_id"] == "scanner-b"
