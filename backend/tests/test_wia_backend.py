from __future__ import annotations

from pathlib import Path

import pytest

from app.models import ScanProfile
from app.scanner import wia_backend as wia
from app.scanner.scanner_types import DiscoveredScanner, ScanError


class ComError(Exception):
    def __init__(self, hresult):
        super().__init__(hresult, "COM")
        self.hresult = hresult


class Prop:
    def __init__(self, pid, value=0, maximum=None):
        self.PropertyID, self.Value, self.SubTypeMax = pid, value, maximum


class Props:
    def __init__(self, props):
        self.props = props

    @property
    def Count(self):
        return len(self.props)

    def Item(self, index):
        return self.props[index - 1]

    def __call__(self, name):
        return next(p for p in self.props if p.PropertyID == name or getattr(p, "name", None) == name)

    def get(self, pid):
        return next((p for p in self.props if p.PropertyID == pid), None)


class Image:
    def SaveFile(self, path):
        Path(path).write_bytes(b"BM")


class Item:
    def __init__(self, pages, error=None):
        self.Properties = Props([
            Prop(wia.IPA_DATATYPE), Prop(wia.IPA_DEPTH), Prop(wia.IPS_XRES), Prop(wia.IPS_YRES),
            Prop(wia.IPS_XEXTENT, 0, 2480), Prop(wia.IPS_YEXTENT, 0, 3508),
        ])
        self.pages, self.error, self.transfers = pages, error, 0

    def Transfer(self, fmt):
        assert fmt == wia.WIA_FORMAT_BMP
        self.transfers += 1
        if self.error and self.transfers > self.pages:
            raise self.error
        if self.transfers > self.pages:
            raise ComError(0x80210003 - (1 << 32))  # negativ wie bei pywin32
        return Image()


class Device:
    def __init__(self, item, with_handling=True):
        props = [Prop(wia.DPS_PAGES)]
        if with_handling:
            props.append(Prop(wia.DPS_DOCUMENT_HANDLING_SELECT))
        self.Properties = Props(props)
        self.item = item

    def Items(self, index):
        assert index == 1
        return self.item


class Info:
    def __init__(self, device_id, name, kind=1, device=None, connect_error=None):
        self.DeviceID, self.Type = device_id, kind
        self.Properties = lambda key: Prop(0, name)
        self._device, self._error = device, connect_error

    def Connect(self):
        if self._error:
            raise self._error
        return self._device


class Manager:
    def __init__(self, infos):
        self.DeviceInfos = Props(infos)
        self.DeviceInfos.Item = lambda i: infos[i - 1]


def backend_for(*infos):
    return wia.WiaBackend(dispatch=lambda prog_id: Manager(list(infos)), init_com=False)


def profile(**kw):
    values = dict(id="p", name="P", duplex=False, adf=True, dpi=300, color_mode="gray")
    values.update(kw)
    return ScanProfile(**values)


def test_discover_lists_only_scanners_with_ids():
    backend = backend_for(
        Info("{a}", "EPSON DS-410"),
        Info("{cam}", "Canon Kamera", kind=2),
        Info("{b}", "HP LaserJet MFP"),
    )
    found = backend.discover()
    assert [(s.id, s.name) for s in found] == [("wia:{a}", "EPSON DS-410"), ("wia:{b}", "HP LaserJet MFP")]


def test_feeder_scan_collects_all_pages_until_feeder_is_empty(tmp_path):
    item = Item(pages=3)
    device = Device(item)
    backend = backend_for(Info("{a}", "S", device=device))
    scanner = DiscoveredScanner(kind="wia", native_id="{a}", name="S")

    pages = backend.acquire(scanner, profile(duplex=True), tmp_path)

    assert [p.name for p in pages] == ["page-0001.bmp", "page-0002.bmp", "page-0003.bmp"]
    handling = device.Properties.get(wia.DPS_DOCUMENT_HANDLING_SELECT).Value
    assert handling == wia.HANDLING_FEEDER | wia.HANDLING_DUPLEX
    assert device.Properties.get(wia.DPS_PAGES).Value == 0
    props = item.Properties
    assert (props.get(wia.IPA_DATATYPE).Value, props.get(wia.IPA_DEPTH).Value) == (1, 8)
    assert props.get(wia.IPS_XRES).Value == props.get(wia.IPS_YRES).Value == 300
    assert (props.get(wia.IPS_XEXTENT).Value, props.get(wia.IPS_YEXTENT).Value) == (2480, 3508)


