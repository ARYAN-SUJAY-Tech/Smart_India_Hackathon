"use client";

import { X } from "lucide-react";
import { RISK_LEVEL_META } from "@/lib/riskLevels";
import type { VillageRisk } from "@/lib/types";

interface VillageDetailPanelProps {
  village: VillageRisk;
  onClose: () => void;
}

export default function VillageDetailPanel({ village, onClose }: VillageDetailPanelProps) {
  const meta = RISK_LEVEL_META[village.risk_level];
  const factors = Object.entries(village.contributing_factors);
  const maxFactor = Math.max(1e-6, ...factors.map(([, v]) => Math.abs(v)));

  return (
    <div
      className="absolute inset-y-0 right-0 w-full sm:w-96 z-1000 flex flex-col shadow-2xl"
      style={{ backgroundColor: "var(--bg-surface)", borderLeft: "1px solid var(--border-color)" }}
    >
      <div className="flex items-start justify-between gap-3 p-4" style={{ borderBottom: "1px solid var(--border-color)" }}>
        <div className="min-w-0">
          <h2 className="text-base font-semibold truncate" style={{ color: "var(--text-primary)" }}>
            {village.name}
          </h2>
          <p className="text-sm truncate" style={{ color: "var(--text-muted)" }}>
            {[village.district, village.state].filter(Boolean).join(", ") || "Unknown district"}
          </p>
        </div>
        <button
          onClick={onClose}
          className="cursor-pointer p-1 -m-1 shrink-0 rounded hover:opacity-70"
          style={{ color: "var(--text-muted)" }}
          aria-label="Close village detail"
        >
          <X size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div
          className="rounded-lg p-4"
          style={{ backgroundColor: "var(--bg-surface-raised)", border: `1px solid ${meta.color}` }}
        >
          <p className="text-xs uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            Current Risk
          </p>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold" style={{ color: meta.color }}>
              {meta.label}
            </span>
            {village.risk_score !== null && (
              <span className="text-sm font-mono" style={{ color: "var(--text-secondary)" }}>
                score {village.risk_score.toFixed(2)}
              </span>
            )}
          </div>
          <p className="text-sm mt-2" style={{ color: "var(--text-secondary)" }}>
            {meta.description}
          </p>
        </div>

        <div>
          <p className="text-sm font-medium mb-3" style={{ color: "var(--text-primary)" }}>
            Contributing Factors
          </p>
          {factors.length === 0 ? (
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              No sensor data yet for this village.
            </p>
          ) : (
            <div className="space-y-3">
              {factors.map(([key, value]) => (
                <div key={key}>
                  <div className="flex justify-between text-sm mb-1">
                    <span style={{ color: "var(--text-secondary)" }}>{key.replace(/_/g, " ")}</span>
                    <span className="font-mono" style={{ color: "var(--text-primary)" }}>
                      {value.toFixed(3)}
                    </span>
                  </div>
                  <div className="h-1.5 w-full rounded-full" style={{ backgroundColor: "var(--border-color)" }}>
                    <div
                      className="h-1.5 rounded-full"
                      style={{
                        width: `${Math.min(100, (Math.abs(value) / maxFactor) * 100)}%`,
                        backgroundColor: "var(--accent-primary)",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 pt-4" style={{ borderTop: "1px solid var(--border-color)" }}>
          <div>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Elevation
            </p>
            <p className="text-sm font-mono" style={{ color: "var(--text-primary)" }}>
              {village.elevation_m !== null ? `${village.elevation_m} m` : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Slope
            </p>
            <p className="text-sm font-mono" style={{ color: "var(--text-primary)" }}>
              {village.slope_deg !== null ? `${village.slope_deg}°` : "—"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
