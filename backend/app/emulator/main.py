from __future__ import annotations

from fastapi import FastAPI
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app import __version__
from app.emulator.routes import router

EMULATOR_PORT = 8766
_ALLOWED_HOSTS = {f"127.0.0.1:{EMULATOR_PORT}", f"localhost:{EMULATOR_PORT}"}


class SameOriginMiddleware:
    """Schützt den Entwicklungs-Emulator vor Webseiten (CSRF/DNS-Rebinding).

    Der Host muss Loopback sein; Anfragen mit ``Origin`` müssen von der
    Emulator-Seite selbst stammen. Ein Browser setzt ``Origin`` bei jedem
    Cross-Site-POST, ein fremdes Formular kann also keine PDFs mehr einspielen.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
            host = headers.get("host", "").lower()
            origin = headers.get("origin")
            if host not in _ALLOWED_HOSTS or (origin is not None and origin != f"http://{host}"):
                await JSONResponse({"detail": "Nicht erlaubt."}, status_code=403)(scope, receive, send)
                return
        await self.app(scope, receive, send)


app = FastAPI(
    title="Nospe TWAIN PDF Emulator",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(SameOriginMiddleware)
app.include_router(router)
