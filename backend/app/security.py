"""Absicherung der lokalen API.

Das Backend lauscht nur auf Loopback, aber Loopback ist keine Vertrauensgrenze:
jede Webseite im Browser und jeder andere Prozess (auch anderer Benutzer auf
Terminalservern) kann Requests dorthin schicken. Deshalb gilt:

* Jede Anfrage braucht den Header ``X-Nospe-Token`` mit dem pro Start zufällig
  erzeugten Secret (Konstantzeit-Vergleich). Der Header erzwingt außerdem einen
  CORS-Preflight, den fremde Origins nicht bestehen.
* Der ``Host``-Header muss ``127.0.0.1``/``localhost`` mit dem echten Port sein.
  Das stoppt DNS-Rebinding, bei dem der Browser die API als „same origin“ sieht.
* Ein vorhandener ``Origin``-Header muss auf der Allowlist stehen.
"""

from __future__ import annotations

import hmac
import os
import secrets
from dataclasses import dataclass, field

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

TOKEN_HEADER = "x-nospe-token"
TOKEN_HEADER_CANONICAL = "X-Nospe-Token"

RELEASE_ORIGINS = (
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
)
DEV_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


@dataclass
class SecurityConfig:
    secret: str = ""
    port: int = 0
    dev: bool = False
    extra_hosts: frozenset[str] = field(default_factory=frozenset)

    def allowed_hosts(self) -> set[str]:
        hosts = {f"127.0.0.1:{self.port}", f"localhost:{self.port}", f"[::1]:{self.port}"}
        return hosts | set(self.extra_hosts)

    def allowed_origins(self) -> list[str]:
        origins = list(RELEASE_ORIGINS)
        if self.dev:
            origins.extend(DEV_ORIGINS)
        return origins


_config = SecurityConfig()


def configure(*, secret: str, port: int, dev: bool = False) -> SecurityConfig:
    """Setzt die Laufzeit-Konfiguration (einmal beim Start, in Tests pro Test)."""
    global _config
    if len(secret) < 16:
        raise ValueError("API-Secret ist zu kurz (mindestens 16 Zeichen).")
    _config = SecurityConfig(secret=secret, port=port, dev=dev)
    return _config


def get_config() -> SecurityConfig:
    return _config


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def dev_mode_enabled() -> bool:
    return os.environ.get("NOSPE_DEV", "").strip().lower() in {"1", "true", "yes"}


def _deny(status: int, message: str) -> JSONResponse:
    return JSONResponse({"detail": message}, status_code=status)


class SecurityMiddleware:
    """Reines ASGI-Middleware, schlägt geschlossen fehl (kein Secret → alles 503)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            # WebSockets o. Ä. gibt es nicht; unbekannte Scopes nie durchlassen.
            if scope["type"] == "lifespan":
                await self.app(scope, receive, send)
            return

        config = get_config()
        if not config.secret:
            await _deny(503, "API nicht konfiguriert.")(scope, receive, send)
            return

        headers = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope["headers"]}

        if headers.get("host", "").lower() not in config.allowed_hosts():
            await _deny(403, "Ungültiger Host.")(scope, receive, send)
            return

        origin = headers.get("origin")
        if origin is not None and origin not in config.allowed_origins():
            await _deny(403, "Ungültiger Origin.")(scope, receive, send)
            return

        if scope["method"] != "OPTIONS":
            supplied = headers.get(TOKEN_HEADER, "")
            if not hmac.compare_digest(supplied.encode(), config.secret.encode()):
                await _deny(401, "Nicht autorisiert.")(scope, receive, send)
                return

        await self.app(scope, receive, send)
