from __future__ import annotations

import httpx
import pytest

from app.models import ScanProfile
from app.scanner import escl_backend as escl
from app.scanner.scanner_types import ScanError

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 32
BASE = "http://192.168.1.50:80/eSCL"
CAPS_ADF_DUPLEX = b"""<?xml version="1.0"?>
<scan:ScannerCapabilities xmlns:scan="http://schemas.hp.com/imaging/escl/2011/05/03">
 <scan:Platen><scan:PlatenInputCaps/></scan:Platen>
 <scan:Adf><scan:AdfSimplexInputCaps/><scan:AdfDuplexInputCaps/></scan:Adf>
</scan:ScannerCapabilities>"""
CAPS_PLATEN_ONLY = CAPS_ADF_DUPLEX.replace(b"<scan:Adf><scan:AdfSimplexInputCaps/><scan:AdfDuplexInputCaps/></scan:Adf>", b"")
CAPS_ADF_SIMPLEX = CAPS_ADF_DUPLEX.replace(b"<scan:AdfDuplexInputCaps/>", b"")


def profile(**kw):
    values = dict(id="p", name="P", duplex=False, adf=True, dpi=300, color_mode="color")
    values.update(kw)
    return ScanProfile(**values)


class FakeScanner:
    def __init__(self, caps=CAPS_ADF_DUPLEX, pages=2, location="/eSCL/ScanJobs/42", busy_first=0, document=JPEG):
        self.caps, self.pages, self.location = caps, pages, location
        self.busy_first, self.document = busy_first, document
        self.posted, self.deleted, self.served = None, False, 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/ScannerCapabilities"):
            return httpx.Response(200, content=self.caps)
        if path.endswith("/ScanJobs") and request.method == "POST":
            self.posted = request.content.decode()
            return httpx.Response(201, headers={"Location": self.location})
        if path.endswith("/NextDocument"):
            if self.busy_first > 0:
                self.busy_first -= 1
                return httpx.Response(503)
            if self.served >= self.pages:
                return httpx.Response(404)
            self.served += 1
            return httpx.Response(200, content=self.document, headers={"Content-Type": "image/jpeg"})
        if request.method == "DELETE":
            self.deleted = True
            return httpx.Response(200)
        return httpx.Response(500)


def run(fake, prof, tmp_path, **kw):
    client = httpx.Client(transport=httpx.MockTransport(fake))
    return escl.scan_escl(BASE, prof, tmp_path, client=client, sleep=lambda _s: None, **kw)


def test_duplex_feeder_scan_downloads_all_pages_and_cleans_up(tmp_path):
    fake = FakeScanner(pages=3)
    pages = run(fake, profile(duplex=True), tmp_path)

    assert [p.name for p in pages] == ["page-0001.jpg", "page-0002.jpg", "page-0003.jpg"]
    assert pages[0].read_bytes() == JPEG
    assert "<pwg:InputSource>Feeder</pwg:InputSource>" in fake.posted
    assert "<scan:Duplex>true</scan:Duplex>" in fake.posted
    assert "<scan:ColorMode>RGB24</scan:ColorMode>" in fake.posted
    assert "<scan:XResolution>300</scan:XResolution>" in fake.posted
    assert fake.deleted is True


@pytest.mark.parametrize(("mode", "expected"), [("gray", "Grayscale8"), ("bw", "BlackAndWhite1")])
def test_color_mode_mapping(tmp_path, mode, expected):
    fake = FakeScanner(pages=1)
    run(fake, profile(color_mode=mode), tmp_path)
    assert f"<scan:ColorMode>{expected}</scan:ColorMode>" in fake.posted


def test_platen_only_device_falls_back_to_glass(tmp_path):
    fake = FakeScanner(caps=CAPS_PLATEN_ONLY, pages=1)
    run(fake, profile(), tmp_path)
    assert "<pwg:InputSource>Platen</pwg:InputSource>" in fake.posted
    assert "<scan:Duplex>false</scan:Duplex>" in fake.posted


def test_duplex_is_refused_if_device_cannot_do_it(tmp_path):
    with pytest.raises(ScanError, match="Duplex"):
        run(FakeScanner(caps=CAPS_ADF_SIMPLEX), profile(duplex=True), tmp_path)


def test_busy_scanner_is_retried(tmp_path):
    pages = run(FakeScanner(pages=1, busy_first=2), profile(), tmp_path)
    assert len(pages) == 1


def test_empty_feeder_is_reported(tmp_path):
    with pytest.raises(ScanError, match="keine Seiten"):
        run(FakeScanner(pages=0), profile(), tmp_path)


def test_job_location_pointing_to_foreign_host_is_refused(tmp_path):
    fake = FakeScanner(location="http://evil.example/steal")
    with pytest.raises(ScanError, match="fremdes Ziel"):
        run(fake, profile(), tmp_path)


def test_relative_job_location_is_resolved_on_same_device(tmp_path):
    assert len(run(FakeScanner(location="/eSCL/ScanJobs/7", pages=1), profile(), tmp_path)) == 1


def test_non_jpeg_payload_is_rejected(tmp_path):
    with pytest.raises(ScanError, match="JPEG"):
        run(FakeScanner(document=b"%PDF-1.4"), profile(), tmp_path)


def test_oversized_payload_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(escl, "MAX_PAGE_BYTES", 10)
    with pytest.raises(ScanError, match="große Daten"):
        run(FakeScanner(), profile(), tmp_path)


def test_unreachable_scanner_gives_clear_error(tmp_path):
    def refuse(_request):
        raise httpx.ConnectError("refused")

    with pytest.raises(ScanError, match="nicht erreichbar"):
        escl.scan_escl(BASE, profile(), tmp_path, client=httpx.Client(transport=httpx.MockTransport(refuse)))


def test_malicious_capabilities_xml_does_not_expand_entities(tmp_path):
    bomb = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;">]><x>&b;</x>'
    with pytest.raises(Exception):
        escl.parse_capabilities(bomb)


class Info:
    def __init__(self, addresses, port=80, props=None, name="HP Office._uscan._tcp.local."):
        self._addresses, self.port, self.properties, self.name = addresses, port, props or {}, name

    def parsed_addresses(self, _version=None):
        return self._addresses


def test_service_with_lan_address_becomes_scanner_with_stable_uuid_id():
    scanner = escl.scanner_from_service(
        Info(["192.168.1.50"], props={b"ty": b"HP Office Jet", b"rs": b"eSCL", b"uuid": b"1234-abcd"}), tls=False
    )
    assert scanner.id == "escl:1234-abcd"
    assert scanner.name == "HP Office Jet"
    assert scanner.extra["url"] == "http://192.168.1.50:80/eSCL"


def test_tls_service_uses_https():
    scanner = escl.scanner_from_service(Info(["10.0.0.5"], port=443), tls=True)
    assert scanner.extra["url"].startswith("https://10.0.0.5:443/")


def test_public_addresses_are_ignored():
    assert escl.scanner_from_service(Info(["8.8.8.8"]), tls=False) is None


def test_hostile_resource_path_falls_back_to_default():
    scanner = escl.scanner_from_service(
        Info(["192.168.1.5"], props={b"rs": b"../../admin?x=1", b"uuid": b"u"}), tls=False
    )
    assert scanner.extra["url"].endswith("/eSCL")


def test_missing_port_or_info_is_ignored():
    assert escl.scanner_from_service(None, tls=False) is None
    assert escl.scanner_from_service(Info(["192.168.1.5"], port=0), tls=False) is None
