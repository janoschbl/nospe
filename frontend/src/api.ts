import { invoke } from "@tauri-apps/api/core";

import type {
  AppSettings,
  HealthResponse,
  PaperlessTestResponse,
  ProfilesResponse,
  SaveSettingsRequest,
  ScanRequest,
  ScanResponse,
  ScannersResponse,
  ScanProfile,
  TwainStatusResponse,
} from "./types";

const DEFAULT_TIMEOUT_MS = 2500;
const TOKEN_HEADER = "X-Nospe-Token";

type BackendConfig = { baseUrl: string; secret: string };

let backendConfig: Promise<BackendConfig> | null = null;

/**
 * Port und Secret des Backends. In der App kommen sie von Tauri (pro Start
 * zufällig). Im reinen Vite-Dev-Server (ohne Tauri) aus VITE_NOSPE_API_URL und
 * VITE_NOSPE_API_SECRET, siehe DEVELOPMENT.md.
 */
function getBackendConfig(): Promise<BackendConfig> {
  if (!backendConfig) {
    const load =
      "__TAURI_INTERNALS__" in window
        ? invoke<BackendConfig>("backend_config")
        : Promise.resolve({
            baseUrl: import.meta.env.VITE_NOSPE_API_URL ?? "http://127.0.0.1:8765",
            secret: import.meta.env.VITE_NOSPE_API_SECRET ?? "",
          });
    backendConfig = load.catch((error) => {
      backendConfig = null; // Backend war noch nicht bereit → beim nächsten Aufruf neu versuchen
      throw error;
    });
  }
  return backendConfig;
}

async function requestJson<T>(
  path: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const config = await getBackendConfig();
    const response = await fetch(`${config.baseUrl}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        [TOKEN_HEADER]: config.secret,
        ...(init?.headers ?? {}),
      },
    });
    if (!response.ok) {
      let detail = "";
      try {
        const body = (await response.json()) as { detail?: unknown };
        detail = typeof body.detail === "string" ? body.detail : "";
      } catch {
        // Keep the status-only fallback for non-JSON proxy errors.
      }
      throw new Error(
        detail
          ? `Backend antwortet mit HTTP ${response.status}: ${detail}`
          : `Backend antwortet mit HTTP ${response.status}.`,
      );
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("Backend antwortet")) {
      throw error;
    }
    throw new Error("Backend nicht erreichbar.");
  } finally {
    clearTimeout(timer);
  }
}

export function getHealth() {
  return requestJson<HealthResponse>("/health");
}

/** Geräteliste aus dem Cache des Backends; `refresh` erzwingt eine neue Suche. */
export function getScanners(refresh = false) {
  return requestJson<ScannersResponse>(
    refresh ? "/scanners?refresh=true" : "/scanners",
    undefined,
    refresh ? 15000 : DEFAULT_TIMEOUT_MS,
  );
}

export function getTwainStatus() {
  return requestJson<TwainStatusResponse>("/scanners/status");
}

export async function getProfiles(): Promise<ScanProfile[]> {
  const data = await requestJson<ProfilesResponse>("/profiles");
  return data.profiles;
}

export function getSettings() {
  return requestJson<AppSettings>("/settings");
}

export function saveSettings(request: SaveSettingsRequest) {
  return requestJson<AppSettings>("/settings", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function scanDocument(request: ScanRequest) {
  return requestJson<ScanResponse>(
    "/scan",
    { method: "POST", body: JSON.stringify(request) },
    30000,
  );
}

export function testPaperlessConnection() {
  return requestJson<PaperlessTestResponse>("/paperless/test", {
    method: "POST",
    body: JSON.stringify({}),
  });
}
