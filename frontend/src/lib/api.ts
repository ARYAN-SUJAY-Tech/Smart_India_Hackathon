import type { Alert, Risk, SensorIngestPayload, Village } from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function getVillages(): Promise<Village[]> {
  return apiFetch<Village[]>("/villages/");
}

export function getRisks(): Promise<Risk[]> {
  return apiFetch<Risk[]>("/risk/");
}

// Unlike GET /risk/ (bulk, used for the map poll), this endpoint also logs
// an AlertLog row server-side -- call it after a sensor submission so the
// alert timeline picks up the change immediately instead of waiting on
// whatever next hits the single-village endpoint.
export function getVillageRisk(villageId: number): Promise<Risk> {
  return apiFetch<Risk>(`/risk/${villageId}`);
}

export function getAlerts(limit = 50): Promise<Alert[]> {
  return apiFetch<Alert[]>(`/alerts/?limit=${limit}`);
}

export function ingestSensorReading(
  payload: SensorIngestPayload
): Promise<{ status: string; reading_id: number }> {
  return apiFetch("/sensor/ingest", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
