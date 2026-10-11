"""Verschlüsselte Ablage kleiner Geheimnisse (Paperless-Token).

Unter Windows wird DPAPI (``CryptProtectData``) genutzt: das Geheimnis ist an das
Windows-Benutzerkonto gebunden, eine kopierte ``config.json`` ist auf einem
anderen Konto/Rechner wertlos. Es braucht keine zusätzliche Abhängigkeit.

Auf anderen Plattformen (nur Entwicklung/Tests, Nospe scannt nur unter Windows)
gibt es keinen Schlüsselbund, dort wird Base64 mit dem Präfix ``plain:`` genutzt
und das ausdrücklich nicht als Verschlüsselung verstanden.
"""

from __future__ import annotations

import base64
import sys

_ENTROPY = b"de.janoschbl.nospe/paperless-token/v1"
_DPAPI_PREFIX = "dpapi:v1:"
_PLAIN_PREFIX = "plain:v1:"


class SecretStoreError(Exception):
    """Entschlüsselung/Verschlüsselung nicht möglich."""


def protect(value: str) -> str:
    """Gibt einen speicherbaren String zurück; leerer Wert bleibt leer."""
    if not value:
        return ""
    raw = value.encode("utf-8")
    if sys.platform == "win32":
        return _DPAPI_PREFIX + base64.b64encode(_dpapi_protect(raw)).decode("ascii")
    return _PLAIN_PREFIX + base64.b64encode(raw).decode("ascii")


def unprotect(stored: str) -> str:
    if not stored:
        return ""
    try:
        if stored.startswith(_DPAPI_PREFIX):
            if sys.platform != "win32":
                raise SecretStoreError("DPAPI-Geheimnis auf dieser Plattform nicht lesbar.")
            blob = base64.b64decode(stored[len(_DPAPI_PREFIX):], validate=True)
            return _dpapi_unprotect(blob).decode("utf-8")
        if stored.startswith(_PLAIN_PREFIX):
            return base64.b64decode(stored[len(_PLAIN_PREFIX):], validate=True).decode("utf-8")
    except SecretStoreError:
        raise
    except Exception as exc:  # noqa: BLE001 - defekte Daten
        raise SecretStoreError("Gespeichertes Geheimnis ist beschädigt.") from exc
    raise SecretStoreError("Unbekanntes Format des gespeicherten Geheimnisses.")


def _dpapi_call(function_name: str, data: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def make_blob(payload: bytes) -> tuple[DataBlob, ctypes.Array]:
        buffer = ctypes.create_string_buffer(payload, len(payload))
        return DataBlob(len(payload), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer

    crypt32 = ctypes.windll.crypt32  # type: ignore[attr-defined]
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]

    source, source_buffer = make_blob(data)
    entropy, entropy_buffer = make_blob(_ENTROPY)
    result = DataBlob()
    function = getattr(crypt32, function_name)
    ui_forbidden = 0x1
    ok = function(
        ctypes.byref(source),
        None,
        ctypes.byref(entropy),
        None,
        None,
        ui_forbidden,
        ctypes.byref(result),
    )
    del source_buffer, entropy_buffer
    if not ok:
        raise SecretStoreError(f"{function_name} fehlgeschlagen (Fehler {ctypes.GetLastError()}).")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(result.pbData, ctypes.c_void_p))


def _dpapi_protect(data: bytes) -> bytes:
    # CryptProtectData(in, description, entropy, reserved, prompt, flags, out)
    return _dpapi_call("CryptProtectData", data)


def _dpapi_unprotect(data: bytes) -> bytes:
    # CryptUnprotectData(in, description_out, entropy, reserved, prompt, flags, out)
    return _dpapi_call("CryptUnprotectData", data)