def test_flatbed_scan_takes_exactly_one_page(tmp_path):
    item = Item(pages=5)
    device = Device(item)
    backend = backend_for(Info("{a}", "S", device=device))
    scanner = DiscoveredScanner(kind="wia", native_id="{a}", name="S")

    pages = backend.acquire(scanner, profile(adf=False), tmp_path)

    assert len(pages) == 1 and item.transfers == 1
    assert device.Properties.get(wia.DPS_DOCUMENT_HANDLING_SELECT).Value == wia.HANDLING_FLATBED


@pytest.mark.parametrize(("mode", "expected"), [("color", (2, 24)), ("gray", (1, 8)), ("bw", (0, 1))])
def test_color_modes_map_to_wia_datatype_and_depth(tmp_path, mode, expected):
    item = Item(pages=1)
    backend = backend_for(Info("{a}", "S", device=Device(item)))
    backend.acquire(DiscoveredScanner(kind="wia", native_id="{a}", name="S"), profile(color_mode=mode), tmp_path)
    assert (item.Properties.get(wia.IPA_DATATYPE).Value, item.Properties.get(wia.IPA_DEPTH).Value) == expected


def test_empty_feeder_gives_clear_error(tmp_path):
    backend = backend_for(Info("{a}", "S", device=Device(Item(pages=0))))
    with pytest.raises(ScanError, match="Kein Papier"):
        backend.acquire(DiscoveredScanner(kind="wia", native_id="{a}", name="S"), profile(), tmp_path)


def test_paper_jam_is_reported_in_german(tmp_path):
    item = Item(pages=1, error=ComError(0x80210002))
    backend = backend_for(Info("{a}", "S", device=Device(item)))
    with pytest.raises(ScanError, match="Papierstau"):
        backend.acquire(DiscoveredScanner(kind="wia", native_id="{a}", name="S"), profile(), tmp_path)


def test_duplex_is_not_silently_dropped_when_device_cannot_do_it(tmp_path):
    backend = backend_for(Info("{a}", "S", device=Device(Item(pages=1), with_handling=False)))
    with pytest.raises(ScanError, match="Duplex"):
        backend.acquire(DiscoveredScanner(kind="wia", native_id="{a}", name="S"), profile(duplex=True), tmp_path)


def test_duplex_without_feeder_is_rejected(tmp_path):
    backend = backend_for(Info("{a}", "S", device=Device(Item(pages=1))))
    with pytest.raises(ScanError, match="Dokumenteneinzug"):
        backend.acquire(DiscoveredScanner(kind="wia", native_id="{a}", name="S"), profile(adf=False, duplex=True), tmp_path)


def test_unplugged_scanner_gives_clear_error(tmp_path):
    backend = backend_for(Info("{other}", "S", device=Device(Item(pages=1))))
    with pytest.raises(ScanError, match="nicht mehr verbunden"):
        backend.acquire(DiscoveredScanner(kind="wia", native_id="{a}", name="S"), profile(), tmp_path)


def test_connect_failure_is_translated(tmp_path):
    backend = backend_for(Info("{a}", "S", connect_error=ComError(0x8021000D)))
    with pytest.raises(ScanError, match="anderen Programm"):
        backend.acquire(DiscoveredScanner(kind="wia", native_id="{a}", name="S"), profile(), tmp_path)


def test_backend_is_unavailable_off_windows_without_injected_com():
    assert wia.WiaBackend().available() is False
