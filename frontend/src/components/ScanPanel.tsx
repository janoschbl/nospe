import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import {
  CalendarClock,
  Check,
  CornerDownLeft,
  FileText,
  FlipVertical2,
  FolderOpen,
  Loader2,
  ScanLine,
  UploadCloud,
  Wand2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group";
import { cn } from "@/lib/utils";

import type {
  ImageType,
  LogEntry,
  Rotation,
  ScanOptions,
  ScanProfile,
  ScanRequest,
  ScanResponse,
  Scanner,
} from "../types";

const SCANNER_KIND_LABEL: Record<Scanner["kind"], string> = {
  twain: "TWAIN",
  wia: "WIA",
  escl: "Netzwerk",
};

/** Veraltete TWAIN-Setup-Hinweise nicht als Hauptstatus zeigen, wenn Scanner schon da sind. */
function isStaleTwainSetupLog(
  entry: LogEntry,
  backendState: ScanPanelProps["backendState"],
  scannerCount: number,
): boolean {
  if (backendState !== "online" || scannerCount === 0) {
    return false;
  }
  const m = entry.message.toLowerCase();
  return (
    entry.level === "warn" &&
    (m.includes("verify_twain") ||
      m.includes("twacker") ||
      m.includes("twain_setup") ||
      m.includes("kein twain-scanner"))
  );
}

type ScanPanelProps = {
  scannerId: string;
  scanners: Scanner[];
  scannerName: string;
  scannerReady: boolean;
  backendState: "checking" | "online" | "offline";
  profiles: ScanProfile[];
  profileId: string;
  defaultOutputDir: string;
  paperlessConfigured: boolean;
  onScan: (request: ScanRequest) => Promise<ScanResponse>;
  onScannerChange: (id: string) => void;
  onOpenSettings: () => void;
  onOutputDirChange: (dir: string) => void;
  onStatusMessage?: (message: string) => void;
  lastScan: ScanResponse | null;
  recentLog: LogEntry | null;
};

type ScanPhase =
  | "idle"
  | "starting"
  | "scanning"
  | "building"
  | "uploading"
  | "done"
  | "error";

const PHASE_TEXT: Record<ScanPhase, string> = {
  idle: "Bereit zum Scannen",
  starting: "Scanner starten…",
  scanning: "Seiten einlesen…",
  building: "PDF erstellen…",
  uploading: "Upload zu Paperless…",
  done: "Scan gespeichert",
  error: "Fehler",
};

const PHASE_PROGRESS: Record<ScanPhase, number> = {
  idle: 0,
  starting: 12,
  scanning: 45,
  building: 72,
  uploading: 90,
  done: 100,
  error: 100,
};

const BUSY: ScanPhase[] = ["starting", "scanning", "building", "uploading"];

const FORMAT_EXT: Record<ScanOptions["format"], string> = {
  pdf: "pdf",
  pdf_a: "pdf",
  jpeg: "jpg",
  png: "png",
  webp: "webp",
};

const FIELD_CONTROL_CLASS =
  "h-11 rounded-lg border border-input bg-background px-3 text-[13.5px] font-medium shadow-xs";

const FIELD_LEADING_ICON_CLASS =
  "grid size-7 shrink-0 place-items-center rounded-md bg-primary/[0.08] text-primary";

const SELECT_VALUE_CLASS =
  "min-w-0 flex-1 truncate text-left text-[13.5px] font-medium leading-tight text-foreground tabular-nums";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

const pad = (n: number) => String(n).padStart(2, "0");

function timestamp(d = new Date()): string {
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `_${pad(d.getHours())}-${pad(d.getMinutes())}-${pad(d.getSeconds())}`
  );
}

// Endgültigen Dateinamen aus Wunschname + optionalem Zeitstempel bauen.
function buildName(title: string, append: boolean, stamp: string): string {
  const base = title.trim();
  if (base && append) return `${base}_${stamp}`;
  if (base) return base;
  if (append) return stamp;
  return "";
}

