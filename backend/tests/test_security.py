from __future__ import annotations

import pytest
from conftest import TEST_PORT, TEST_SECRET, make_client
from fastapi.testclient import TestClient

from app import security
from app.main import app


def bare_client(host: str = f"127.0.0.1:{TEST_PORT}") -> TestClient:
    return TestClient(app, base_url=f"http://{host}")


def test_request_without_token_is_rejected():
    assert bare_client().get("/health").status_code == 401


def test_request_with_wrong_token_is_rejected():
    response = bare_client().get("/health", headers={"X-Nospe-Token": "wrong" * 5})
    assert response.status_code == 401


def test_request_with_token_is_accepted():
    assert make_client().get("/health").json()["ok"] is True


@pytest.mark.parametrize("host", ["evil.example:8765", "127.0.0.1:9999", "127.0.0.1", "testserver"])
def test_foreign_host_header_is_rejected_even_with_token(host):
    """DNS-Rebinding: der Browser schickt den Hostnamen der Angreiferseite mit."""
    response = bare_client(host).get("/health", headers={"X-Nospe-Token": TEST_SECRET})
    assert response.status_code == 403


def test_localhost_host_header_is_accepted():
    response = bare_client(f"localhost:{TEST_PORT}").get("/health", headers={"X-Nospe-Token": TEST_SECRET})
    assert response.status_code == 200


def test_foreign_origin_is_rejected_even_with_token():
    response = make_client().get("/health", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403


def test_other_localhost_dev_server_origin_is_rejected_in_release():
    response = make_client().get("/settings", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 403


def test_tauri_origin_gets_cors_headers():
    response = make_client().get("/health", headers={"Origin": "tauri://localhost"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "tauri://localhost"


def test_preflight_from_tauri_is_allowed_without_token():
    response = bare_client().options(
        "/settings",
        headers={
            "Origin": "tauri://localhost",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-nospe-token,content-type",
        },
    )
    assert response.status_code == 200
    assert "x-nospe-token" in response.headers["access-control-allow-headers"].lower()


def test_preflight_from_foreign_origin_is_denied():
    response = bare_client().options(
        "/settings",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-nospe-token",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_unconfigured_secret_fails_closed():
    security._config = security.SecurityConfig()
    assert make_client().get("/health").status_code == 503


def test_short_secret_is_refused():
    with pytest.raises(ValueError):
        security.configure(secret="short", port=1)


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_interactive_docs_are_disabled(path):
    assert make_client().get(path).status_code == 404


def test_emulator_rejects_cross_site_upload():
    from app.emulator.main import app as emulator_app

    client = TestClient(emulator_app, base_url="http://127.0.0.1:8766")
    response = client.post(
        "/emulator/upload",
        files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403


def test_emulator_rejects_rebound_host():
    from app.emulator.main import app as emulator_app

    client = TestClient(emulator_app, base_url="http://evil.example:8766")
    assert client.get("/emulator").status_code == 403
