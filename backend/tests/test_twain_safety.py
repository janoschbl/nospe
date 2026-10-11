from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models import ScanProfile
from app.scanner import twain_env, twain_scan, twain_sources
from app.scanner.scanner_types import ScanError
from app.scanner.twain_lock import TWAIN_LOCK, TwainBusy, twain_session

PROFILE = ScanProfile(id="p", name="P", duplex=False, adf=False, dpi=300, color_mode="gray")
READY = twain_env.TwainEnvironment(platform="Windows", python_bitness=64, twain_supported=True, dsm_available=True)


@pytest.fixture(autouse=True)
def _reset_probe_cache():
    twain_env.reset_probe_cache()
    yield
    twain_env.reset_probe_cache()


def hold_lock_in_thread():
    acquired, release = threading.Event(), threading.Event()

    def worker():
        with twain_session():
            acquired.set()
            release.wait(5)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    assert acquired.wait(2)
    return release, thread


def test_nonblocking_listing_reports_busy_during_scan():
    release, thread = hold_lock_in_thread()
    try:
        with patch.object(twain_sources, "probe_twain_environment", side_effect=TwainBusy):
            with pytest.raises(TwainBusy):
                twain_sources.list_twain_product_names(blocking=False)
    finally:
        release.set()
        thread.join()


def test_probe_does_not_touch_dsm_while_scan_holds_lock():
    release, thread = hold_lock_in_thread()
    try:
        with pytest.raises(TwainBusy):
            twain_env.probe_twain_environment(blocking=False)
    finally:
        release.set()
        thread.join()


def test_successful_probe_is_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(twain_env, "_probe_uncached", lambda: calls.append(1) or READY)
    twain_env.probe_twain_environment()
    twain_env.probe_twain_environment()
    assert len(calls) == 1


def test_failed_probe_is_retried(monkeypatch):
    blocked = twain_env.TwainEnvironment(
        platform="Windows", python_bitness=64, twain_supported=True, dsm_available=False, error="x"
    )
    calls = []
    monkeypatch.setattr(twain_env, "_probe_uncached", lambda: calls.append(1) or blocked)
    twain_env.probe_twain_environment()
    twain_env.probe_twain_environment()
    assert len(calls) == 2


def test_scan_holds_twain_lock_for_whole_acquisition(tmp_path, monkeypatch):
    seen = {}
    sm = MagicMock()
    sm.__enter__.return_value = sm
    source = MagicMock()
    sm.open_source.return_value = source

    def acquire(**_kwargs):
        # Ein anderer Thread darf den DSM jetzt nicht bekommen.
        result = []
        t = threading.Thread(target=lambda: result.append(TWAIN_LOCK.acquire(blocking=False)))
        t.start(); t.join()
        seen["other_thread_got_lock"] = result[0]
        if result[0]:
            TWAIN_LOCK.release()

    source.acquire_natively.side_effect = acquire
    monkeypatch.setattr(twain_scan, "_apply_profile", lambda *a, **k: None)
    with patch("twain.SourceManager", return_value=sm), pytest.raises(ScanError, match="keine Seiten"):
        twain_scan._acquire_images("X", PROFILE, tmp_path)
    assert seen["other_thread_got_lock"] is False


def test_temp_pages_are_removed_when_scan_fails_midway(tmp_path, monkeypatch):
    monkeypatch.setattr(twain_scan.tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(twain_scan, "probe_twain_environment", lambda: READY)

    def failing_acquire(_name, _profile, workdir, **_kw):
        (workdir / "page-0001.bmp").write_bytes(b"BM vertraulich")
        raise RuntimeError("Papierstau")

    monkeypatch.setattr(twain_scan, "_acquire_images", failing_acquire)

    with pytest.raises(RuntimeError, match="Papierstau"):
        twain_scan._scan_via_twain("X", PROFILE, tmp_path / "out.pdf")

    assert list(tmp_path.glob("nospe-scan-*")) == []


def test_temp_pages_are_removed_after_success(tmp_path, monkeypatch):
    from PIL import Image

    monkeypatch.setattr(twain_scan.tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(twain_scan, "probe_twain_environment", lambda: READY)

    def acquire(_name, _profile, workdir, **_kw):
        page = workdir / "page-0001.bmp"
        Image.new("L", (10, 10)).save(page)
        return [page]

    monkeypatch.setattr(twain_scan, "_acquire_images", acquire)
    out = tmp_path / "out.pdf"
    twain_scan._scan_via_twain("X", PROFILE, out)
    assert out.exists()
    assert list(tmp_path.glob("nospe-scan-*")) == []


def test_partial_pdf_is_removed_when_pdf_build_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(twain_scan.tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(twain_scan, "probe_twain_environment", lambda: READY)
    monkeypatch.setattr(twain_scan, "_acquire_images", lambda *a, **k: [tmp_path / "missing.bmp"])
    out = tmp_path / "out.pdf"
    out.write_bytes(b"partial")
    with pytest.raises(Exception):
        twain_scan._scan_via_twain("X", PROFILE, out)
    assert not out.exists()


def test_sweep_removes_only_old_scan_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(twain_scan.tempfile, "tempdir", str(tmp_path))
    old, fresh, other = tmp_path / "nospe-scan-old", tmp_path / "nospe-scan-new", tmp_path / "unrelated"
    for d in (old, fresh, other):
        d.mkdir()
        (d / "page.bmp").write_bytes(b"x")
    past = time.time() - 7200
    os.utime(old, (past, past))
    os.utime(other, (past, past))

    assert twain_scan.sweep_stale_scan_dirs(3600) == 1
    assert not old.exists() and fresh.exists() and other.exists()


@pytest.mark.parametrize("title", ["CON", "nul", "COM1", "lpt3.txt", "con.pdf"])
def test_reserved_windows_device_names_are_not_used(title):
    name = twain_scan._sanitize_title(title)
    assert name.split(".")[0].casefold() not in twain_scan._RESERVED_NAMES


@pytest.mark.parametrize("title", ["../../Windows/evil", "a/b\\c", "..", ""])
def test_titles_cannot_escape_output_dir(tmp_path, title):
    path = twain_scan.resolve_output_path(tmp_path, title)
    assert path.parent == tmp_path


def test_overlong_titles_are_truncated(tmp_path):
    assert len(twain_scan.resolve_output_path(tmp_path, "x" * 500).name) < 140
