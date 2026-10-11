# Nospe

Windows-App für den Epson DS-410 und andere Scanner: scannen, PDF erzeugen, optional zu **Paperless-ngx** hochladen.

```
Tauri 2 App (React/TypeScript)
   │  Tauri-Kommando backend_config  →  Port + Secret (pro Start zufällig)
   ▼
Python FastAPI Backend (Sidecar, nur 127.0.0.1, Header X-Nospe-Token)
   ├─ TWAIN  (pytwain, 64 Bit)        Epson Scan 2 u. a.
   ├─ WIA 2.0 (COM, pywin32)          alles, was Windows als Scanner kennt
   └─ eSCL/AirScan (mDNS, httpx)      Netzwerkscanner ohne Treiber
   ▼
lokale PDF  →  optional Paperless-ngx (POST /api/documents/post_document/)
```

## Status

| Bereich | Stand |
|---------|-------|
| Backend, Sicherheitsmodell, Scanner-Registry | implementiert, 152 automatisierte Tests (Linux, mit Mocks) |
| TWAIN-Scan (Epson DS-410) | implementiert, vor dem Einsatz am echten Gerät testen |
| WIA- und eSCL-Scan | implementiert, **nur gegen simulierte Geräte getestet** |
| DPAPI-Tokenverschlüsselung, Tauri-Host (Rust) | **auf Windows noch nicht ausgeführt/kompiliert** |
| Virtueller Scanner (`twain_ds/`) | Entwicklungswerkzeug, nicht produktionsreif |

Die Punkte „nicht getestet“ sind die erste Aufgabe beim ersten Windows-Lauf, siehe [Checkliste](docs/INSTALL.md#7-erster-test-checkliste).

## Quickstart (Entwicklung auf Windows)

Voraussetzungen: Windows 10/11 x64, [uv](https://docs.astral.sh/uv/), Node.js 20+, Rust (stable, MSVC), 64-bit-TWAIN-DSM und Scanner-Treiber (Details in [docs/INSTALL.md](docs/INSTALL.md)).

```powershell
git clone https://github.com/<user>/nospe.git
cd nospe

# 1. Backend vorbereiten und prüfen
cd backend
uv sync
uv run python -m pytest -q          # 152 Tests
uv run python scripts/verify_twain.py

# 2. Backend starten (Terminal 1) - gibt Port und Secret aus
$env:NOSPE_DEV = "1"
$env:NOSPE_API_SECRET = "dev-secret-0123456789abcdef"
uv run python run_backend.py

# 3. App starten (Terminal 2), gegen dieses Backend
cd ..\frontend
npm install
$env:NOSPE_API_PORT = "8765"
$env:NOSPE_API_SECRET = "dev-secret-0123456789abcdef"
npm run tauri dev
```

Nur die Oberfläche im Browser (ohne Tauri): `VITE_NOSPE_API_URL=http://127.0.0.1:8765` und `VITE_NOSPE_API_SECRET=<Secret>` setzen, dann `npm run dev` (http://localhost:5173).

Auf Linux/macOS laufen Backend-Tests und die Web-UI; gescannt wird nur unter Windows.

## Installation für Anwender

Installer bauen und installieren: [docs/INSTALL.md](docs/INSTALL.md).

## Projektstruktur

```
backend/        FastAPI, Scanner-Backends, PDF, Einstellungen, Paperless
  app/scanner/    registry.py, twain_*.py, wia_backend.py, escl_backend.py, scan_service.py
  app/security.py Secret-, Host- und Origin-Prüfung
  app/settings.py Konfiguration, URL-/Pfad-Validierung, DPAPI-Token
frontend/       React + Vite UI
  src-tauri/      Rust-Host: startet den Sidecar, übergibt Port/Secret
twain_ds/       Virtueller TWAIN-Scanner (C++, nur Entwicklung)
docs/           TWAIN-Setup, Installationsanleitung
DEVELOPMENT.md  Architektur, Sicherheitsmodell, Release-Ablauf
```

## Sicherheit in Kürze

- Das Backend lauscht nur auf `127.0.0.1`, mit **zufälligem Port und Secret pro Start**; jede Anfrage braucht `X-Nospe-Token`. `Host`- und `Origin`-Prüfung gegen DNS-Rebinding und fremde Webseiten.
- Der Paperless-Token liegt nur DPAPI-verschlüsselt in `%APPDATA%\Nospe\config.json` und ist an die Paperless-Server-URL gebunden.
- Scan-Zwischendateien werden auch bei Fehlern gelöscht.

Details: [DEVELOPMENT.md](DEVELOPMENT.md#sicherheitsmodell-der-lokalen-api).

## API (nur über die App/mit Secret erreichbar)

| Methode | Pfad               | Zweck                                                   |
|---------|--------------------|---------------------------------------------------------|
| GET     | `/health`          | `{ ok, version }`                                       |
| GET     | `/scanners`        | Geräte aller Zugänge aus dem Cache (`?refresh=true` erzwingt Suche) |
| GET     | `/scanners/status` | TWAIN-Diagnose (Bitness, DSM, Quellen, Hinweise)        |
| GET     | `/profiles`        | Scan-Profile (Duplex Grau / Simplex Farbe)              |
| POST    | `/scan`            | Scan ausführen, PDF-Pfad zurückgeben                    |
| GET/POST| `/settings`        | Einstellungen (Token nie im Klartext)                   |
| POST    | `/paperless/test`  | Verbindung zu Paperless-ngx prüfen                      |

## Weitere Dokumentation

- [docs/INSTALL.md](docs/INSTALL.md): Voraussetzungen, Bauen, Installieren, Fehlersuche
- [docs/TWAIN_SETUP.md](docs/TWAIN_SETUP.md): TWAIN-DSM und Epson-Treiber
- [DEVELOPMENT.md](DEVELOPMENT.md): Architektur, Sicherheitsmodell, Emulator, Release
- [twain_ds/README.md](twain_ds/README.md): virtueller Scanner
