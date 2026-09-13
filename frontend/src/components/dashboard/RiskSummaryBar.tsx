"use client";

import { RISK_LEVEL_META, RISK_LEVEL_ORDER } from "@/lib/riskLevels";
import type { RiskLevel, VillageRisk } from "@/lib/types";

interface RiskSummaryBarProps {
  villages: VillageRisk[];
  activeFilter: RiskLevel | null;
  onFilterChange: (level: RiskLevel | null) => void;
  children?: React.ReactNode;
}

export default function RiskSummaryBar({ villages, activeFilter, onFilterChange, children }: RiskSummaryBarProps) {
  const counts = villages.reduce<Record<RiskLevel, number>>(
    (acc, v) => {
      acc[v.risk_level] += 1;
      return acc;
    },
    { normal: 0, watch: 0, warning: 0, severe: 0 }
  );

  return (
    <div
      className="flex items-center justify-between gap-3 px-4 md:px-6 py-3 shrink-0"
      style={{ borderBottom: "1px solid var(--border-color)", backgroundColor: "var(--bg-surface)" }}
    >
      <div className="flex gap-2 overflow-x-auto">
        {RISK_LEVEL_ORDER.slice()
          .reverse()
          .map((level) => {
            const meta = RISK_LEVEL_META[level];
            const isActive = activeFilter === level;
            return (
              <button
                key={level}
                type="button"
                onClick={() => onFilterChange(isActive ? null : level)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm shrink-0 cursor-pointer transition-colors"
                style={{
                  border: `1px solid ${isActive ? meta.color : "var(--border-color)"}`,
                  backgroundColor: isActive ? `color-mix(in srgb, ${meta.color} 15%, transparent)` : "transparent",
                }}
                aria-pressed={isActive}
                title={meta.description}
              >
                <span className="inline-block w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: meta.color }} />
                <span style={{ color: "var(--text-secondary)" }}>{meta.label}</span>
                <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
                  {counts[level]}
                </span>
              </button>
            );
          })}
      </div>
      {children && <div className="shrink-0">{children}</div>}
    </div>
  );
}
