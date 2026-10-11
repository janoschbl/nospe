"""eSCL/AirScan-Backend für Netzwerkscanner (mDNS ``_uscan._tcp``).

Fast alle Netzwerkscanner und Multifunktionsgeräte der letzten Jahre sprechen
eSCL (Apple AirScan / Mopria Scan). Sie melden sich per mDNS und brauchen unter
Windows keinen Treiber. Entdeckt werden ausschließlich Geräte im lokalen Netz;
gescannt wird nur gegen Geräte, die die Registry selbst gefunden hat, nie gegen
eine vom Client gelieferte URL.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

import httpx
from defusedxml import ElementTree

from ..models import ScanProfile
from .scanner_types import DiscoveredScanner, ScanError

logger = logging.getLogger(__name__)

SERVICE_TYPES = ("_uscan._tcp.local.", "_uscans._tcp.local.")
MAX_CAPABILITIES_BYTES = 1_000_000
MAX_PAGE_BYTES = 200 * 1024 * 1024
MAX_PAGES = 500
BUSY_RETRY_SECONDS = 60.0

_COLOR_MODES = {"color": "RGB24", "gray": "Grayscale8", "bw": "BlackAndWhite1"}
_SAFE_RESOURCE = re.compile(r"^[A-Za-z0-9._~\-]+(/[A-Za-z0-9._~\-]+)*$")
_NS = (
    'xmlns:pwg="http://www.pwg.org/schemas/2010/12/sm" '
    'xmlns:scan="http://schemas.hp.com/imaging/escl/2011/05/03"'
)


def _is_local_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return ip.is_private or ip.is_link_local or ip.is_loopback


def _safe_resource(value: str | None) -> str:
    resource = (value or "eSCL").strip("/")
    if not _SAFE_RESOURCE.match(resource) or ".." in resource.split("/"):
        return "eSCL"
    return resource


def build_scan_settings(profile: ScanProfile, *, feeder: bool) -> str:
    duplex = "true" if (feeder and profile.duplex) else "false"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<scan:ScanSettings {_NS}>"
        "<pwg:Version>2.0</pwg:Version>"
        f"<pwg:InputSource>{'Feeder' if feeder else 'Platen'}</pwg:InputSource>"
        f"<scan:ColorMode>{_COLOR_MODES[profile.color_mode]}</scan:ColorMode>"
        f"<scan:XResolution>{int(profile.dpi)}</scan:XResolution>"
        f"<scan:YResolution>{int(profile.dpi)}</scan:YResolution>"
        "<pwg:DocumentFormat>image/jpeg</pwg:DocumentFormat>"
        f"<scan:Duplex>{duplex}</scan:Duplex>"
        "</scan:ScanSettings>"
    )


def parse_capabilities(xml: bytes) -> dict[str, bool]:
    """Liest nur, ob Einzug und Duplex vorhanden sind."""
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise ScanError("Der Netzwerkscanner lieferte unlesbare Fähigkeiten.") from exc
    tags = {element.tag.rsplit("}", 1)[-1] for element in root.iter()}
    return {"adf": "Adf" in tags, "duplex": "AdfDuplexInputCaps" in tags, "platen": "Platen" in tags}


def _read_limited(response: httpx.Response, limit: int) -> bytes:
    data = bytearray()
    for chunk in response.iter_bytes():
        data.extend(chunk)
        if len(data) > limit:
            raise ScanError("Der Scanner lieferte unerwartet große Daten.")
    return bytes(data)


def scan_escl(
    base_url: str,
    profile: ScanProfile,
    workdir: Path,
    *,
    verify_tls: bool = False,
    client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[Path]:
    """Führt einen eSCL-Scan aus und gibt die Seitenbilder (JPEG) zurück."""
    own_client = client is None
    http = client or httpx.Client(verify=verify_tls, follow_redirects=False, timeout=httpx.Timeout(120.0, connect=5.0))
    base = base_url.rstrip("/")
    job_url: str | None = None
    try:
        try:
            with http.stream("GET", f"{base}/ScannerCapabilities") as response:
                if response.status_code != 200:
                    raise ScanError(f"Netzwerkscanner antwortet mit HTTP {response.status_code}.")
                capabilities = parse_capabilities(_read_limited(response, MAX_CAPABILITIES_BYTES))

            feeder = profile.adf and capabilities["adf"]
            if profile.adf and not capabilities["adf"]:
                if capabilities["platen"]:
                    feeder = False  # Gerät hat nur Vorlagenglas → Vorlagenglas verwenden
                else:
                    raise ScanError("Der Netzwerkscanner hat keinen Dokumenteneinzug.")
            if profile.duplex and feeder and not capabilities["duplex"]:
                raise ScanError("Der Netzwerkscanner unterstützt keinen Duplex-Scan.")

            created = http.post(
                f"{base}/ScanJobs",
                content=build_scan_settings(profile, feeder=feeder),
                headers={"Content-Type": "text/xml"},
            )
            if created.status_code != 201 or "location" not in created.headers:
                raise ScanError(f"Netzwerkscanner lehnt den Scan ab (HTTP {created.status_code}).")
            job_url = _validated_job_url(base, created.headers["location"])

            return _download_pages(http, job_url, workdir, sleep)
        except httpx.HTTPError as exc:
            raise ScanError(f"Netzwerkscanner nicht erreichbar: {exc}") from exc
    finally:
        if job_url:
            try:
                http.delete(job_url, timeout=5.0)
            except httpx.HTTPError:
                pass
        if own_client:
            http.close()


def _validated_job_url(base: str, location: str) -> str:
    """Der Job muss auf demselben Gerät liegen (kein Umleiten auf fremde Hosts)."""
    base_parts = urlsplit(base)
    job = urlsplit(location)
    if not job.scheme:  # relative Location
        job = urlsplit(f"{base_parts.scheme}://{base_parts.netloc}{location}")
    if (job.scheme, job.netloc) != (base_parts.scheme, base_parts.netloc):
        raise ScanError("Der Scanner verweist auf ein fremdes Ziel und wird ignoriert.")
    return job.geturl().rstrip("/")


def _download_pages(http: httpx.Client, job_url: str, workdir: Path, sleep: Callable[[float], None]) -> list[Path]:
    pages: list[Path] = []
    deadline = time.monotonic() + BUSY_RETRY_SECONDS
    while len(pages) < MAX_PAGES:
        with http.stream("GET", f"{job_url}/NextDocument") as response:
            if response.status_code == 404:
                break  # Auftrag abgeschlossen
            if response.status_code in (409, 503):
                if time.monotonic() > deadline:
                    raise ScanError("Der Netzwerkscanner ist beschäftigt oder nicht bereit.")
                sleep(1.0)
                continue
            if response.status_code != 200:
                raise ScanError(f"Netzwerkscanner liefert Fehler (HTTP {response.status_code}).")
            data = _read_limited(response, MAX_PAGE_BYTES)
        if not data.startswith(b"\xff\xd8"):
            raise ScanError("Der Netzwerkscanner lieferte kein JPEG-Bild.")
        path = workdir / f"page-{len(pages) + 1:04d}.jpg"
        path.write_bytes(data)
        pages.append(path)
        deadline = time.monotonic() + BUSY_RETRY_SECONDS
    if not pages:
        raise ScanError("Der Netzwerkscanner lieferte keine Seiten (Einzug leer?).")
    return pages


class EsclBackend:
    """Findet eSCL-Scanner per mDNS. Ereignisgesteuert, daher ``interval = 0``."""

    kind = "escl"
    interval = 0.0

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._found: dict[str, DiscoveredScanner] = {}
        self._zeroconf: Any = None
        self._browsers: list[Any] = []

    def start(self) -> None:
        if self._zeroconf is not None:
            return
        try:
            from zeroconf import ServiceBrowser, Zeroconf

            self._zeroconf = Zeroconf()
            self._browsers = [
                ServiceBrowser(self._zeroconf, service_type, handlers=[self._on_change])
                for service_type in SERVICE_TYPES
            ]
        except Exception:  # noqa: BLE001 - kein Netzwerk o. Ä. darf den Start nicht verhindern
            logger.warning("mDNS-Suche nach Netzwerkscannern konnte nicht gestartet werden", exc_info=True)
            self.stop()

    def stop(self) -> None:
        for browser in self._browsers:
            try:
                browser.cancel()
            except Exception:  # noqa: BLE001
                pass
        self._browsers = []
        if self._zeroconf is not None:
            try:
                self._zeroconf.close()
            except Exception:  # noqa: BLE001
                pass
            self._zeroconf = None

    def discover(self) -> list[DiscoveredScanner]:
        with self._lock:
            entries = list(self._found.values())
        # Dasselbe Gerät meldet sich oft als _uscan und _uscans: https bevorzugen.
        unique: dict[str, DiscoveredScanner] = {}
        for scanner in entries:
            current = unique.get(scanner.native_id)
            if current is None or scanner.extra["url"].startswith("https"):
                unique[scanner.native_id] = scanner
        return sorted(unique.values(), key=lambda s: s.name.casefold())

    def _on_change(self, zeroconf: Any, service_type: str, name: str, state_change: Any) -> None:
        from zeroconf import ServiceStateChange

        if state_change is ServiceStateChange.Removed:
            with self._lock:
                self._found.pop(name, None)
            return
        info = zeroconf.get_service_info(service_type, name, timeout=3000)
        scanner = scanner_from_service(info, tls=service_type.startswith("_uscans"))
        if scanner is not None:
            with self._lock:
                self._found[name] = scanner

    def acquire(self, scanner: DiscoveredScanner, profile: ScanProfile, workdir: Path) -> list[Path]:
        # Selbstsignierte Zertifikate sind bei Scannern der Normalfall; die Adresse
        # stammt ausschließlich aus der mDNS-Suche und ist auf das LAN beschränkt.
        return scan_escl(scanner.extra["url"], profile, workdir, verify_tls=False)


def scanner_from_service(info: Any, *, tls: bool) -> DiscoveredScanner | None:
    """Baut aus einem mDNS-Eintrag einen Scanner; ignoriert alles außerhalb des LAN."""
    if info is None or not info.port:
        return None
    try:
        from zeroconf import IPVersion

        addresses = info.parsed_addresses(IPVersion.V4Only)
    except Exception:  # noqa: BLE001
        addresses = []
    address = next((a for a in addresses if _is_local_address(a)), None)
    if address is None:
        return None

    def prop(key: bytes) -> str:
        value = (info.properties or {}).get(key)
        return value.decode("utf-8", "replace").strip() if isinstance(value, bytes) else ""

    resource = _safe_resource(prop(b"rs"))
    scheme = "https" if tls else "http"
    base_url = f"{scheme}://{address}:{info.port}/{resource}"
    display = prop(b"ty") or str(info.name).split(".")[0]
    uuid = re.sub(r"[^A-Za-z0-9\-]", "", prop(b"uuid"))
    # Die UUID bleibt stabil, wenn der Router dem Scanner eine neue IP gibt.
    return DiscoveredScanner(
        kind="escl",
        native_id=uuid or f"{address}:{info.port}",
        name=display[:120],
        extra={"url": base_url},
    )
