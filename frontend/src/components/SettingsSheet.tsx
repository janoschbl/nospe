import { useEffect, useState } from "react";
import {
  Archive,
  BriefcaseBusiness,
  CheckCircle2,
  Folder,
  FolderCheck,
  HardDrive,
  Loader2,
  PlugZap,
  Plus,
  Save,
  Star,
  Trash2,
  XCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetBody,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

import type {
  AppSettings,
  FolderFavorite,
  FolderFavoriteIcon,
  LogEntry,
  PaperlessTestResponse,
  SaveSettingsRequest,
  ScanProfile,
} from "../types";

type SettingsSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  settings: AppSettings;
  profiles: ScanProfile[];
  profileId: string;
  onProfileChange: (id: string) => void;
  onSave: (request: SaveSettingsRequest) => Promise<AppSettings>;
  onSessionChange: (request: SaveSettingsRequest) => void;
  onTestPaperless: () => Promise<PaperlessTestResponse>;
  onStatusMessage?: (message: string) => void;
  log: LogEntry[];
  backendVersion: string;
};

type ActionState = "idle" | "busy" | "ok" | "error";

const RESOLUTIONS = ["150", "200", "300", "400", "600"] as const;
const SOURCES: { value: string; label: string }[] = [
  { value: "adf_simplex", label: "ADF einseitig" },
  { value: "adf_duplex", label: "ADF duplex" },
  { value: "flatbed", label: "Flachbett" },
];
const SIZES: { value: string; label: string }[] = [
  { value: "auto", label: "Automatisch" },
  { value: "a4", label: "A4" },
  { value: "a5", label: "A5" },
  { value: "letter", label: "Letter" },
  { value: "legal", label: "Legal" },
];
const FORMATS: { value: string; label: string }[] = [
  { value: "pdf", label: "PDF" },
  { value: "pdf_a", label: "PDF/A" },
  { value: "jpeg", label: "JPEG" },
  { value: "png", label: "PNG" },
  { value: "webp", label: "WebP" },
];

const FAVORITE_ICONS: { value: FolderFavoriteIcon; label: string }[] = [
  { value: "folder", label: "Ordner" },
  { value: "folder-check", label: "Standard" },
  { value: "briefcase", label: "Office" },
  { value: "archive", label: "Archiv" },
  { value: "star", label: "Favorit" },
  { value: "hard-drive", label: "Laufwerk" },
];

