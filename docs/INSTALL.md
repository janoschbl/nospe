# Nospe: Installationsanleitung

Zielsystem: **Windows 10/11, 64 Bit**. Gescannt wird nur unter Windows; Backend-Tests und die Web-UI laufen auch unter Linux/macOS.

Abschnitt 1-3: einmalige Vorbereitung. 4-5: Installer bauen und installieren. 6: Einstellungen. 7: Checkliste für den ersten Test. 8: Fehlersuche.

## 1. Scanner-Treiber und TWAIN-DSM

Nospe findet Scanner über drei Wege. Mindestens einer muss funktionieren:

| Weg | Voraussetzung |
|-----|---------------|
| **TWAIN** (empfohlen für den Epson DS-410) | **Epson Scan 2** (nicht nur die alte „EPSON Scan“-App) und die 64-bit-`TWAINDSM.dll` |
| **WIA** | Nichts extra: jeder Scanner mit Windows-Treiber erscheint automatisch |
| **eSCL/AirScan** | Netzwerkscanner im selben Netz, mDNS nicht blockiert (Firewall/VLAN) |

### TWAIN-DSM installieren (PowerShell als Administrator)

Windows liefert den DSM nicht mit. Er ist nicht der Scanner-Treiber, sondern die Vermittler-DLL.

```powershell
$zip = "$env:TEMP\dsm_020501.zip"
Invoke-WebRequest -Uri "https://github.com/twain/twain-dsm/releases/download/v2.5.1/dsm_020501.zip" -OutFile $zip
Expand-Archive -Path $zip -DestinationPath "$env:TEMP\dsm_020501" -Force
Copy-Item "$env:TEMP\dsm_020501\dsm_020501\windows\64\TWAINDSM.dll" -Destination "$env:SystemRoot\System32\TWAINDSM.dll"
```

Mehr dazu und zur Bitness-Prüfung: [TWAIN_SETUP.md](TWAIN_SETUP.md).

## 2. Entwicklungswerkzeuge (nur zum Bauen)

| Werkzeug | Zweck | Installation |
|----------|-------|--------------|
| Git | Quellcode | `winget install Git.Git` |
| uv | Python-Umgebung (Python 3.11+, **64 Bit**) | `winget install astral-sh.uv` |
| Node.js 20+ | Frontend | `winget install OpenJS.NodeJS.LTS` |
| Rust (stable, MSVC) | Tauri-Host | `winget install Rustlang.Rustup`, danach `rustup default stable` |
| Visual Studio Build Tools | C++-Linker für Rust | `winget install Microsoft.VisualStudio.2022.BuildTools` (Workload „Desktop development with C++“) |
| WebView2 | Oberfläche | in Windows 11 enthalten; der Installer lädt es unter Windows 10 bei Bedarf nach |

## 3. Quellcode holen und prüfen

```powershell
git clone https://github.com/<user>/nospe.git
cd nospe\backend
uv sync
uv run python -m pytest -q
uv run python scripts/verify_twain.py
```

