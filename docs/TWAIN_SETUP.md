# TWAIN 64-bit Setup (Nospe Phase 0)

Nospe listet Scanner über **64-bit Python** und **pytwain** auf. Treiber, DSM und Python müssen dieselbe Bittiefe haben.

## Checkliste vor dem ersten echten Scan

1. **Windows 64-bit** mit installiertem **Epson Scan 2** (DS-410) oder **Nospe Virtual Scanner** (Emulator).
2. **64-bit Python** für das Backend (`uv run python -c "import struct; print(struct.calcsize('P')*8)"` → `64`).
3. **TWAIN-Quellen in 64-bit sichtbar** (TWACKER 64-bit oder Nospe-Verifikationsskript).
4. Optional Emulator: PDF auf Port 8766 laden, `NospeVirtualScanner.ds` nach `C:\Windows\twain_64\` kopieren.

## Verifikation (Phase 0)

Im Backend-Verzeichnis:

```powershell
cd backend
uv run python scripts/verify_twain.py
```

Exit-Code:

| Code | Bedeutung |
|------|-----------|
| 0 | 64-bit Windows, DSM lädt, mindestens eine TWAIN-Quelle |
| 1 | Allgemeiner Fehler (z. B. kein Windows) |
| 2 | Python ist nicht 64-bit |
| 3 | TWAIN DSM nicht ladbar (z. B. `TWAINDSM.dll` fehlt in System32) |
| 4 | DSM OK, aber **keine** Quellen (Treiber/Bitness prüfen) |

JSON-Ausgabe auf stdout für Automatisierung; Hinweise bei Problemen auf stderr.

## TWAIN DSM installieren (64-bit, offiziell)

**Das ist nicht der Scanner-Treiber.** Das DSM ist nur die Vermittler-DLL zwischen Nospe (pytwain) und den `.ds`-Treibern in `C:\Windows\twain_64\`.

SourceForge ist nur ein **alter Download-Spiegel** desselben Projekts. Offizielle Quelle heute:

**[twain/twain-dsm v2.5.1](https://github.com/twain/twain-dsm/releases/tag/v2.5.1)**

### Was du herunterlädst

| Asset | Brauchst du? |
|-------|----------------|
| **`dsm_020501.zip`** | **Ja** — enthält fertige Windows-DLLs |
| `twain-dsm-2.5.1.zip` | Nein (Quellcode + alte Release-Ordner, ~14 MB) |
| `twain-dsm-2.5.1.tar.gz` | Nein (Linux/Mac-Entwicklerpaket) |

In `dsm_020501.zip`:

```
dsm_020501/windows/64/TWAINDSM.dll   → 64-bit Apps (Nospe, pytwain)
dsm_020501/windows/32/TWAINDSM.dll   → nur für 32-bit Apps (optional)
```

### Installation (PowerShell als Administrator)

```powershell
$zip = "$env:TEMP\dsm_020501.zip"
Invoke-WebRequest -Uri "https://github.com/twain/twain-dsm/releases/download/v2.5.1/dsm_020501.zip" -OutFile $zip
Expand-Archive -Path $zip -DestinationPath "$env:TEMP\dsm_020501" -Force

# 64-bit DSM für Nospe (64-bit Python)
Copy-Item "$env:TEMP\dsm_020501\dsm_020501\windows\64\TWAINDSM.dll" `
  -Destination "$env:SystemRoot\System32\TWAINDSM.dll"

# Optional: 32-bit DSM für alte 32-bit Programme
Copy-Item "$env:TEMP\dsm_020501\dsm_020501\windows\32\TWAINDSM.dll" `
  -Destination "$env:SystemRoot\SysWOW64\TWAINDSM.dll"
```

pytwain lädt `twaindsm.dll` per Namen — unter Windows ist das dieselbe Datei wie `TWAINDSM.dll` (Groß-/Kleinschreibung egal).

Danach:

```powershell
cd backend
uv run python scripts/verify_twain.py
```

Exit-Code **3** sollte weg sein. Exit-Code **4** (keine Quellen) bedeutet: DSM OK, aber noch **kein Data Source** — dann Epson Scan 2 oder Nospe Virtual Scanner installieren (siehe unten).

Die `.msm`-Dateien im ZIP sind **Windows-Installer-Merge-Module** für Software-Hersteller; für Nospe reicht das manuelle Kopieren der DLL.

## Epson DS-410

- **Epson Scan 2** installieren (nicht nur die alte EPSON Scan-App).
- Laut Epson unterstützt Scan 2 für unterstützte Modelle **64-bit TWAIN**; DS-410 ist dabei.
- Nach Installation: Epson-Treiber in **64-bit TWACKER** sichtbar?

## Nospe Virtual Scanner (Test ohne Hardware)

1. Emulator: `uv run python run_emulator.py` → http://127.0.0.1:8766/emulator  
2. PDF hochladen.  
3. Native DS bauen und installieren (siehe [README.md](../README.md#twain-pdf-emulator)).  
4. `verify_twain.py` sollte `Nospe Virtual Scanner` in der Quellenliste zeigen.

## Häufige Probleme

| Symptom | Ursache | Maßnahme |
|---------|---------|----------|
| Leere Quellenliste, 64-bit Python | Nur 32-bit TWAIN-Treiber | Epson Scan 2 (64-bit) neu installieren |
| `SMLoadFileFailed` / DSM nicht ladbar | 64-bit `TWAINDSM.dll` fehlt in `System32` | [twain-dsm v2.5.1](https://github.com/twain/twain-dsm/releases/tag/v2.5.1) → `dsm_020501.zip` |
| DSM OK, aber 0 Quellen | Kein `.ds`-Treiber in `twain_64` | Epson Scan 2 oder `NospeVirtualScanner.ds` installieren |
| Quellen in TWACKER 32-bit, nicht in 64-bit | Bitness-Mismatch | 64-bit Treiberpaket verwenden |
| Backend zeigt 0 Scanner, verify OK | Backend nicht neu gestartet | `uv run python run_backend.py` neu starten |

## API (Phase 1)

- `GET /scanners` — echte TWAIN-`ProductName`-Liste (kein Mock mehr, wenn Backend läuft).
- `GET /scanners/status` — Bitness, DSM, `source_count`, Fehler, Hinweise.
- `POST /scan` — TWAIN-Scan → PDF im Zielordner; Nospe Virtual Scanner nutzt bei TWAIN-Fehler den Emulator-Spool.

### Virtual Scanner testen

1. `uv run python run_emulator.py` → PDF auf http://127.0.0.1:8766/emulator laden  
2. `uv run python run_backend.py` → Nospe-UI: **Nospe Virtual Scanner** + Scan  
3. Nach `.ds`-Update: `cmake --build twain_ds/build --config Release` und `NospeVirtualScanner.ds` nach `C:\Windows\twain_64\` kopieren  
4. Nur Spool (ohne TWAIN): Umgebungsvariable `NOSPE_EMULATOR_DIRECT_SCAN=1` beim Backend-Start
