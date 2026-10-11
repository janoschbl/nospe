import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Cloud,
  RefreshCw,
  ScanLine,
  Settings as SettingsIcon,
} from "lucide-react";

import {
  getHealth,
  getProfiles,
  getTwainStatus,
  getSettings,
  saveSettings,
  scanDocument,
  testPaperlessConnection,
} from "./api";
import type {
  AppSettings,
  LogEntry,
  LogLevel,
  SaveSettingsRequest,
  ScanProfile,
  ScanRequest,
  ScanResponse,
  Scanner,
} from "./types";

import AppToaster from "./components/AppToaster";
import ScanPanel from "./components/ScanPanel";
import SettingsSheet from "./components/SettingsSheet";
import { Button } from "@/components/ui/button";

function nowHHMMSS(): string {
  return new Date().toLocaleTimeString("de-DE", { hour12: false });
}

async function getHealthWithRetry() {
  let lastError: unknown;
  for (let attempt = 0; attempt < 5; attempt += 1) {
    try {
      return await getHealth();
    } catch (error) {
      lastError = error;
      if (attempt < 4) await new Promise((resolve) => setTimeout(resolve, 400));
    }
  }
  throw lastError;
}

export default function App() {
  const [status, setStatus] = useState<"checking" | "online" | "offline">("checking");
  const [version, setVersion] = useState<string>("");
  const [settingsOpen, setSettingsOpen] = useState(false);

  const [scanners, setScanners] = useState<Scanner[]>([]);
  const [profiles, setProfiles] = useState<ScanProfile[]>([]);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [profileId, setProfileId] = useState<string>("");
  const [scannerId, setScannerId] = useState<string>("");
  const [lastScan, setLastScan] = useState<ScanResponse | null>(null);

  const [log, setLog] = useState<LogEntry[]>([]);
  const logId = useRef(0);
  const [loading, setLoading] = useState(true);

  const addLog = useCallback((message: string, level: LogLevel = "info") => {
    setLog((prev) => {
      // Aufeinanderfolgende identische Meldungen nicht doppelt protokollieren
      // (z. B. "Backend verbunden" nach jedem Neuladen).
      if (prev.some((entry) => entry.message === message && entry.level === level)) {
        return prev;
      }
      const entry: LogEntry = {
        id: logId.current++,
        time: nowHHMMSS(),
        level,
        message,
      };
      return [...prev, entry].slice(-30);
    });
  }, []);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setStatus("checking");

    try {
      const health = await getHealthWithRetry();
      setStatus(health.ok ? "online" : "offline");
      setVersion(health.version);
      const [profilesRes, settingsRes, twainRes] =
        await Promise.all([getProfiles(), getSettings(), getTwainStatus()]);
      const scannersRes = twainRes.sources.map((name) => ({ id: name, name }));
      setScanners(scannersRes);
      setProfiles(profilesRes);
      setSettings(settingsRes);
      const fallbackScannerId =
        (settingsRes.selected_scanner_id && scannersRes.some(
          (scanner) => scanner.id === settingsRes.selected_scanner_id,
        )
          ? settingsRes.selected_scanner_id
          : scannersRes[0]?.id) ?? "";
      setScannerId((cur) => {
        if (cur && scannersRes.some((scanner) => scanner.id === cur)) return cur;
        return fallbackScannerId;
      });
      if (fallbackScannerId && settingsRes.selected_scanner_id !== fallbackScannerId) {
        void saveSettings({
          scan_output_dir: settingsRes.scan_output_dir,
          paperless_url: settingsRes.paperless_url,
          folder_favorites: settingsRes.folder_favorites,
          selected_scanner_id: fallbackScannerId,
        }).then(setSettings).catch((error) => {
          addLog(error instanceof Error ? error.message : "Scanner-Standard konnte nicht gespeichert werden.", "error");
        });
      }
      setProfileId((cur) => cur || profilesRes[0]?.id || "");
      addLog(`Backend verbunden v${health.version}`, "success");
      const tw = twainRes;
        if (tw.error) {
          addLog(`TWAIN: ${tw.error}`, "error");
        } else if (tw.source_count === 0) {
          addLog(
            "Kein TWAIN-Scanner (64-bit) — siehe docs/TWAIN_SETUP.md",
            "warn",
          );
        } else {
          addLog(`TWAIN: ${tw.source_count} Quelle(n) gefunden`, "success");
          setLog((prev) =>
            prev.filter(
              (e) =>
                e.level !== "warn" ||
                (!e.message.includes("verify_twain") &&
                  !e.message.includes("TWACKER") &&
                  !e.message.includes("TWAIN_SETUP") &&
                  !e.message.includes("Kein TWAIN-Scanner")),
            ),
          );
        }
        const hint = tw.hints[0];
        if (hint && tw.source_count === 0) {
          addLog(hint, "warn");
        }
    } catch (error) {
      setStatus("offline");
      setScanners([]);
      setProfiles([]);
      setSettings(null);
      addLog(error instanceof Error ? error.message : "Backend nicht erreichbar.", "error");
    }

    setLoading(false);
  }, [addLog]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const handleScan = useCallback(
    async (request: ScanRequest): Promise<ScanResponse> => {
      const result = await scanDocument(request);
      setLastScan(result);
      addLog("Scan gespeichert", "success");

      if (result.paperless_error) {
        addLog(`Paperless: ${result.paperless_error}`, "error");
      } else if (result.uploaded_to_paperless) {
        addLog(
          `Paperless #${result.paperless_document_id ?? "?"}`,
          "success",
        );
      }

      return result;
    },
    [addLog],
  );

  const handleSaveSettings = useCallback(
    async (request: SaveSettingsRequest): Promise<AppSettings> => {
      const result = await saveSettings(request);
      setSettings(result);
      addLog("Einstellungen gespeichert", "success");
      return result;
    },
    [addLog],
  );

  const handleScannerChange = useCallback(
    (nextScannerId: string) => {
      setScannerId(nextScannerId);
      if (!settings) return;
      void saveSettings({
        scan_output_dir: settings.scan_output_dir,
        paperless_url: settings.paperless_url,
        folder_favorites: settings.folder_favorites,
        selected_scanner_id: nextScannerId,
      }).then((updated) => setSettings(updated)).catch((error) => {
        addLog(error instanceof Error ? error.message : "Scanner-Auswahl konnte nicht gespeichert werden.", "error");
      });
    },
    [settings, addLog],
  );

  const handleSessionSettingsChange = useCallback(
    (request: SaveSettingsRequest) => {
      setSettings((current) => current ? {
        ...current,
        scan_output_dir: request.scan_output_dir,
        paperless_url: request.paperless_url,
        folder_favorites: request.folder_favorites ?? current.folder_favorites,
        selected_scanner_id: request.selected_scanner_id ?? current.selected_scanner_id,
      } : current);
    },
    [],
  );

  const handleOutputDirChange = useCallback(
    (dir: string) => {
      setSettings((current) => current ? { ...current, scan_output_dir: dir } : current);
    },
    [],
  );

  const handleTestPaperless = useCallback(async () => {
    const result = await testPaperlessConnection();
    return result;
  }, []);

  const effectiveScannerId = scanners.some((scanner) => scanner.id === scannerId)
    ? scannerId
    : scanners[0]?.id ?? "";

  const activeScanner =
    scanners.find((s) => s.id === effectiveScannerId)?.name ??
    (scanners.length === 0
      ? status === "online"
        ? "Kein TWAIN-Scanner (64-bit)"
        : "Kein Scanner"
      : "Scanner");

  const scannerReady = scanners.length > 0 && Boolean(effectiveScannerId);

  const paperlessConfigured = useMemo(
    () =>
      Boolean(settings?.paperless_url?.trim()) &&
      Boolean(settings?.paperless_token_set),
    [settings],
  );

  const backendState: "online" | "offline" | "checking" = status;

  return (
    <div className="flex min-h-screen w-full justify-center bg-background">
      <AppToaster />
      {/* App window — a deliberate compact column, not a full-bleed web page */}
      <div className="flex w-full max-w-[590px] flex-col overflow-hidden border-border bg-card sm:border-x sm:shadow-[0_0_40px_-20px_oklch(0.21_0.02_260/0.25)]">
        {/* Title bar */}
        <header className="flex items-center justify-between gap-3 border-b border-border bg-card px-5 py-3.5">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-primary text-primary-foreground shadow-sm">
              <ScanLine className="size-4.5" aria-hidden />
            </span>
            <div className="min-w-0">
              <h1 className="text-[17px] font-semibold leading-none tracking-tight">
                Nospe
              </h1>
              <p className="mt-1 text-[11.5px] leading-none text-muted-foreground">
                {backendState === "checking"
                  ? "Verbinde…"
                  : backendState === "online"
                    ? "Bereit"
                    : "Offline"}
              </p>
            </div>
          </div>

          <div className="flex min-w-0 items-center gap-1">
            <button
              type="button"
              onClick={() => setSettingsOpen(true)}
              className="relative grid h-8 w-8 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              title={
                paperlessConfigured
                  ? "Paperless ist bereit"
                  : "Paperless ist nicht eingerichtet"
              }
              aria-label={
                paperlessConfigured
                  ? "Paperless ist bereit"
                  : "Paperless ist nicht eingerichtet"
              }
            >
              <Cloud className="size-4" aria-hidden />
              <span
                className={`absolute right-1.5 top-1.5 size-2 rounded-full border border-card ${
                  paperlessConfigured ? "bg-success" : "bg-muted-foreground/50"
                }`}
                aria-hidden
              />
            </button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => void loadAll()}
              disabled={loading}
              title="Geräte neu laden"
              aria-label="Geräte neu laden"
            >
              <RefreshCw className={loading ? "animate-spin" : ""} />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setSettingsOpen(true)}
              title="Einstellungen"
              aria-label="Einstellungen öffnen"
            >
              <SettingsIcon />
            </Button>
          </div>
        </header>

        <main className="flex flex-1 flex-col bg-card">
          <ScanPanel
            scannerId={effectiveScannerId}
            scanners={scanners}
            scannerName={activeScanner}
            scannerReady={scannerReady}
            backendState={backendState}
            profiles={profiles}
            profileId={profileId}
            onScannerChange={handleScannerChange}
            defaultOutputDir={settings?.scan_output_dir ?? ""}
            paperlessConfigured={paperlessConfigured}
            onScan={handleScan}
            onOpenSettings={() => setSettingsOpen(true)}
            onOutputDirChange={handleOutputDirChange}
            onStatusMessage={(m) => addLog(m)}
            lastScan={lastScan}
            recentLog={log.slice(-1)[0] ?? null}
          />
        </main>
      </div>

      {settings && (
        <SettingsSheet
          open={settingsOpen}
          onOpenChange={setSettingsOpen}
          settings={settings}
          profiles={profiles}
          profileId={profileId}
          onProfileChange={setProfileId}
          onSave={handleSaveSettings}
          onSessionChange={handleSessionSettingsChange}
          onTestPaperless={handleTestPaperless}
          onStatusMessage={(m) => addLog(m)}
          log={log}
          backendVersion={version}
        />
      )}
    </div>
  );
}
