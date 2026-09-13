import type { RiskLevel } from "./types";

interface RiskLevelMeta {
  // IMD's own colour-coded warning terminology (Green/Yellow/Orange/Red --
  // "Be Aware"/"Be Prepared"/"Take Action") so the label is instantly
  // recognizable to an Indian disaster-response audience instead of a raw
  // enum string like "watch". Colors match IMD's scheme too.
  label: string;
  description: string;
  color: string;
}

// Raw hex, not CSS var() references: these values also feed Leaflet
// CircleMarker pathOptions, which set actual SVG/canvas paint attributes
// internally rather than participating in the page's CSS cascade.
export const RISK_LEVEL_META: Record<RiskLevel, RiskLevelMeta> = {
  normal: {
    label: "Normal",
    description: "No warning — conditions normal.",
    color: "#22c55e",
  },
  watch: {
    label: "Be Aware",
    description: "Elevated risk — monitor conditions closely.",
    color: "#eab308",
  },
  warning: {
    label: "Be Prepared",
    description: "High risk — prepare for possible evacuation.",
    color: "#f97316",
  },
  severe: {
    label: "Take Action",
    description: "Severe risk — evacuate at-risk areas immediately.",
    color: "#ef4444",
  },
};

// Most severe first -- used for sorting the village list and summary bar.
export const RISK_LEVEL_ORDER: RiskLevel[] = ["severe", "warning", "watch", "normal"];
