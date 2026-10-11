from __future__ import annotations

from fastapi import FastAPI

from app import __version__
from app.emulator.routes import router

app = FastAPI(title="Nospe TWAIN PDF Emulator", version=__version__)
app.include_router(router)