export default function SettingsSheet({
  open,
  onOpenChange,
  settings,
  profiles,
  profileId,
  onProfileChange,
  onSave,
  onSessionChange,
  onTestPaperless,
  onStatusMessage,
  log,
  backendVersion,
}: SettingsSheetProps) {
  const [outputDir, setOutputDir] = useState(settings.scan_output_dir);
  const [folderFavorites, setFolderFavorites] = useState<FolderFavorite[]>(
    settings.folder_favorites ?? [],
  );
  const [paperlessUrl, setPaperlessUrl] = useState(settings.paperless_url);
  const [token, setToken] = useState("");
  const [tokenSet, setTokenSet] = useState(settings.paperless_token_set);

  const [resolution, setResolution] = useState("300");
  const [source, setSource] = useState("adf_duplex");
  const [docSize, setDocSize] = useState("auto");
  const [format, setFormat] = useState("pdf");

  const [saveState, setSaveState] = useState<ActionState>("idle");
  const [testState, setTestState] = useState<ActionState>("idle");
  const [testMessage, setTestMessage] = useState<string | null>(null);

  useEffect(() => {
    setOutputDir(settings.scan_output_dir);
    setFolderFavorites(settings.folder_favorites ?? []);
    setPaperlessUrl(settings.paperless_url);
    setTokenSet(settings.paperless_token_set);
  }, [settings]);

  // Keep the running session in sync while the explicit Save button remains
  // the only durable persistence action.
  useEffect(() => {
    onSessionChange({
      scan_output_dir: outputDir,
      paperless_url: paperlessUrl,
      folder_favorites: cleanFavorites(folderFavorites),
    });
  }, [outputDir, paperlessUrl, folderFavorites, onSessionChange]);

  async function handleSave() {
    setSaveState("busy");
    const request: SaveSettingsRequest = {
      scan_output_dir: outputDir.trim(),
      paperless_url: paperlessUrl.trim(),
      folder_favorites: cleanFavorites(folderFavorites),
    };
    if (token.trim().length > 0) {
      request.paperless_token = token.trim();
    }
    try {
      const updated = await onSave(request);
      setFolderFavorites(updated.folder_favorites ?? []);
      setTokenSet(updated.paperless_token_set);
      setToken("");
      setSaveState("ok");
      onStatusMessage?.("Einstellungen gespeichert");
      window.setTimeout(() => setSaveState("idle"), 1800);
    } catch (error) {
      setSaveState("error");
      const msg = error instanceof Error ? error.message : "Fehler";
      onStatusMessage?.(`Speichern fehlgeschlagen: ${msg}`);
    }
  }

  async function handleTest() {
    setTestState("busy");
    setTestMessage(null);
    try {
      const result = await onTestPaperless();
      setTestState(result.ok ? "ok" : "error");
      setTestMessage(result.message);
      onStatusMessage?.(`Paperless: ${result.message}`);
    } catch (error) {
      setTestState("error");
      const msg = error instanceof Error ? error.message : "Fehler";
      setTestMessage(msg);
    }
  }

  const busy = saveState === "busy" || testState === "busy";

  function updateFavorite(
    id: string,
    field: keyof FolderFavorite,
    value: string,
  ) {
    setFolderFavorites((items) =>
      items.map((item) => (item.id === id ? { ...item, [field]: value } : item)),
    );
  }

  function notifySessionChange(patch: Partial<SaveSettingsRequest>) {
    onSessionChange({
      scan_output_dir: patch.scan_output_dir ?? outputDir,
      paperless_url: patch.paperless_url ?? paperlessUrl,
      folder_favorites: patch.folder_favorites ?? cleanFavorites(folderFavorites),
    });
  }

  function addFavoriteFromOutput() {
    const path = outputDir.trim();
    setFolderFavorites((items) => [
      ...items,
      {
        id: makeFavoriteId(),
        label: labelFromPath(path) || "Neuer Favorit",
        path,
        icon: "folder",
      },
    ]);
  }

  function removeFavorite(id: string) {
    setFolderFavorites((items) => items.filter((item) => item.id !== id));
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="p-0">
        <SheetHeader>
          <SheetTitle>Einstellungen</SheetTitle>
          <SheetDescription>
            Profil, Speicherort, Paperless und Protokoll.
          </SheetDescription>
        </SheetHeader>

        <SheetBody className="space-y-6">
          <Section title="Scan-Vorgaben">
            <FieldRow label="Profil">
              <Select
                value={profileId}
                onValueChange={onProfileChange}
                disabled={busy || profiles.length === 0}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Kein Profil" />
                </SelectTrigger>
                <SelectContent>
                  {profiles.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FieldRow>
            <FieldRow label="Quelle">
              <Select value={source} onValueChange={setSource} disabled={busy}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SOURCES.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FieldRow>
            <FieldRow label="Dokumentgröße">
              <Select value={docSize} onValueChange={setDocSize} disabled={busy}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SIZES.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FieldRow>
            <div className="grid grid-cols-2 gap-3">
              <FieldRow label="Auflösung">
                <Select
                  value={resolution}
                  onValueChange={setResolution}
                  disabled={busy}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {RESOLUTIONS.map((r) => (
                      <SelectItem key={r} value={r}>
                        {r} dpi
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FieldRow>
              <FieldRow label="Format">
                <Select value={format} onValueChange={setFormat} disabled={busy}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {FORMATS.map((f) => (
                      <SelectItem key={f.value} value={f.value}>
                        {f.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FieldRow>
            </div>
          </Section>

          <Section title="Speicherort">
            <FieldRow label="Ordner" htmlFor="set-output">
              <Input
                id="set-output"
                value={outputDir}
                onChange={(e) => {
                  const value = e.target.value;
                  setOutputDir(value);
                  notifySessionChange({ scan_output_dir: value });
                }}
                placeholder="C:\\Users\\…\\Scans"
                disabled={busy}
              />
            </FieldRow>
            <p className="text-[12px] text-muted-foreground">
              Das ist der Standard-Zielordner für neue Scans. Favoriten darunter
              sind Schnellzugriffe im Ordnerdialog.
            </p>
            <div className="space-y-2.5">
              <div className="flex items-center justify-between gap-2">
                <Label className="text-[12px]">Favoriten</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="xs"
                  onClick={addFavoriteFromOutput}
                  disabled={busy || !outputDir.trim()}
                >
                  <Plus />
                  Aktuellen Ordner merken
                </Button>
              </div>
              {folderFavorites.length === 0 ? (
                <p className="rounded-lg border border-dashed border-border bg-secondary/30 px-3 py-2 text-[12px] text-muted-foreground">
                  Keine eigenen Favoriten. Laufwerke bleiben im Ordnerdialog
                  trotzdem sichtbar.
                </p>
              ) : (
                <div className="space-y-2">
                  {folderFavorites.map((favorite) => (
                    <div
                      key={favorite.id}
                      className="rounded-lg border border-border bg-secondary/20 p-2"
                    >
                      <div className="grid grid-cols-[7.5rem_1fr_auto] gap-2">
                        <Select
                          value={favorite.icon}
                          onValueChange={(value) =>
                            updateFavorite(favorite.id, "icon", value)
                          }
                          disabled={busy}
                        >
                          <SelectTrigger className="h-8 text-[12px]">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {FAVORITE_ICONS.map((icon) => (
                              <SelectItem key={icon.value} value={icon.value}>
                                <span className="inline-flex items-center gap-2">
                                  <FavoriteIcon icon={icon.value} />
                                  {icon.label}
                                </span>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <Input
                          value={favorite.label}
                          onChange={(e) => {
                            const next = folderFavorites.map((item) =>
                              item.id === favorite.id ? { ...item, label: e.target.value } : item,
                            );
                            setFolderFavorites(next);
                            notifySessionChange({ folder_favorites: cleanFavorites(next) });
                          }}
                          placeholder="Name"
                          className="h-8"
                          disabled={busy}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => removeFavorite(favorite.id)}
                          disabled={busy}
                          aria-label={`${favorite.label || "Favorit"} entfernen`}
                        >
                          <Trash2 />
                        </Button>
                      </div>
                      <div className="mt-2 flex gap-2">
                        <Input
                          value={favorite.path}
                          onChange={(e) => {
                            const next = folderFavorites.map((item) =>
                              item.id === favorite.id ? { ...item, path: e.target.value } : item,
                            );
                            setFolderFavorites(next);
                            notifySessionChange({ folder_favorites: cleanFavorites(next) });
                          }}
                          placeholder="C:\\Pfad\\zum\\Ordner"
                          className="h-8 min-w-0 flex-1"
                          disabled={busy}
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="xs"
                          onClick={() => setOutputDir(favorite.path)}
                          disabled={busy || !favorite.path.trim()}
                        >
                          Als Standard
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Section>

          <Section title="Paperless">
            <p className="text-[12px] text-muted-foreground">
              URL und Token deiner Paperless-ngx-Instanz. Erst danach kann ein
              Scan automatisch hochgeladen werden.
            </p>
            <FieldRow label="URL" htmlFor="set-paperless-url">
              <Input
                id="set-paperless-url"
                type="url"
                value={paperlessUrl}
                onChange={(e) => {
                  const value = e.target.value;
                  setPaperlessUrl(value);
                  notifySessionChange({ paperless_url: value });
                }}
                placeholder="https://paperless.example.com"
                disabled={busy}
              />
            </FieldRow>
            <FieldRow label="Token" htmlFor="set-paperless-token">
              <Input
                id="set-paperless-token"
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder={tokenSet ? "Gespeichert — leer lassen" : "Token"}
                autoComplete="off"
                disabled={busy}
              />
            </FieldRow>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => void handleTest()}
                disabled={busy}
                className="flex-1"
              >
                {testState === "busy" ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <PlugZap />
                )}
                Verbindung testen
              </Button>
            </div>
            {testMessage && (
              <p
                className={cn(
                  "mt-1 flex items-center gap-1.5 text-[11.5px]",
                  testState === "ok" ? "text-success" : "text-destructive",
                )}
              >
                {testState === "ok" ? (
                  <CheckCircle2 className="size-3.5" />
                ) : (
                  <XCircle className="size-3.5" />
                )}
                {testMessage}
              </p>
            )}
          </Section>

          <Section title="Protokoll">
            {log.length === 0 ? (
              <p className="text-[12px] text-muted-foreground">
                Noch keine Ereignisse.
              </p>
            ) : (
              <ul
                className="max-h-44 space-y-px overflow-y-auto rounded-md border border-border bg-secondary/40 p-1.5 text-[11.5px]"
                aria-live="polite"
              >
                {[...log]
                  .reverse()
                  .slice(0, 14)
                  .map((entry) => (
                    <li
                      key={entry.id}
                      className="grid grid-cols-[auto_1fr] items-baseline gap-2 rounded-sm px-1.5 py-1"
                    >
                      <span className="font-mono text-[10.5px] text-muted-foreground">
                        {entry.time}
                      </span>
                      <span
                        className={cn(
                          "break-words text-foreground/80",
                          entry.level === "success" && "text-success",
                          entry.level === "warn" && "text-warning",
                          entry.level === "error" && "text-destructive",
                        )}
                      >
                        {entry.message}
                      </span>
                    </li>
                  ))}
              </ul>
            )}
          </Section>

          <Separator />

          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>Nospe</span>
            <span className="font-mono">v{backendVersion || "—"}</span>
          </div>
        </SheetBody>

        <SheetFooter>
          {saveState === "ok" && (
            <span className="mr-auto inline-flex items-center gap-1.5 text-[12px] text-success">
              <CheckCircle2 className="size-3.5" /> Gespeichert
            </span>
          )}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={busy}
          >
            Schließen
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={() => void handleSave()}
            disabled={busy}
          >
            {saveState === "busy" ? (
              <Loader2 className="animate-spin" />
            ) : (
              <Save />
            )}
            Speichern
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-2.5">
      <h3 className="border-b border-border pb-1.5 text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h3>
      <div className="space-y-2.5">{children}</div>
    </section>
  );
}

function FieldRow({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
    </div>
  );
}

function makeFavoriteId(): string {
  return `favorite-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 7)}`;
}

function labelFromPath(path: string): string {
  const parts = path.trim().replace(/[/\\]+$/, "").split(/[/\\]/).filter(Boolean);
  return parts.at(-1) ?? "";
}

function cleanFavorites(favorites: FolderFavorite[]): FolderFavorite[] {
  const seen = new Set<string>();
  return favorites
    .map((favorite) => {
      const path = favorite.path.trim();
      const label = favorite.label.trim() || labelFromPath(path) || path;
      return {
        ...favorite,
        label,
        path,
        icon: favorite.icon || "folder",
      };
    })
    .filter((favorite) => {
      if (!favorite.path || seen.has(favorite.path)) return false;
      seen.add(favorite.path);
      return true;
    });
}

function FavoriteIcon({ icon }: { icon: FolderFavoriteIcon }) {
  const className = "size-3.5 shrink-0";
  if (icon === "folder-check") {
    return <FolderCheck className={className} aria-hidden />;
  }
  if (icon === "briefcase") {
    return <BriefcaseBusiness className={className} aria-hidden />;
  }
  if (icon === "archive") {
    return <Archive className={className} aria-hidden />;
  }
  if (icon === "star") {
    return <Star className={className} aria-hidden />;
  }
  if (icon === "hard-drive") {
    return <HardDrive className={className} aria-hidden />;
  }
  return <Folder className={className} aria-hidden />;
}
