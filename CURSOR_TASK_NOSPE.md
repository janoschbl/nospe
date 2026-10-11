# Cursor Agent Auftrag: Nospe MVP implementieren

Du bist der Coding-Agent für das Projekt Nospe. Arbeite im Workspace `/root/nospe`.

## Wichtig

- Implementiere selbstständig. Frag nicht zurück, außer es ist wirklich blockierend.
- Nutze vorhandene Skills falls verfügbar: `caveman`, `ui-ux-pro-max`, `impeccable`.
- Design darf modern/polished sein, aber Funktion und Build sind Pflicht.
- Keine echten TWAIN-Zugriffe bauen.
- Kein echter Paperless Upload.
- Baue UI + vorbereitete Python-FastAPI-Backend-Stubs/Mocks, damit das spätere Backend einfach anschließbar ist.
- Am Ende wirklich ausführen: `npm install`, `npm run build`, möglichst auch Tauri build/dev. Zusätzlich Backend kurz verifizieren, falls du Backend anlegst.
- Committe nur, wenn Git-Repo sauber ist und keine fremden Änderungen überschrieben werden.

## Gelesene Pläne

Lies zuerst:

- `/root/.hermes/plans/nospe-tauri-python-paperless-plan.md`
- `/root/.hermes/plans/2026-06-02_074005-nospe-tauri-ui-mvp-plan.md`

Setze daraus konkret um.

## Ziel

Baue den ersten MVP von Nospe:

- Tauri 2 + React + TypeScript + Vite UI
- lokale Python FastAPI Backend-Struktur mit Stub-Endpunkten
- Frontend API Client gegen `http://127.0.0.1:8765`
- Mock-Fallback, falls Backend nicht erreichbar ist
- UI zeigt klar: `Backend nicht erreichbar — Mock-Modus aktiv`
- UI-Sprache Deutsch

## Erwartete Struktur

Falls noch kein Projekt existiert, erstelle:

```text
nospe/
├─ frontend/
│  ├─ package.json
│  ├─ index.html
│  ├─ tsconfig.json
│  ├─ tsconfig.node.json
│  ├─ vite.config.ts
│  ├─ src/
│  │  ├─ main.tsx
│  │  ├─ App.tsx
│  │  ├─ api.ts
│  │  ├─ types.ts
│  │  ├─ styles.css
│  │  └─ components/
│  │     ├─ ScanPanel.tsx
│  │     ├─ SettingsPanel.tsx
│  │     ├─ StatusLog.tsx
│  │     └─ LastScanCard.tsx
│  └─ src-tauri/
│     ├─ Cargo.toml
│     ├─ build.rs
│     ├─ tauri.conf.json
│     └─ src/
│        └─ main.rs
├─ backend/
│  ├─ app/
│  │  ├─ __init__.py
│  │  ├─ main.py
│  │  ├─ models.py
│  │  ├─ settings.py
│  │  ├─ scanner/
│  │  │  ├─ __init__.py
│  │  │  └─ profiles.py
│  │  └─ paperless/
│  │     ├─ __init__.py
│  │     └─ client.py
│  ├─ requirements.txt
│  └─ run_backend.py
└─ README.md
```

Wenn bestehende Struktur da ist, passe dich daran an.

## Frontend UI

Zielbild:

```text
Nospe

Scanner
[ EPSON DS-410 v ]

Profil
[ Duplex Grau 300 DPI v ]

Titel
[ Rechnung / Dokumentname ]

[✓] Zusätzlich zu Paperless hochladen

[ Scannen ]

Status:
Bereit
```

Nach Scan:

```text
Scan fertig

Datei:
C:\Users\Janosch\Documents\Scans\scan.pdf

[PDF öffnen] [Ordner öffnen]

Paperless:
Hochgeladen / Nicht hochgeladen / Fehler
```

Settings Screen:

```text
Scan-Ausgabeordner
[ C:\Users\Janosch\Documents\Scans ]

Paperless URL
[ https://... ]

Paperless Token
[ **** ]

[Verbindung testen]
[Speichern]
```

## Frontend Komponenten

### App.tsx

- Layout
- Tabs/Nav: `Scan`, `Einstellungen`
- Initialdaten laden: health, scanners, profiles, settings
- Backend-Status: Online oder Offline/Mock-Modus
- Statuslog führen

### ScanPanel.tsx

Props ungefähr:

```ts
type ScanPanelProps = {
  scanners: Scanner[];
  profiles: ScanProfile[];
  onScan: (request: ScanRequest) => Promise<ScanResponse>;
};
```

UI:

- Scanner Select
- Profil Select
- Titel Input
- Checkbox `Zusätzlich zu Paperless hochladen`
- Button `Scannen`
- Disabled/loading State
- Statusmeldungen simulieren:
  - Bereit
  - Starte Scan...
  - Scanne...
  - Baue PDF...
  - Upload zu Paperless...
  - Fertig
  - Fehler

