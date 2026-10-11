"""Feste Scan-Profile."""

from __future__ import annotations

from ..models import ScanProfile

DEFAULT_PROFILES: list[ScanProfile] = [
    ScanProfile(
        id="duplex_gray_300",
        name="Duplex Grau 300 DPI",
        duplex=True,
        adf=True,
        dpi=300,
        color_mode="gray",
    ),
    ScanProfile(
        id="simplex_color_300",
        name="Simplex Farbe 300 DPI",
        duplex=False,
        adf=True,
        dpi=300,
        color_mode="color",
    ),
]


def get_profiles() -> list[ScanProfile]:
    return list(DEFAULT_PROFILES)


def find_profile(profile_id: str) -> ScanProfile | None:
    return next((p for p in DEFAULT_PROFILES if p.id == profile_id), None)