export default function ScanPanel({
  scannerId,
  scanners,
  scannerName,
  scannerReady,
  backendState,
  profiles,
  profileId,
  defaultOutputDir,
  paperlessConfigured,
  onScan,
  onScannerChange,
  onOpenSettings,
  onOutputDirChange,
  onStatusMessage,
  lastScan,
  recentLog,
}: ScanPanelProps) {
  const [title, setTitle] = useState("");
  const [appendDateTime, setAppendDateTime] = useState(true);
  const [pushToPaperless, setPushToPaperless] = useState(false);

  const [options, setOptions] = useState<ScanOptions>({
    source: "adf_duplex",
    size: "auto",
    imageType: "color",
    resolution: 300,
    rotation: 0,
    mirrorVertical: false,
    correctSkew: true,
    editAfterScan: false,
    format: "pdf",
    outputDir: defaultOutputDir,
  });

  const [phase, setPhase] = useState<ScanPhase>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [, setClock] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setClock(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  // Profil steuert Quelle + Auflösung. Der Farbmodus bleibt bewusst eine
  // freie Nutzerentscheidung mit Default „Farbe“.
  useEffect(() => {
    const profile = profiles.find((p) => p.id === profileId);
    if (!profile) return;
    setOptions((prev) => ({
      ...prev,
      resolution: ([150, 200, 300, 400, 600].includes(profile.dpi)
        ? profile.dpi
        : 300) as ScanOptions["resolution"],
      source: profile.adf
        ? profile.duplex
          ? "adf_duplex"
          : "adf_simplex"
        : "flatbed",
    }));
  }, [profileId, profiles]);

  useEffect(() => {
    setOptions((prev) => ({ ...prev, outputDir: defaultOutputDir }));
  }, [defaultOutputDir]);

  // Paperless-Upload nur anbieten, wenn URL + Token hinterlegt sind.
  useEffect(() => {
    setPushToPaperless(paperlessConfigured);
  }, [paperlessConfigured]);

  const busy = BUSY.includes(phase);
  const canScan = scannerReady && Boolean(profileId) && !busy;
  const folder = options.outputDir || defaultOutputDir;

  const update = <K extends keyof ScanOptions>(k: K, v: ScanOptions[K]) =>
    setOptions((p) => ({ ...p, [k]: v }));

  function announce(message: string) {
    onStatusMessage?.(message);
  }

  async function handleSelectFolder() {
    try {
      const selected = await openDialog({
        directory: true,
        multiple: false,
        defaultPath: folder || undefined,
        title: "Zielordner wählen",
      });
      if (typeof selected !== "string" || !selected.trim()) return;
      const dir = selected.trim();
      update("outputDir", dir);
      onOutputDirChange(dir);
      announce(`Zielordner: ${dir}`);
    } catch (error) {
      const message = error instanceof Error
        ? error.message
        : "Ordner konnte nicht geöffnet werden.";
      toast.error(message);
    }
  }

  async function handleScan() {
    if (!canScan) return;
    setErrorMsg(null);

    const finalName = buildName(title, appendDateTime, timestamp());
    const request: ScanRequest = {
      scanner_id: scannerId,
      profile_id: profileId,
      title: finalName,
      color_mode: options.imageType,
      push_to_paperless: pushToPaperless,
    };

    try {
      setPhase("starting");
      await sleep(280);
      setPhase("scanning");
      await sleep(520);
      setPhase("building");
      await sleep(360);
      if (pushToPaperless) {
        setPhase("uploading");
        await sleep(360);
      }

      const result = await onScan(request);
      if (!result.ok) {
        setPhase("error");
        setErrorMsg("Scan fehlgeschlagen. Scanner prüfen und erneut versuchen.");
        return;
      }
      setPhase("done");
      window.setTimeout(() => setPhase("idle"), 3200);
    } catch (error) {
      setPhase("error");
      setErrorMsg(error instanceof Error ? error.message : "Unbekannter Fehler");
    }
  }

  // Enter im Formular und Strg/Cmd+Enter global starten den Scan.
  const canScanRef = useRef(canScan);
  canScanRef.current = canScan;
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && canScanRef.current) {
        e.preventDefault();
        void handleScan();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const progress = PHASE_PROGRESS[phase];
  const showProgress = busy;
  const shownToasts = useRef(new Set<string>());

  useEffect(() => {
    if (phase === "starting") {
      shownToasts.current.clear();
    }
  }, [phase]);

  useEffect(() => {
    if (phase !== "error" || !errorMsg) return;
    const key = `err:${errorMsg}`;
    if (shownToasts.current.has(key)) return;
    shownToasts.current.add(key);
    toast.error(errorMsg);
  }, [phase, errorMsg]);

  useEffect(() => {
    if (phase !== "done" || !lastScan?.file_path) return;
    const key = `done:${lastScan.file_path}:${lastScan.paperless_document_id ?? ""}:${lastScan.paperless_error ?? ""}`;
    if (shownToasts.current.has(key)) return;
    shownToasts.current.add(key);

    const path = compactPath(lastScan.file_path);
    const upload = paperlessResultLine(lastScan);
    if (upload?.kind === "warn") {
      toast.success(`PDF gespeichert\n${path}`);
      toast(upload.text, {
        icon: "⚠️",
        style: { borderColor: "var(--warning)" },
        duration: 6000,
      });
      return;
    }
    const lines = ["PDF gespeichert", path];
    if (upload?.text) lines.push(upload.text);
    toast.success(lines.join("\n"));
  }, [phase, lastScan]);

  useEffect(() => {
    if (!recentLog) return;
    if (phase !== "idle") return;
    if (recentLog.level !== "error" && recentLog.level !== "warn") return;
    if (isStaleTwainSetupLog(recentLog, backendState, scanners.length)) return;
    if (
      lastScan?.paperless_error &&
      recentLog.message.includes(lastScan.paperless_error)
    ) {
      return;
    }
    const key = `log:${recentLog.id}`;
    if (shownToasts.current.has(key)) return;
    shownToasts.current.add(key);
    if (recentLog.level === "error") {
      toast.error(recentLog.message);
    } else {
      toast(recentLog.message, {
        icon: "⚠️",
        style: { borderColor: "var(--warning)" },
        duration: 5500,
      });
    }
  }, [recentLog, phase, lastScan, backendState, scanners.length]);

  const previewName =
    buildName(title, appendDateTime, timestamp()) || "scan";
  const previewFile = `${previewName}.${FORMAT_EXT[options.format]}`;

  const liveMessage =
    busy
      ? PHASE_TEXT[phase]
      : phase === "error" && errorMsg
        ? errorMsg
        : PHASE_TEXT.idle;

  return (
    <form
      className="flex flex-1 flex-col"
      onSubmit={(e) => {
        e.preventDefault();
        void handleScan();
      }}
    >
      <p className="sr-only" role="status" aria-live="polite">
        {liveMessage}
      </p>

      <div className="mx-5 mt-3">
        <ScannerDropdown
          scannerId={scannerId}
          scanners={scanners}
          scannerName={scannerName}
          backendState={backendState}
          disabled={busy || scanners.length === 0}
          onChange={onScannerChange}
        />
      </div>

      <FormatSelectCard
        value={options.format}
        disabled={busy}
        onChange={(value) => update("format", value)}
      />

      {/* Controls */}
      <div className="grid grid-cols-1 gap-3 px-5 pb-3 pt-2.5">
        {/* Filename with optional date+time stamp */}
        <Field label="Dateiname" htmlFor="scan-title">
          <Input
            id="scan-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="z. B. Rechnung Stadtwerke"
            disabled={busy}
            autoComplete="off"
          />
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <p
              className="min-w-[10rem] flex-1 truncate text-[11.5px] text-muted-foreground tabular-nums"
              title={previewFile}
            >
              <span className="text-muted-foreground/70">Speichert als </span>
              {previewFile}
            </p>
            <CheckChip
              checked={appendDateTime}
              onChange={setAppendDateTime}
              disabled={busy}
              icon={<CalendarClock />}
              label="Datum & Uhrzeit"
            />
          </div>
        </Field>

        <Field label="Zielordner">
          <button
            type="button"
            onClick={() => void handleSelectFolder()}
            disabled={busy}
            title={folder || "Ordner wählen"}
            className={cn(
              FIELD_CONTROL_CLASS,
              "group flex w-full items-center gap-3 text-left transition-colors",
              "hover:border-ring/60 hover:bg-secondary/40",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background",
              "disabled:cursor-not-allowed disabled:opacity-60",
            )}
          >
            <span className="grid size-7 shrink-0 place-items-center rounded-md bg-primary/[0.08] text-primary">
              <FolderOpen className="size-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[13.5px] font-medium leading-tight text-foreground tabular-nums">
                {compactPath(folder) || "Ordner wählen…"}
              </span>
              <span className="block truncate text-[11px] leading-tight text-muted-foreground">
                {folder ? "Zum Ändern klicken" : "Noch kein Ziel gewählt"}
              </span>
            </span>
            <span className="shrink-0 text-[11.5px] font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
              Durchsuchen
            </span>
          </button>
        </Field>

        {/* Mode + rotation */}
        <div className="grid grid-cols-1 gap-3">
          <Field label="Modus">
            <ToggleGroup
              type="single"
              value={options.imageType}
              onValueChange={(v) => {
                if (v) update("imageType", v as ImageType);
              }}
              aria-label="Farbmodus"
              disabled={busy}
            >
              <ToggleGroupItem
                value="gray"
                className="data-[state=on]:bg-primary data-[state=on]:text-primary-foreground data-[state=on]:shadow-sm"
              >
                <ModeChoice kind="gray" label="Grau" />
              </ToggleGroupItem>
              <ToggleGroupItem
                value="color"
                className="data-[state=on]:bg-primary data-[state=on]:text-primary-foreground data-[state=on]:shadow-sm"
              >
                <ModeChoice kind="color" label="Farbe" />
              </ToggleGroupItem>
              <ToggleGroupItem
                value="bw"
                className="data-[state=on]:bg-primary data-[state=on]:text-primary-foreground data-[state=on]:shadow-sm"
              >
                <ModeChoice kind="bw" label="S/W" />
              </ToggleGroupItem>
            </ToggleGroup>
          </Field>
          <Field label="Drehung">
            <ToggleGroup
              type="single"
              value={String(options.rotation)}
              onValueChange={(v) => {
                if (v) update("rotation", Number(v) as Rotation);
              }}
              aria-label="Drehung"
              disabled={busy}
            >
              <ToggleGroupItem value="0" className="data-[state=on]:bg-primary data-[state=on]:text-primary-foreground data-[state=on]:shadow-sm">
                0°
              </ToggleGroupItem>
              <ToggleGroupItem value="90" className="data-[state=on]:bg-primary data-[state=on]:text-primary-foreground data-[state=on]:shadow-sm">
                90°
              </ToggleGroupItem>
              <ToggleGroupItem value="180" className="data-[state=on]:bg-primary data-[state=on]:text-primary-foreground data-[state=on]:shadow-sm">
                180°
              </ToggleGroupItem>
              <ToggleGroupItem value="270" className="data-[state=on]:bg-primary data-[state=on]:text-primary-foreground data-[state=on]:shadow-sm">
                270°
              </ToggleGroupItem>
            </ToggleGroup>
          </Field>
        </div>

        {/* Option toggles */}
        <div className="space-y-2">
          <Label className="block pl-0.5">Optionen</Label>
          <div className="grid grid-cols-2 gap-2.5">
            <OptionToggle
              icon={<FlipVertical2 />}
              label="Vertikal spiegeln"
              title="Seiten vertikal spiegeln."
              checked={options.mirrorVertical}
              onChange={(v) => update("mirrorVertical", v)}
              disabled={busy}
            />
            <OptionToggle
              icon={<Wand2 />}
              label="Entzerren"
              title="Schiefe Seiten beim Scannen automatisch gerade ausrichten."
              checked={options.correctSkew}
              onChange={(v) => update("correctSkew", v)}
              disabled={busy}
            />
          </div>
          <PaperlessToggle
            checked={pushToPaperless}
            onChange={setPushToPaperless}
            disabled={busy || !paperlessConfigured}
            configured={paperlessConfigured}
            onConfigure={onOpenSettings}
          />
        </div>
      </div>

      {/* Action bar */}
      <div className="mt-auto border-t border-border bg-secondary/30 px-5 py-3">
        <div
          className="mb-2.5 h-[3px] overflow-hidden rounded-full bg-secondary"
          role="progressbar"
          aria-valuenow={showProgress ? progress : 0}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-hidden={!showProgress}
        >
          <div
            className="h-full rounded-full bg-primary transition-[width,opacity] duration-300"
            style={{
              width: `${showProgress ? progress : 0}%`,
              opacity: showProgress ? 1 : 0,
            }}
          />
        </div>
        <Button
          type="submit"
          disabled={!canScan}
          className="w-full text-[14px] font-semibold"
          size="default"
        >
          {busy ? <Loader2 className="animate-spin" /> : <ScanLine />}
          <span>Scannen</span>
          <kbd className="ml-1 inline-flex items-center gap-0.5 rounded border border-primary-foreground/25 px-1.5 py-0.5 text-[10.5px] font-normal text-primary-foreground/75">
            Enter
            <CornerDownLeft className="size-3" aria-hidden />
          </kbd>
        </Button>

        {/* Centered hints below the button */}
        {!canScan && !busy && (
          <p className="mt-2.5 text-center text-[12px] text-muted-foreground">
            {!scannerReady
              ? "Kein Scanner verbunden — Gerät anschließen oder neu laden."
              : "Profil in den Einstellungen wählen, um zu scannen."}
          </p>
        )}
      </div>

    </form>
  );
}

function paperlessResultLine(
  scan: ScanResponse,
): { text: string; kind: "ok" | "warn" } | null {
  if (scan.paperless_error) {
    return {
      text: `Paperless-Upload fehlgeschlagen: ${scan.paperless_error}`,
      kind: "warn",
    };
  }
  if (scan.uploaded_to_paperless) {
    return {
      text: `Zu Paperless hochgeladen${
        scan.paperless_document_id ? ` (#${scan.paperless_document_id})` : ""
      }`,
      kind: "ok",
    };
  }
  return null;
}

function CheckChip({
  checked,
  onChange,
  disabled,
  icon,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      disabled={disabled}
      className={cn(
        "inline-flex shrink-0 items-center gap-2 rounded-full border py-1 pl-1 pr-3 text-[12px] font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background",
        "disabled:cursor-not-allowed disabled:opacity-50",
        checked
          ? "border-primary/40 bg-primary/[0.07] text-primary"
          : "border-border bg-background text-muted-foreground hover:border-ring/60 hover:text-foreground",
      )}
    >
      <span
        className={cn(
          "grid size-[18px] place-items-center rounded-full border transition-colors [&_svg]:size-3",
          checked
            ? "border-primary bg-primary text-primary-foreground"
            : "border-input bg-card text-transparent",
        )}
        aria-hidden
      >
        <Check />
      </span>
      <span className="inline-flex items-center gap-1.5 [&_svg]:size-3.5">
        {icon}
        {label}
      </span>
    </button>
  );
}

function ScannerDropdown({
  scannerId,
  scanners,
  scannerName,
  backendState,
  disabled,
  onChange,
}: {
  scannerId: string;
  scanners: Scanner[];
  scannerName: string;
  backendState: "checking" | "online" | "offline";
  disabled?: boolean;
  onChange: (id: string) => void;
}) {
  return (
    <Field label="Scanner">
      <Select value={scannerId} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger className={cn(FIELD_CONTROL_CLASS, "gap-3 py-0")}>
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <span className={FIELD_LEADING_ICON_CLASS}>
              <ScanLine className="size-4" aria-hidden />
            </span>
            <span className={SELECT_VALUE_CLASS}>
              <SelectValue
                placeholder={
                  backendState === "checking"
                    ? "Verbinde…"
                    : backendState === "online"
                      ? "Kein Scanner gefunden"
                      : "Kein Scanner"
                }
              />
            </span>
          </div>
        </SelectTrigger>
        <SelectContent>
          {scanners.map((scanner) => (
            <SelectItem key={scanner.id} value={scanner.id}>
              {scanner.name}
              <span className="ml-2 text-xs text-muted-foreground">{SCANNER_KIND_LABEL[scanner.kind]}</span>
            </SelectItem>
          ))}
          {scanners.length === 0 && (
            <SelectItem value="none" disabled>
              {scannerName}
            </SelectItem>
          )}
        </SelectContent>
      </Select>
    </Field>
  );
}

function PaperlessToggle({
  checked,
  onChange,
  disabled,
  configured,
  onConfigure,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
  configured: boolean;
  onConfigure: () => void;
}) {
  const active = configured && checked;
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3 rounded-lg border px-3 py-2 transition-colors",
        active
          ? "border-primary/40 bg-primary/[0.05]"
          : "border-border bg-secondary/25",
      )}
    >
      <div className="min-w-0">
        <p className="flex items-center gap-1.5 text-[12.5px] font-medium text-foreground">
          <UploadCloud className="size-3.5 text-primary" aria-hidden />
          Paperless
        </p>
        <p className="truncate text-[11px] text-muted-foreground">
          {configured ? "Scan zusätzlich hochladen" : "In Einstellungen einrichten"}
        </p>
      </div>
      {configured ? (
        <Switch
          checked={checked}
          onCheckedChange={onChange}
          disabled={disabled}
          aria-label="Paperless-Upload"
        />
      ) : (
        <button
          type="button"
          onClick={onConfigure}
          className="shrink-0 text-[12px] font-medium text-primary underline-offset-2 hover:underline"
        >
          Einrichten
        </button>
      )}
    </div>
  );
}

function FormatSelectCard({
  value,
  disabled,
  onChange,
}: {
  value: ScanOptions["format"];
  disabled?: boolean;
  onChange: (value: ScanOptions["format"]) => void;
}) {
  return (
    <div className="mx-5 mb-0.5 mt-2.5">
      <Field label="Dateiformat">
        <Select
          value={value}
          onValueChange={(next) => onChange(next as ScanOptions["format"])}
          disabled={disabled}
        >
          <SelectTrigger className={cn(FIELD_CONTROL_CLASS, "gap-3 py-0")}>
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <span className={FIELD_LEADING_ICON_CLASS}>
                <FileText className="size-4" aria-hidden />
              </span>
              <span className={SELECT_VALUE_CLASS}>
                <SelectValue />
              </span>
            </div>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="pdf">PDF</SelectItem>
            <SelectItem value="pdf_a">PDF/A</SelectItem>
            <SelectItem value="jpeg">JPG</SelectItem>
            <SelectItem value="png">PNG</SelectItem>
            <SelectItem value="webp">WebP</SelectItem>
          </SelectContent>
        </Select>
      </Field>
    </div>
  );
}

function ModeChoice({
  kind,
  label,
}: {
  kind: "gray" | "color" | "bw";
  label: string;
}) {
  if (kind === "gray") {
    return (
      <span className="inline-flex items-center gap-1.5">
        <span className="size-3 rounded-full bg-slate-400" aria-hidden />
        {label}
      </span>
    );
  }
  if (kind === "color") {
    return (
      <span className="inline-flex items-center gap-1.5">
        <span className="inline-flex -space-x-1" aria-hidden>
          <span className="size-3 rounded-full bg-red-500" />
          <span className="size-3 rounded-full bg-emerald-500" />
          <span className="size-3 rounded-full bg-blue-500" />
        </span>
        <span>{label}</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="grid size-3 overflow-hidden rounded-full border border-border">
        <span className="bg-white" />
        <span className="bg-foreground" />
      </span>
      {label}
    </span>
  );
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <Label htmlFor={htmlFor} className="pl-0.5">
        {label}
      </Label>
      {children}
    </div>
  );
}

function OptionToggle({
  icon,
  label,
  title,
  checked,
  onChange,
  disabled,
  locked,
}: {
  icon: React.ReactNode;
  label: string;
  title?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  locked?: boolean;
}) {
  return (
    <label
      title={title}
      className={cn(
        "group flex h-11 min-w-0 cursor-pointer items-center gap-2.5 rounded-lg border border-input bg-background pl-3 pr-2 shadow-xs transition-colors",
        "hover:border-ring/60",
        checked && "border-primary/40 bg-primary/[0.05]",
        disabled && "cursor-not-allowed opacity-60",
        locked && "border-dashed",
      )}
    >
      <span
        className={cn(
          "flex shrink-0 items-center justify-center text-muted-foreground transition-colors [&_svg]:size-4",
          checked && "text-primary",
        )}
        aria-hidden
      >
        {icon}
      </span>
      <span
        className={cn(
          "min-w-0 flex-1 truncate text-[13.5px] font-medium leading-normal text-foreground/85",
          checked && "text-foreground",
        )}
      >
        {label}
      </span>
      <Switch
        checked={checked}
        onCheckedChange={onChange}
        disabled={disabled}
        aria-label={title ?? label}
        className="ml-0"
      />
    </label>
  );
}

function compactPath(p: string): string {
  if (!p) return "";
  const sep = p.includes("\\") ? "\\" : "/";
  const parts = p.split(sep).filter(Boolean);
  if (parts.length <= 2) return p;
  const tail = parts.slice(-2).join(sep);
  return `…${sep}${tail}`;
}
