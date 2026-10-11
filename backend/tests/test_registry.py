from __future__ import annotations

import pytest

from app.scanner.registry import ScannerRegistry, merge_duplicates
from app.scanner.scanner_types import BackendBusy, DiscoveredScanner


def scanner(kind, native_id, name):
    return DiscoveredScanner(kind=kind, native_id=native_id, name=name)


class FakeBackend:
    def __init__(self, kind, results=None, interval=0.0, error=None):
        self.kind, self.interval = kind, interval
        self.results = results or []
        self.error = error
        self.calls = 0
        self.started = self.stopped = False

    def discover(self):
        self.calls += 1
        if self.error:
            raise self.error
        return list(self.results)

    def acquire(self, *_a):
        return []

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def test_same_device_via_twain_and_wia_is_shown_once_with_twain_preferred():
    merged = merge_duplicates([
        scanner("wia", "{wia-id}", "EPSON DS-410"),
        scanner("twain", "EPSON DS-410", "EPSON DS-410"),
    ])
    assert [(s.kind, s.name) for s in merged] == [("twain", "EPSON DS-410")]
    assert merged[0].also_via == ("wia:{wia-id}",)


def test_series_suffix_and_vendor_prefix_do_not_prevent_merge():
    merged = merge_duplicates([
        scanner("twain", "EPSON DS-410", "EPSON DS-410"),
        scanner("wia", "{x}", "DS-410 Series"),
        scanner("escl", "uuid", "EPSON DS-410 Series"),
    ])
    assert len(merged) == 1 and len(merged[0].also_via) == 2


def test_different_devices_are_not_merged():
    merged = merge_duplicates([
        scanner("twain", "EPSON DS-410", "EPSON DS-410"),
        scanner("wia", "{x}", "Brother MFC-L2710"),
    ])
    assert len(merged) == 2


def test_two_identical_twain_sources_are_not_collapsed():
    merged = merge_duplicates([scanner("twain", "A DS-410", "A DS-410"), scanner("twain", "B DS-410", "B DS-410")])
    assert len(merged) == 2


def test_short_or_generic_names_are_not_merged():
    merged = merge_duplicates([scanner("twain", "Scan", "Scan"), scanner("wia", "{x}", "Scanner")])
    assert len(merged) == 2


def test_snapshot_combines_backends_and_orders_by_kind():
    registry = ScannerRegistry([
        FakeBackend("escl", [scanner("escl", "u", "HP Office")]),
        FakeBackend("twain", [scanner("twain", "Zeta", "Zeta")]),
    ])
    registry.refresh()
    assert [s.kind for s in registry.snapshot().scanners] == ["twain", "escl"]


def test_failing_backend_is_isolated_and_reported():
    registry = ScannerRegistry([
        FakeBackend("twain", error=RuntimeError("DSM fehlt")),
        FakeBackend("wia", [scanner("wia", "{x}", "Canon LiDE 400")]),
    ])
    registry.refresh()
    snapshot = registry.snapshot()
    assert [s.name for s in snapshot.scanners] == ["Canon LiDE 400"]
    assert snapshot.errors == {"twain": "DSM fehlt"}


def test_busy_backend_keeps_previous_result():
    backend = FakeBackend("twain", [scanner("twain", "A", "A")])
    registry = ScannerRegistry([backend])
    registry.refresh(force=True)
    backend.error = BackendBusy("scan")
    registry.refresh(force=True)
    snapshot = registry.snapshot()
    assert [s.name for s in snapshot.scanners] == ["A"] and snapshot.errors == {}


def test_unplugged_device_disappears_on_next_refresh():
    backend = FakeBackend("wia", [scanner("wia", "{x}", "Canon LiDE 400")])
    registry = ScannerRegistry([backend])
    registry.refresh(force=True)
    backend.results = []
    registry.refresh(force=True)
    assert registry.snapshot().scanners == []


def test_nothing_is_queried_while_a_scan_runs():
    backend = FakeBackend("wia", [scanner("wia", "{x}", "Canon")])
    registry = ScannerRegistry([backend], scan_active=lambda: True)
    registry.refresh(force=True)
    assert backend.calls == 0
    assert registry.snapshot().scanning is True


def test_interval_is_respected_for_polling_backends():
    now = [100.0]
    backend = FakeBackend("twain", [scanner("twain", "A", "A")], interval=30.0)
    registry = ScannerRegistry([backend], clock=lambda: now[0])
    registry.refresh(); registry.refresh()
    assert backend.calls == 1
    now[0] += 31
    registry.refresh()
    assert backend.calls == 2


def test_event_driven_backends_are_read_on_every_refresh():
    backend = FakeBackend("escl", interval=0.0)
    registry = ScannerRegistry([backend])
    registry.refresh(); registry.refresh()
    assert backend.calls == 2


def test_unavailable_backends_are_skipped():
    class Unavailable(FakeBackend):
        def available(self):
            return False

    backend = Unavailable("wia", [scanner("wia", "{x}", "X")])
    registry = ScannerRegistry([backend])
    registry.refresh(force=True)
    assert backend.calls == 0 and registry.snapshot().scanners == []


@pytest.mark.parametrize("stored", ["EPSON DS-410", "twain:EPSON DS-410"])
def test_legacy_bare_names_resolve_as_twain(stored):
    registry = ScannerRegistry([FakeBackend("twain", [scanner("twain", "EPSON DS-410", "EPSON DS-410")])])
    registry.refresh()
    assert registry.resolve(stored).native_id == "EPSON DS-410"


def test_resolve_unknown_returns_none_and_never_invents_devices():
    registry = ScannerRegistry([FakeBackend("escl", [scanner("escl", "u", "HP")])])
    registry.refresh()
    assert registry.resolve("escl:http://evil.example/eSCL") is None
    assert registry.resolve("wia:{unknown}") is None


def test_start_and_stop_manage_backends():
    backend = FakeBackend("escl")
    registry = ScannerRegistry([backend])
    registry.start(tick=0.01)
    registry.stop()
    assert backend.started and backend.stopped
