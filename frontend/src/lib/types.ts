// Mirrors Backend/app/models/schemas.py exactly -- keep in sync with that file.

export type RiskLevel = "normal" | "watch" | "warning" | "severe";

export interface Village {
  id: number;
  external_id: string | null;
  name: string;
  district: string | null;
  state: string | null;
  latitude: number;
  longitude: number;
  elevation_m: number | null;
  slope_deg: number | null;
}

export interface Risk {
  village_id: number;
  village_name: string;
  risk_score: number;
  risk_level: RiskLevel;
  contributing_factors: Record<string, number>;
  timestamp: string;
}

// Village + its latest risk, merged client-side by village_id.
export interface VillageRisk extends Village {
  risk_score: number | null;
  risk_level: RiskLevel;
  contributing_factors: Record<string, number>;
  risk_timestamp: string | null;
}

// AlertOut has no village_name -- callers must resolve it via the villages list.
export interface Alert {
  id: number;
  village_id: number;
  risk_score: number;
  risk_level: RiskLevel;
  timestamp: string;
}

export interface SensorIngestPayload {
  village_id: number;
  soil_moisture?: number;
  rainfall_mm?: number;
  water_level_m?: number;
  source?: string;
  timestamp?: string;
}
