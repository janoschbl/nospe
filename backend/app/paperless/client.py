"""Paperless-ngx Client für Verbindungsprüfung und PDF-Upload."""

from __future__ import annotations

import httpx

from ..models import PaperlessTestResponse


def _api_url(url: str, path: str) -> str:
    return f"{url.rstrip('/')}/api/{path.lstrip('/')}"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Token {token}"}


def test_connection(url: str, token: str) -> PaperlessTestResponse:
    """Prüft URL und Token gegen den geschützten Dokument-Endpunkt."""
    if not url.strip():
        return PaperlessTestResponse(
            ok=False, message="Keine Paperless-URL gesetzt."
        )
    if not token.strip():
        return PaperlessTestResponse(
            ok=False, message="Kein Paperless-Token gesetzt."
        )
    if not (url.startswith("http://") or url.startswith("https://")):
        return PaperlessTestResponse(
            ok=False,
            message="Paperless-URL muss mit http:// oder https:// beginnen.",
        )
    try:
        response = httpx.get(
            _api_url(url, "documents/?page_size=1"),
            headers=_headers(token),
            timeout=8.0,
        )
    except httpx.RequestError:
        return PaperlessTestResponse(
            ok=False,
            message="Paperless-Server ist nicht erreichbar oder die URL ist ungültig.",
        )
    if response.status_code in (401, 403):
        return PaperlessTestResponse(ok=False, message="Paperless-Token ist ungültig.")
    if not response.is_success:
        return PaperlessTestResponse(
            ok=False,
            message=f"Paperless antwortet mit HTTP {response.status_code}.",
        )
    return PaperlessTestResponse(ok=True, message="Mit Paperless verbunden.")


def upload_document(
    *, url: str, token: str, file_path: str, title: str
) -> str:
    """Lädt die PDF hoch; ein Uploadfehler lässt den lokalen Scan bestehen."""
    if not url.strip() or not token.strip():
        raise RuntimeError("Paperless nicht konfiguriert (URL/Token fehlt).")
    with open(file_path, "rb") as document:
        response = httpx.post(
            _api_url(url, "documents/post_document/"),
            headers=_headers(token),
            data={"title": title},
            files={"document": ("scan.pdf", document, "application/pdf")},
            timeout=60.0,
        )
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Paperless-Antwort ist kein gültiges JSON.") from exc
    if isinstance(payload, dict):
        task_id = payload.get("task")
    elif isinstance(payload, str):
        task_id = payload
    else:
        raise RuntimeError("Paperless lieferte eine unerwartete Upload-Antwort.")
    if task_id is None or (isinstance(task_id, str) and not task_id.strip()):
        raise RuntimeError("Paperless lieferte keine Upload-Task-ID.")
    if not isinstance(task_id, str):
        raise RuntimeError("Paperless lieferte eine ungültige Upload-Task-ID.")
    return task_id
