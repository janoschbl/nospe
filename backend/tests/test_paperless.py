from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.paperless import client


def test_connection_checks_paperless_with_token_header():
    response = MagicMock(status_code=200)
    response.raise_for_status.return_value = None

    with patch("app.paperless.client.httpx.get", return_value=response) as get:
        result = client.test_connection("http://paperless.local:8000/", "secret-token")

    assert result.ok is True
    assert "verbunden" in result.message.lower()
    get.assert_called_once_with(
        "http://paperless.local:8000/api/documents/?page_size=1",
        headers={"Authorization": "Token secret-token"},
        timeout=8.0,
    )


def test_connection_reports_invalid_paperless_token():
    response = MagicMock(status_code=401)

    with patch("app.paperless.client.httpx.get", return_value=response):
        result = client.test_connection("http://paperless.local:8000", "secret-token")

    assert result.ok is False
    assert "Token" in result.message


def test_upload_accepts_uuid_task_id(tmp_path):
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    response = MagicMock()
    response.json.return_value = "cf13c75d-9d9a-4b73-b1e1-31fc8e7b2d54"

    with patch("app.paperless.client.httpx.post", return_value=response):
        task_id = client.upload_document(
            url="http://paperless.local:8000",
            token="secret-token",
            file_path=str(pdf),
            title="Test",
        )

    assert task_id == "cf13c75d-9d9a-4b73-b1e1-31fc8e7b2d54"


def test_upload_accepts_object_uuid_task_id(tmp_path):
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    response = MagicMock()
    response.json.return_value = {"task": "cf13c75d-9d9a-4b73-b1e1-31fc8e7b2d54"}

    with patch("app.paperless.client.httpx.post", return_value=response):
        task_id = client.upload_document(
            url="http://paperless.local:8000",
            token="secret-token",
            file_path=str(pdf),
            title="Test",
        )

    assert task_id == "cf13c75d-9d9a-4b73-b1e1-31fc8e7b2d54"
