from __future__ import annotations

import json

import pytest
from conftest import make_client

from app import secret_store
from app import settings as store
from app.models import SaveSettingsRequest


@pytest.fixture()
def config(tmp_path, monkeypatch):
    path = tmp_path / "config" / "config.json"
    monkeypatch.setattr(store, "_DATA_DIR", path.parent)
    monkeypatch.setattr(store, "_CONFIG_PATH", path)
    monkeypatch.setattr(store, "_LEGACY_CONFIG_PATH", None)
    return path


def request(tmp_path, **overrides):
    values = {"scan_output_dir": str(tmp_path / "scans"), "paperless_url": "https://paperless.example"}
    values.update(overrides)
    return SaveSettingsRequest(**values)


def test_token_is_stored_encrypted_not_in_plaintext(config, tmp_path):
    store.save_settings(request(tmp_path, paperless_token="s3cret-token-value"))

    on_disk = config.read_text()
    assert "s3cret-token-value" not in on_disk
    assert json.loads(on_disk)["paperless_token_enc"]
    assert store.get_raw_settings()["paperless_token"] == "s3cret-token-value"
    assert store.get_settings().paperless_token_set is True


def test_token_is_never_returned_by_api(config, tmp_path):
    store.save_settings(request(tmp_path, paperless_token="s3cret-token-value"))
    body = make_client().get("/settings").text
    assert "s3cret-token-value" not in body


def test_changing_url_to_other_server_requires_new_token(config, tmp_path):
    store.save_settings(request(tmp_path, paperless_token="s3cret-token-value"))

    with pytest.raises(store.SettingsError, match="anderen Server"):
        store.save_settings(request(tmp_path, paperless_url="https://attacker.example"))

    assert store.get_settings().paperless_url == "https://paperless.example"
    assert store.get_raw_settings()["paperless_token"] == "s3cret-token-value"


def test_url_change_via_api_cannot_exfiltrate_token(config, tmp_path):
    client = make_client()
    store.save_settings(request(tmp_path, paperless_token="s3cret-token-value"))

    response = client.post(
        "/settings",
        json={"scan_output_dir": str(tmp_path), "paperless_url": "https://attacker.example"},
    )

    assert response.status_code == 400
    assert store.get_raw_settings()["paperless_url"] == "https://paperless.example"


def test_same_origin_path_change_keeps_token(config, tmp_path):
    store.save_settings(request(tmp_path, paperless_token="tok-123456"))
    store.save_settings(request(tmp_path, paperless_url="https://paperless.example/paperless"))
    assert store.get_raw_settings()["paperless_token"] == "tok-123456"


def test_new_token_with_new_url_is_accepted(config, tmp_path):
    store.save_settings(request(tmp_path, paperless_token="old-token"))
    store.save_settings(request(tmp_path, paperless_url="https://other.example", paperless_token="new-token"))
    assert store.get_raw_settings()["paperless_token"] == "new-token"


def test_clearing_url_drops_token(config, tmp_path):
    store.save_settings(request(tmp_path, paperless_token="tok-123456"))
    store.save_settings(request(tmp_path, paperless_url=""))
    assert store.get_settings().paperless_token_set is False


def test_token_ignored_if_config_was_hand_edited_to_other_origin(config, tmp_path):
    store.save_settings(request(tmp_path, paperless_token="tok-123456"))
    data = json.loads(config.read_text())
    data["paperless_url"] = "https://attacker.example"
    config.write_text(json.dumps(data))

    assert store.get_raw_settings()["paperless_token"] == ""
    assert store.get_settings().paperless_token_set is False


def test_legacy_plaintext_token_is_migrated(config, tmp_path):
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({
        "scan_output_dir": str(tmp_path),
        "paperless_url": "https://paperless.example",
        "paperless_token": "legacy-token",
    }))

    assert store.get_raw_settings()["paperless_token"] == "legacy-token"
    migrated = config.read_text()
    assert "legacy-token" not in migrated
    assert '"paperless_token"' not in migrated


def test_corrupt_secret_does_not_crash(config, tmp_path):
    store.save_settings(request(tmp_path, paperless_token="tok-123456"))
    data = json.loads(config.read_text())
    data["paperless_token_enc"] = "plain:v1:!!!not-base64!!!"
    config.write_text(json.dumps(data))
    assert store.get_settings().paperless_token_set is False


@pytest.mark.parametrize(
    "url",
    [
        "http://paperless.example.com",
        "http://8.8.8.8:8000",
        "ftp://paperless.example",
        "https://user:pw@paperless.example",
        "https://paperless.example/?x=1",
        "javascript:alert(1)",
        "https://",
    ],
)
def test_unsafe_paperless_urls_are_rejected(url):
    with pytest.raises(store.SettingsError):
        store.validate_paperless_url(url)


@pytest.mark.parametrize(
    "url",
    ["https://paperless.example", "http://192.168.1.20:8000", "http://paperless:8000", "http://nas.local", "http://localhost:8000", ""],
)
def test_expected_paperless_urls_are_accepted(url):
    assert store.validate_paperless_url(url) == url


@pytest.mark.parametrize("path", ["relative/dir", "", "   ", "/etc/cron.d", "/usr/lib/x"])
def test_unsafe_output_dirs_are_rejected(path):
    with pytest.raises(store.SettingsError):
        store.validate_output_dir(path)


def test_absolute_output_dir_is_accepted(tmp_path):
    assert store.validate_output_dir(str(tmp_path)) == str(tmp_path)


def test_scan_refuses_manipulated_output_dir_in_config(config, tmp_path, monkeypatch):
    from unittest.mock import patch

    from app.scanner.scanner_types import DiscoveredScanner

    scanner = DiscoveredScanner(kind="twain", native_id="X", name="X")
    with (
        patch("app.main.registry.resolve", return_value=scanner),
        patch("app.settings.get_raw_settings", return_value={"scan_output_dir": "/etc/cron.d"}),
    ):
        response = make_client().post(
            "/scan", json={"scanner_id": "twain:X", "profile_id": "duplex_gray_300", "title": "t"}
        )
    assert response.status_code == 400


def test_secret_store_roundtrip_and_empty():
    assert secret_store.unprotect(secret_store.protect("äöü-token")) == "äöü-token"
    assert secret_store.protect("") == "" and secret_store.unprotect("") == ""
    with pytest.raises(secret_store.SecretStoreError):
        secret_store.unprotect("garbage")
