"use client";

import { RISK_LEVEL_META, RISK_LEVEL_ORDER } from "@/lib/riskLevels";
import type { VillageRisk } from "@/lib/types";

interface VillageListProps {
  villages: VillageRisk[];
  activeId: number | null;
  onSelect: (village: VillageRisk) => void;
}

export default function VillageList({ villages, activeId, onSelect }: VillageListProps) {
  const sorted = [...villages].sort((a, b) => {
    const levelDiff = RISK_LEVEL_ORDER.indexOf(a.risk_level) - RISK_LEVEL_ORDER.indexOf(b.risk_level);
    if (levelDiff !== 0) return levelDiff;
    return (b.risk_score ?? 0) - (a.risk_score ?? 0);
  });

  if (sorted.length === 0) {
    return (
      <p className="text-sm p-4" style={{ color: "var(--text-muted)" }}>
        No villages match this filter.
      </p>
    );
  }

  return (
    <ul className="divide-y" style={{ borderColor: "var(--border-color)" }}>
      {sorted.map((village) => {
        const meta = RISK_LEVEL_META[village.risk_level];
        const isActive = activeId === village.id;
        return (
          <li key={village.id}>
            <button
              type="button"
              onClick={() => onSelect(village)}
              className="w-full text-left px-4 py-3 flex items-center gap-3 cursor-pointer transition-colors"
              style={{
                backgroundColor: isActive ? "color-mix(in srgb, var(--accent-primary) 12%, transparent)" : "transparent",
                borderLeft: isActive ? "3px solid var(--accent-primary)" : "3px solid transparent",
              }}
            >
              <span className="inline-block w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: meta.color }} />
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
                  {village.name}
                </span>
                <span className="block text-xs truncate" style={{ color: "var(--text-muted)" }}>
                  {[village.district, village.state].filter(Boolean).join(", ") || "Unknown district"}
                </span>
              </span>
              <span className="text-right shrink-0">
                <span className="block text-xs font-medium" style={{ color: meta.color }}>
                  {meta.label}
                </span>
                <span className="block text-xs font-mono" style={{ color: "var(--text-muted)" }}>
                  {village.risk_score !== null ? village.risk_score.toFixed(2) : "—"}
                </span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
