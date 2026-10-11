# Nospe – Entwicklung und Release

## Architektur auf einen Blick

- `frontend/`: React/Vite-Oberfläche und Tauri-Desktop-App.
- `frontend/src-tauri/`: Rust-Host. Startet beim normalen App-Start ausschließlich `nospe-backend.exe` auf `127.0.0.1:8765`.
- `backend/`: FastAPI, TWAIN-Scan, PDF-Erzeugung, Einstellungen und Paperless-Upload.
- `twain_ds/`: optionaler nativer TWAIN-Data-Source für den virtuellen Scanner.
- `backend/dist/emulator/nospe-emulator.exe`: separat gebauter Emulator. Er ist absichtlich nicht Teil des Nospe-Installers.

Die persistente Nutzerkonfiguration liegt bei der installierten App unter:

```text
%APPDATA%\Nospe\config.json
```

Sie enthält unter anderem Zielordner, ausgewählten Scanner und Paperless-Zugangsdaten. Keine Tokens in Logs, Tests, Screenshots oder Commits ausgeben.

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

Das Frontend erwartet das Backend auf `http://127.0.0.1:8765`.

## Scanner und Emulator

Nospe verwendet Windows-TWAIN-Quellen (64 Bit).

- Echte Windows-Scanner stehen in der Liste immer zuerst und werden dadurch als Standard gewählt.
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
