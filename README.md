# Nospe

Windows-App für den Epson DS-410: lokal scannen → PDF erzeugen → optional zusätzlich zu **Paperless-ngx** hochladen.

Dieser Stand ist der **MVP**: vollständige UI + lauffähige Backend-Struktur mit **Stub-Endpunkten**
plus lokalem PDF-Emulator-Spool. Es gibt bewusst **noch keinen echten Epson-TWAIN-Zugriff** und
**keinen echten Paperless-Upload**.

```
Tauri 2 App (React/TypeScript)
   ↓ HTTP  http://127.0.0.1:8765
Python FastAPI Backend  (Stub)
   ↓ TWAIN        (später)
Epson DS-410
   ↓
lokale PDF
   ↓ optional
Paperless-ngx API        (später)
```

## Projektstruktur

```
nospe/
├─ frontend/        Tauri 2 + React + TypeScript + Vite UI
│  ├─ src/          App, Komponenten, API-Client, Types, Styles
│  └─ src-tauri/    Tauri-2-Stub (Rust)
├─ backend/         Python FastAPI Backend (Stub-Endpunkte)
└─ README.md
```

## Frontend (UI)

### Start (Dev)

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

### Build

```bash
cd frontend
npm run build      # tsc + vite build -> frontend/dist
```

### Tauri (Desktop)

```bash
cd frontend
npm run tauri dev      # benötigt Rust + WebKitGTK (Linux) bzw. WebView2 (Windows)
npm run tauri build
```

> Tauri benötigt eine Rust-Toolchain und Plattform-WebView-Abhängigkeiten.
> Ohne diese läuft die App weiterhin als reine Web-UI über Vite (`npm run dev`).

## Backend (FastAPI Stub)

```bash
cd backend
uv sync
uv run python run_backend.py  # startet 127.0.0.1:8765
```

Alternativ direkt mit Uvicorn:

```bash
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Health-Check:

```bash
curl http://127.0.0.1:8765/health
# {"ok":true,"version":"0.1.0"}
```

### Endpunkte

| Methode | Pfad              | Zweck                                              |
| ------- | ----------------- | ------------------------------------------------- |
| GET     | `/health`         | `{ ok, version }`                                 |
| GET     | `/scanners`       | TWAIN-Quellen (64-bit, echte ProductNames)         |
| GET     | `/scanners/status`| TWAIN-Diagnose (Bitness, DSM, Quellen, Hinweise)   |
| GET     | `/profiles`       | Scan-Profile (Duplex Grau / Simplex Farbe)        |
| POST    | `/scan`           | Führt den Scan aus und liefert den PDF-Pfad       |
| GET     | `/settings`       | Settings lesen (Token nie im Klartext)            |
| POST    | `/settings`       | Settings speichern (Token nur bei Eingabe)        |
| POST    | `/paperless/test` | Konfig-Check (Stub, kein echter Request)          |
| GET     | `/emulator`       | Minimaler PDF-Upload für den virtuellen Scanner   |
| POST    | `/emulator/upload`| Eine PDF hochladen und in Scanseiten rendern      |
| GET     | `/emulator/job`   | Aktiven Emulator-Job lesen                        |
| POST    | `/emulator/job/consume` | Aktiven Emulator-Job verbrauchen            |

## TWAIN-PDF-Emulator

Der Emulator besteht aus zwei Teilen:

- Python/FastAPI speichert genau eine aktive PDF unter `%LOCALAPPDATA%\Nospe\twain-emulator\active` und rendert sie sofort als 300-DPI-RGB-PNG-Seiten.
- `twain_ds/` enthält das native Windows-x64-Data-Source-Modul `NospeVirtualScanner.ds` mit exportiertem `DS_Entry` und der Identität `Nospe Virtual Scanner`.

Der Emulator ist bewusst **nicht** Teil des Nospe-Installers und wird beim Start
von Nospe nicht gestartet. Die normale App listet ausschließlich die in Windows
installierten echten TWAIN-Scanner; der virtuelle Scanner bleibt ein manuell
gestartetes Diagnosewerkzeug.

Upload-Seite separat starten:

```bash
cd backend
uv run python run_emulator.py
# http://127.0.0.1:8766/emulator
```

Als separate EXE bauen und starten:

```powershell
cd backend
.\scripts\build_emulator.ps1
.\dist\emulator\nospe-emulator.exe
```

Das normale Nospe-Backend bleibt auf `http://127.0.0.1:8765` und liefert keine
Emulator-Seite aus.

Native Data Source bauen:

```powershell
cmake -S twain_ds -B twain_ds/build -A x64
cmake --build twain_ds/build --config Release
```

Danach `twain_ds/build/Release/NospeVirtualScanner.ds` als Administrator nach
`C:\Windows\twain_64\NospeVirtualScanner.ds` kopieren. Der native Teil unterstützt Identität, Open/Close, Manifest-Lesen und nativen
Memory-Transfer (DIB) für die Emulator-PNG-Seiten. Nach Änderungen am `.ds` neu
bauen und nach `C:\Windows\twain_64\` kopieren.

## Backend offline

Die UI verwendet ausschließlich das echte Backend. Wenn `http://127.0.0.1:8765`
nicht erreichbar ist, zeigt sie den Offline-Zustand und erzeugt keine lokalen
Ersatzdaten.

## TWAIN 64-bit (Phase 0 + 1)

Verifikation und Setup: [docs/TWAIN_SETUP.md](docs/TWAIN_SETUP.md)

```powershell
cd backend
uv run python scripts/verify_twain.py
```

Backend listet Scanner über **pytwain** (`GET /scanners`). Ohne 64-bit-Treiber/DSM ist die Liste leer.

## Scan (Phase 2)

`POST /scan` führt einen echten TWAIN-Scan aus, schreibt eine PDF in den konfigurierten Zielordner und gibt den Dateipfad zurück. Für Farbdokumente fordert Nospe RGB mit 24 Bit an und bricht mit einer verständlichen Meldung ab, wenn der Windows-TWAIN-Treiber das nicht liefern kann.

Testablauf Virtual Scanner:

1. Emulator: `uv run python run_emulator.py` → PDF auf http://127.0.0.1:8766/emulator laden
2. Optional: `NospeVirtualScanner.ds` neu bauen und nach `C:\Windows\twain_64\` kopieren (echter TWAIN-Transfer)
3. Backend: `uv run python run_backend.py`
4. In der Nospe-UI Scanner **Nospe Virtual Scanner** wählen und scannen

Umgehungsvariable (nur Spool, kein TWAIN): `NOSPE_EMULATOR_DIRECT_SCAN=1`

## Bundling und lokaler E2E-Start

Für die Desktop-Bundle-Erstellung wird das Backend als PyInstaller-Sidecar gebaut:

```powershell
cd backend
uv run pyinstaller --clean --noconfirm --distpath ..\frontend\src-tauri\binaries --workpath build\pyinstaller nospe_backend.spec
```

Die erzeugte `nospe-backend.exe` wird beim Start der gebündelten Tauri-App
automatisch gestartet und beim Beenden beendet.

Für lokale Tests starten Backend und Scanner-Emulator gemeinsam:

```powershell
cd backend
uv sync
uv run python run_local.py
```

Danach stehen `http://127.0.0.1:8765/health` und
`http://127.0.0.1:8766/emulator` bereit.

## Noch nicht implementiert (nächste Schritte)
- Echter Paperless-ngx-Upload (`POST /api/documents/post_document/`)
