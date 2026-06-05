export type Subtype =
  | "crude_oil"
  | "product"
  | "chemical"
  | "lng"
  | "lpg"
  | "other"
  | "unknown";

export const ALL_SUBTYPES: Subtype[] = [
  "crude_oil",
  "product",
  "chemical",
  "lng",
  "lpg",
  "other",
  "unknown",
];

export const SUBTYPE_LABEL: Record<Subtype, string> = {
  crude_oil: "Crude Oil",
  product: "Product",
  chemical: "Chemical",
  lng: "LNG",
  lpg: "LPG",
  other: "Other",
  unknown: "Unknown",
};

export interface Position {
  latitude: number;
  longitude: number;
  sog: number | null;
  cog: number | null;
  heading: number | null;
  nav_status: number | null;
  reported_at: string;
}

export interface VesselSummary {
  mmsi: number;
  imo: number | null;
  name: string | null;
  subtype: Subtype;
  ship_type: number;
  flag: string | null;
  length_m: number | null;
  width_m: number | null;
  dwt: number | null;
  design_draught_m: number | null;
  current_draught_m: number | null;
  estimated_cargo_tonnes: number | null;
  estimate_confidence: "high" | "medium" | "low" | "none";
  last_seen: string;
  last_position: Position | null;
}
