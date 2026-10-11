# Nospe – Entwicklung und Release

## Architektur auf einen Blick

- `frontend/`: React/Vite-Oberfläche und Tauri-Desktop-App.
- `frontend/src-tauri/`: Rust-Host. Startet beim normalen App-Start ausschließlich `nospe-backend.exe` auf `127.0.0.1` (zufälliger Port, siehe „Sicherheitsmodell“).
- `backend/`: FastAPI, TWAIN-Scan, PDF-Erzeugung, Einstellungen und Paperless-Upload.
- `twain_ds/`: optionaler nativer TWAIN-Data-Source für den virtuellen Scanner.
- `backend/dist/emulator/nospe-emulator.exe`: separat gebauter Emulator. Er ist absichtlich nicht Teil des Nospe-Installers.

Die persistente Nutzerkonfiguration liegt bei der installierten App unter:

```text
%APPDATA%\Nospe\config.json
```

Sie enthält unter anderem Zielordner, ausgewählten Scanner und die Paperless-URL. Der Paperless-Token liegt dort nur **DPAPI-verschlüsselt** (an das Windows-Konto gebunden) und an den Origin der Paperless-URL gebunden. Ältere Klartext-Tokens werden beim ersten Lesen automatisch migriert. Keine Tokens in Logs, Tests, Screenshots oder Commits ausgeben.

## Sicherheitsmodell der lokalen API

Loopback ist keine Vertrauensgrenze: jede Webseite im Browser und jeder andere Prozess kann `127.0.0.1` ansprechen. Deshalb:

- **Zufälliger Port + Secret pro Start.** Tauri übergibt dem Sidecar `NOSPE_HANDSHAKE_FILE`; das Backend bindet einen freien Port, erzeugt das Secret und schreibt beides (Zeile 1 Port, Zeile 2 Secret) in diese Datei. Tauri liest und löscht sie und reicht die Werte nur über das Kommando `backend_config` an die UI weiter.
- Jede Anfrage braucht den Header `X-Nospe-Token`; falscher/fehlender Token → 401. Der Header erzwingt außerdem einen CORS-Preflight, den fremde Origins nicht bestehen.
- `Host` muss `127.0.0.1:<Port>`/`localhost:<Port>` sein (gegen DNS-Rebinding), ein vorhandener `Origin` muss auf der Allowlist stehen (nur `tauri://localhost` & Co.; `localhost:5173` nur mit `NOSPE_DEV=1`).
- Der Paperless-Token wird nur an den Server geschickt, für den er eingegeben wurde. Wird die URL auf einen anderen Server geändert, muss er neu eingegeben werden. `http://` ist nur im lokalen Netz erlaubt.
- Das Backend beendet sich selbst, wenn Tauri verschwindet (`NOSPE_PARENT_PID`).
- Keine `/docs`/`/openapi.json`.

Entwicklung ohne Tauri-Sidecar:

```powershell
# Terminal 1: Backend (gibt Port und Secret auf stderr aus, oder selbst setzen)
cd backend
$env:NOSPE_DEV = "1"; $env:NOSPE_API_SECRET = "dev-secret-0123456789abcdef"
uv run python run_backend.py

# Terminal 2a: Tauri gegen dieses Backend
cd frontend
$env:NOSPE_API_PORT = "8765"; $env:NOSPE_API_SECRET = "dev-secret-0123456789abcdef"
npm run tauri dev

# Terminal 2b: oder nur der Vite-Server im Browser
$env:VITE_NOSPE_API_URL = "http://127.0.0.1:8765"; $env:VITE_NOSPE_API_SECRET = "dev-secret-0123456789abcdef"
npm run dev
```

## Lokales Entwickeln

Backend:

```powershell
cd backend
uv sync
uv run python run_backend.py
```

Frontend/Tauri im Entwicklungsmodus:

```powershell
cd frontend
npm install
npm run tauri dev
```

Port und Secret des Backends siehe „Sicherheitsmodell der lokalen API“.

## Scanner und Emulator

Nospe sucht Scanner automatisch über drei Zugänge (`backend/app/scanner/registry.py`), IDs sind `twain:<Name>`, `wia:<DeviceID>` oder `escl:<UUID>`:

| Zugang | Findet | Hinweis |
|--------|--------|---------|
| TWAIN | Geräte mit 64-bit-TWAIN-Treiber (z. B. Epson Scan 2) | bevorzugt, beste Einzug-/Duplex-Unterstützung |
| WIA 2.0 | alles, was Windows selbst als Scanner kennt (auch WSD-Netzwerkscanner, Geräte ohne TWAIN) | COM über `pywin32`, nur Windows |
| eSCL/AirScan | Netzwerkscanner per mDNS (`_uscan._tcp`) | kein Treiber nötig, nur LAN-Adressen |

