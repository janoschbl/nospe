from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

EmulatorJobStatus = Literal["ready", "transferring", "consumed"]


class EmulatorPage(BaseModel):
    index: int
    path: str
    width_px: int
    height_px: int


class EmulatorJob(BaseModel):
    active: Literal[True] = True
    job_id: str
    status: EmulatorJobStatus
    original_pdf: str
    page_count: int
    dpi: int
    color_mode: Literal["color"] = "color"
    pages: list[EmulatorPage]
    created_at: str


class EmulatorInactiveJob(BaseModel):
    active: Literal[False] = False


EmulatorJobResponse = EmulatorJob | EmulatorInactiveJob
