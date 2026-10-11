from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.emulator.main import app


PDF_BYTES = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] /Resources << >> /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 0 >>
stream

endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000216 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
265
%%EOF
"""


def client_with_spool(monkeypatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("NOSPE_EMULATOR_SPOOL_DIR", str(tmp_path / "spool"))
    return TestClient(app)


def test_pdf_upload_creates_active_job_manifest_and_page(monkeypatch, tmp_path):
    client = client_with_spool(monkeypatch, tmp_path)

    response = client.post(
        "/emulator/upload",
        files={"file": ("sample.pdf", PDF_BYTES, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["active"] is True
    assert body["page_count"] == 1
    assert body["dpi"] == 300
    assert body["color_mode"] == "color"
    assert body["status"] == "ready"

    manifest_path = tmp_path / "spool" / "active" / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["job_id"] == body["job_id"]
    assert Path(manifest["original_pdf"]).exists()
    assert len(manifest["pages"]) == 1
    assert Path(manifest["pages"][0]["path"]).exists()
    with Image.open(manifest["pages"][0]["path"]) as page:
        assert page.mode == "RGB"


def test_job_status_and_consume_lifecycle(monkeypatch, tmp_path):
    client = client_with_spool(monkeypatch, tmp_path)
    upload = client.post(
        "/emulator/upload",
        files={"file": ("sample.pdf", PDF_BYTES, "application/pdf")},
    )
    assert upload.status_code == 200

    status = client.get("/emulator/job")
    assert status.status_code == 200
    assert status.json()["active"] is True

    consume = client.post("/emulator/job/consume")
    assert consume.status_code == 200
    assert consume.json() == {"active": False}
    assert client.get("/emulator/job").json() == {"active": False}


def test_upload_rejects_non_pdf_and_empty_pdf(monkeypatch, tmp_path):
    client = client_with_spool(monkeypatch, tmp_path)

    text_response = client.post(
        "/emulator/upload",
        files={"file": ("sample.txt", b"hello", "text/plain")},
    )
    assert text_response.status_code == 400

    empty_response = client.post(
        "/emulator/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert empty_response.status_code == 400


def test_upload_rejects_file_larger_than_configured_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("NOSPE_EMULATOR_MAX_BYTES", "3")
    client = client_with_spool(monkeypatch, tmp_path)

    response = client.post(
        "/emulator/upload",
        files={"file": ("sample.pdf", PDF_BYTES, "application/pdf")},
    )

    assert response.status_code == 413


def test_upload_rejects_when_job_is_transferring(monkeypatch, tmp_path):
    client = client_with_spool(monkeypatch, tmp_path)
    upload = client.post(
        "/emulator/upload",
        files={"file": ("sample.pdf", PDF_BYTES, "application/pdf")},
    )
    assert upload.status_code == 200

    manifest_path = tmp_path / "spool" / "active" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "transferring"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    blocked = client.post(
        "/emulator/upload",
        files={"file": ("replacement.pdf", PDF_BYTES, "application/pdf")},
    )
    assert blocked.status_code == 409


def test_emulator_page_is_minimal_upload_surface(monkeypatch, tmp_path):
    client = client_with_spool(monkeypatch, tmp_path)

    response = client.get("/emulator")

    assert response.status_code == 200
    html = response.text
    assert 'type="file"' in html
    assert 'accept="application/pdf,.pdf"' in html
    assert "dragover" in html
    assert "drop" in html
    assert "/emulator/upload" in html