- Die Registry fragt im Hintergrund ab (WIA alle 5 s, TWAIN alle 30 s, eSCL ereignisgesteuert); `GET /scanners` liest nur den Cache. Während eines Scans wird nichts abgefragt.
- Dasselbe Gerät in mehreren Zugängen wird einmal angezeigt (TWAIN bevorzugt, die anderen als `also_via`).
- Alles, was den TWAIN-DSM anfasst (Umgebungsprüfung, Quellenliste, Scan), läuft unter `twain_lock.TWAIN_LOCK`.

Nospe verwendet Windows-TWAIN-Quellen (64 Bit).

- Echte Scanner stehen in der Liste immer vor dem virtuellen und werden dadurch als Standard gewählt.
- `Nospe Virtual Scanner` erscheint nur dann zusätzlich, wenn der separate Emulator läuft und die virtuelle `.ds`-Quelle in Windows installiert ist.
- Der Emulator wird nicht automatisch von Nospe gestartet und nicht in den Installer gepackt.

Emulator separat starten:

```powershell
backend\dist\emulator\nospe-emulator.exe
# danach: http://127.0.0.1:8766/emulator
```

Emulator neu bauen:

```powershell
cd backend
.\scripts\build_emulator.ps1
```

TWAIN prüfen:

```powershell
cd backend
uv run python scripts\verify_twain.py
```

Details zur Treiber-/DSM-Bitness: [docs/TWAIN_SETUP.md](docs/TWAIN_SETUP.md).

Wichtig: Der TWAIN-DSM ist pro Prozess global und nicht nebenläufig sicher. Die Quellenermittlung daher nicht parallel über mehrere Endpunkte auslösen. Beim Scan setzt `Farbe` `TWPT_RGB` plus 24 Bit; kann ein Treiber das nicht, muss der Scan mit einer verständlichen Fehlermeldung abbrechen, nicht still in Grau weiterlaufen.

## Tests und Qualitätsgates

Nach Backend-Änderungen mindestens:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Nach Frontend-/Rust-Änderungen:

```powershell
cd frontend
npm run build

cd src-tauri
cargo check
```

Für E2E-Änderungen zusätzlich die installierte Anwendung testen: Backend-Health, Scannerstatus, Einstellungs-Persistenz nach Neustart und bei Bedarf Paperless gegen die echte Instanz. Keine echten Dokumente oder Tokens in Testausgaben speichern.

## Release bauen und installieren

1. Backend-Sidecar bauen:

```powershell
cd backend
uv run pyinstaller --clean --noconfirm `
  --distpath ..\frontend\src-tauri\binaries `
  --workpath build\pyinstaller nospe_backend.spec
```

2. Target-Datei für Tauri aktualisieren:

```powershell
cd ..\frontend\src-tauri
Copy-Item -LiteralPath binaries\nospe-backend.exe `
  -Destination binaries\nospe-backend-x86_64-pc-windows-msvc.exe -Force
```

3. Installer bauen:

```powershell
cd ..
npm run tauri build
```

Der Installer liegt danach hier:

```text
frontend\src-tauri\target\release\bundle\nsis\Nospe_0.1.0_x64-setup.exe
```

Vor einem Upgrade die laufende Nospe-App schließen. Danach den Installer starten und die installierte App aus `%LOCALAPPDATA%\Nospe\nospe.exe` testen.

## E2E-Implementierungen

Bei einer neuen Funktion immer den vollständigen Pfad verfolgen:

1. API-Contract in `backend/app/models.py` definieren oder erweitern.
2. Backend-Route und Logik implementieren, zuerst mit Backend-Test.
3. TypeScript-Typen und `frontend/src/api.ts` synchronisieren.
4. UI anbinden und Zustand/Fehlerzustand prüfen.
5. Bei Änderungen an Sidecars, Rust oder Tauri-Konfiguration den Installer neu bauen.
6. Mit der installierten EXE testen, nicht nur mit Vite oder dem Python-Backend.

Besonders beachten:

- Dateinamen dürfen nie vorhandene PDFs überschreiben; `resolve_output_path` nummeriert Kollisionen.
- Einstellungen im UI dürfen für die Session sofort gelten; dauerhaft werden sie erst über „Speichern“ geschrieben.
- Paperless-Antworten können unterschiedlich strukturiert sein. Fehler robust behandeln und Token nie zurückgeben.
- Bei einem Fehler zuerst den tatsächlich laufenden Prozess, Port und API-Status prüfen, bevor Dienste neu gestartet werden.