`verify_twain.py` sollte Exit-Code 0 liefern und deinen Scanner nennen. Andere Codes: siehe [TWAIN_SETUP.md](TWAIN_SETUP.md#verifikation-phase-0).

## 4. Installer bauen

```powershell
# a) Backend als Sidecar-EXE
cd backend
uv run pyinstaller --clean --noconfirm --distpath ..\frontend\src-tauri\binaries --workpath build\pyinstaller nospe_backend.spec

# b) Datei für Tauri benennen (Target-Triple)
cd ..\frontend\src-tauri
Copy-Item binaries\nospe-backend.exe binaries\nospe-backend-x86_64-pc-windows-msvc.exe -Force

# c) Rust prüfen, dann Installer bauen
cargo check
cd ..
npm install
npm run tauri build
```

Ergebnis: `frontend\src-tauri\target\release\bundle\nsis\Nospe_0.1.0_x64-setup.exe`

`cargo check` zuerst ausführen: der Rust-Teil wurde bisher nicht auf Windows kompiliert.

## 5. Installieren

1. Laufende Nospe-App schließen.
2. `Nospe_0.1.0_x64-setup.exe` ausführen. Der Installer ist nicht signiert, SmartScreen zeigt daher eine Warnung („Weitere Informationen“, „Trotzdem ausführen“).
3. Start über das Startmenü oder `%LOCALAPPDATA%\Nospe\nospe.exe`.

Beim Start erzeugt die App ein neues Backend mit zufälligem Port und Secret. Es muss nichts konfiguriert werden und es gibt keinen festen Port.

Deinstallation: Windows-Einstellungen, Apps. Die Einstellungen in `%APPDATA%\Nospe\config.json` bleiben dabei erhalten.

## 6. Einstellungen

In der App (Zahnrad):

- **Zielordner** für die PDFs (absolut; Systemordner wie `C:\Windows` sind gesperrt).
- **Paperless-URL** und **Token**. Erlaubt ist `https://…`; `http://` nur im lokalen Netz (private IP, `.local`, Einzel-Hostname). Der Token wird verschlüsselt gespeichert und gilt nur für diesen Server: bei geänderter URL muss er neu eingegeben werden.
- **Scanner**: wird automatisch gefunden. Angeschlossene Geräte erscheinen nach spätestens etwa 5 Sekunden (TWAIN bis 30 Sekunden). Mehrere Zugänge zum selben Gerät erscheinen nur einmal, TWAIN hat Vorrang.

Der Token wird nie in Logs, Screenshots oder Commits ausgegeben. Eine vorhandene Datei `backend\data\config.json` aus der Entwicklung gehört nicht in Git (ist ausgeschlossen).

## 7. Erster Test (Checkliste)

Rust, DPAPI, WIA und eSCL sind noch nicht auf echter Hardware geprüft. Bitte der Reihe nach:

- [ ] `cargo check` läuft ohne Fehler, `npm run tauri build` erzeugt den Installer.
- [ ] App startet, Titelleiste zeigt „Backend verbunden“.
- [ ] Der Epson DS-410 erscheint in der Scannerliste (Typ TWAIN).
- [ ] Simplex-Farbscan über den Einzug ergibt eine PDF mit allen Seiten.
- [ ] Duplex-Graustufenscan ergibt Vorder- und Rückseiten in der richtigen Reihenfolge.
- [ ] Gleicher Scan über WIA (anderen Zugang wählen bzw. TWAIN-Treiber deaktivieren).
- [ ] Papier im Einzug leer: verständliche Fehlermeldung, kein Absturz.
- [ ] Scanner abziehen und wieder anstecken: verschwindet und erscheint ohne App-Neustart.
- [ ] Paperless: „Verbindung testen“, dann Scan mit Upload.
- [ ] `config.json` in `%APPDATA%\Nospe` enthält den Token nicht im Klartext (`paperless_token_enc` mit Präfix `dpapi:v1:`).
- [ ] Nach dem Schließen der App läuft kein `nospe-backend.exe` mehr im Task-Manager.
- [ ] `%TEMP%` enthält nach einem abgebrochenen Scan kein `nospe-scan-*`-Verzeichnis.
- [ ] Optional Netzwerkscanner: erscheint als Typ „Netzwerk“, Scan funktioniert.

## 8. Fehlersuche

| Symptom | Ursache und Maßnahme |
|---------|----------------------|
| „Backend nicht erreichbar“ | Sidecar nicht gestartet: `nospe-backend.exe` fehlt im Installationsordner, Virenscanner blockiert die EXE, oder erster Start dauert (bis ca. 60 Sekunden). |
| Kein Scanner gefunden, TWAIN-Fehler im Log | DSM fehlt oder falsche Bitness: Abschnitt 1, [TWAIN_SETUP.md](TWAIN_SETUP.md). |
| Scanner nur über WIA, Einzug/Duplex fehlt | WIA-Treiber des Geräts kann es nicht: den TWAIN-Zugang (Epson Scan 2) verwenden. |
| Netzwerkscanner wird nicht gefunden | mDNS (UDP 5353) wird blockiert oder anderes Subnetz. Gerät muss `_uscan._tcp` melden (AirScan/Mopria). |
| „Die Paperless-URL zeigt auf einen anderen Server“ | Gewollt: Token für den neuen Server neu eingeben. |
| „Unverschlüsseltes http:// ist nur im lokalen Netz erlaubt“ | `https://` verwenden oder einen lokalen Hostnamen/eine private IP. |
| „In diesen Systemordner darf Nospe nicht speichern“ | Anderen Zielordner wählen. |
| „Es läuft bereits ein Scan“ | Es kann nur ein Scan gleichzeitig laufen; fertig werden lassen. |
| Entwicklung: Anfragen enden mit 401/403 | Secret oder Host stimmt nicht: Ablauf in [DEVELOPMENT.md](../DEVELOPMENT.md#sicherheitsmodell-der-lokalen-api). |
