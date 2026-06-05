import { Position, Subtype, VesselSummary } from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL as string;

if (!BASE) {
  console.warn("VITE_API_BASE_URL is not set; API calls will fail.");
}

async function getJson<T>(path: string, params: Record<string, string | number | undefined> = {}): Promise<T> {
  const url = new URL(`${BASE}${path}`);
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) url.searchParams.set(k, String(v));
  }
  const res = await fetch(url.toString());
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} on ${path}`);
  }
  return (await res.json()) as T;
}

export function fetchLatestPositions(subtypes: Subtype[]): Promise<VesselSummary[]> {
  return getJson<VesselSummary[]>("/positions/latest", {
    subtype: subtypes.join(",") || undefined,
    limit: 1500,
  });
}

export function fetchVessel(mmsi: number): Promise<VesselSummary> {
  return getJson<VesselSummary>(`/vessels/${mmsi}`);
}

export function fetchTrack(mmsi: number, hours = 24): Promise<Position[]> {
  return getJson<Position[]>(`/vessels/${mmsi}/track`, { hours });
}
