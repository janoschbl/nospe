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
  Scanner,
  TwainStatusResponse,
} from "./types";

export const API_BASE_URL = "http://127.0.0.1:8765";
const DEFAULT_TIMEOUT_MS = 2500;

async function requestJson<T>(
  path: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
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

export async function getScanners(): Promise<Scanner[]> {
  const data = await requestJson<ScannersResponse>("/scanners");
  return data.scanners;
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