### LastScanCard.tsx

- Datei-Pfad
- Upload-Status
- Paperless Dokument-ID falls vorhanden
- Paperless Fehler falls vorhanden
- Buttons PDF öffnen / Ordner öffnen erstmal Stub mit `console.log()` oder Tauri Shell wenn leicht machbar

### SettingsPanel.tsx

- Scan Output Directory Input
- Paperless URL Input
- Paperless Token Input
- Verbindung testen
- Speichern
- Token nicht aus `/settings` anzeigen
- Placeholder `Token ist gespeichert`, falls `paperless_token_set === true`
- Neuer Token nur mitsenden, wenn User etwas eingibt

### StatusLog.tsx

- Liste mit Uhrzeit: `[21:42:10] Backend online`

## Types

In `frontend/src/types.ts`:

```ts
export type Scanner = { id: string; name: string };
export type ScanProfile = {
  id: string;
  name: string;
  duplex: boolean;
  adf: boolean;
  dpi: number;
  color_mode: "gray" | "color" | "bw";
};
export type ScanRequest = {
  scanner_id: string;
  profile_id: string;
  title: string;
  push_to_paperless: boolean;
};
export type ScanResponse = {
  ok: boolean;
  file_path: string;
  uploaded_to_paperless: boolean;
  paperless_document_id?: number;
  paperless_error?: string;
};
export type AppSettings = {
  scan_output_dir: string;
  paperless_url: string;
  paperless_token_set: boolean;
};
```

Ergänze weitere Response/Request Types sinnvoll.

## API Client

`frontend/src/api.ts`:

Base URL: `http://127.0.0.1:8765`

Endpoints:

- GET `/health`
- GET `/scanners`
- GET `/profiles`
- POST `/scan`
- GET `/settings`
- POST `/settings`
- POST `/paperless/test`

Implementiere:

- echten Backend-Call versuchen
- wenn Backend nicht erreichbar/Timeout: Mock-Daten nutzen
- App muss den Mock-Modus erkennen/anzeigen können

Mock Scanner:

```ts
[{ id: "EPSON DS-410", name: "EPSON DS-410" }]
```

Mock Profile:

```ts
[
  { id: "duplex_gray_300", name: "Duplex Grau 300 DPI", duplex: true, adf: true, dpi: 300, color_mode: "gray" },
  { id: "simplex_color_300", name: "Simplex Farbe 300 DPI", duplex: false, adf: true, dpi: 300, color_mode: "color" }
]
```

Mock Scan Response:

```ts
{
  ok: true,
  file_path: "C:\\Users\\Janosch\\Documents\\Scans\\mock-scan.pdf",
  uploaded_to_paperless: true,
  paperless_document_id: 123
}
```

## Backend Stub

Lege ein minimales Python FastAPI Backend an, das dieselben Endpoints bereitstellt.

- Port: `8765`
- CORS für Vite/Tauri erlauben
- `/health`: `{ ok: true, version: "0.1.0" }`
- `/scanners`: Epson DS-410 Mock
- `/profiles`: Profile wie oben
- `/scan`: simuliert kurzen Scan, gibt lokale Mock-PDF-Pfad-Antwort zurück
- `/settings`: liest/schreibt einfache lokale JSON-Datei, Token nie zurückgeben
- `/paperless/test`: Stub-Antwort, bei fehlender URL/Token sinnvolle Meldung

Keine echte TWAIN/Paperless Logik.

## UX-Stil

Modern, clean, kompakt:

- dunkles/neutrales Layout
- gute Cards
- klare Abstände
- sichtbare Buttons
- verständliche Status-Badges
- nicht enterprise-hässlich
- keine riesigen Textwände

Nutze `lucide-react`. Tailwind optional, CSS reicht.

## Verifikation Pflicht

Führe aus und berichte echte Ausgabe:

```bash
cd /root/nospe/frontend
npm install
npm run build
```

Wenn möglich:

```bash
npm run tauri build
```

Backend:

```bash
cd /root/nospe/backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python run_backend.py
```

Falls Server testweise gestartet wird, prüfe `/health` mit curl.

Wenn Tauri wegen Systemdeps/Rust/WebKit scheitert: exakt dokumentieren, React Build muss trotzdem erfolgreich sein.

## Ergebnisbericht

Am Ende knapp berichten:

- Dateien erstellt/geändert
- Startbefehle
- Build-Ergebnis
- Backend-Test-Ergebnis
- Tauri-Ergebnis oder Blocker
- aktive Mock-Daten
- was als nächstes real angeschlossen werden muss

## Commit

Nur wenn Repo sauber und kein Fremdcode überschrieben:

```bash
git add frontend backend README.md
 git commit -m "feat: add initial Nospe Tauri UI"
```
