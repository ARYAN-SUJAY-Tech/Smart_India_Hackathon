"use client";

import { AlertTriangle } from "lucide-react";
import { useData } from "@/context/DataContext";
import { RISK_LEVEL_META } from "@/lib/riskLevels";

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function AlertTimeline() {
  const { alerts, villages } = useData();
  const villageNameById = new Map(villages.map((v) => [v.id, v.name]));

  return (
    <div className="flex flex-col">
      <div
        className="flex items-center gap-2 px-4 py-3 sticky top-0"
        style={{ backgroundColor: "var(--bg-surface)", borderBottom: "1px solid var(--border-color)" }}
      >
        <AlertTriangle size={16} style={{ color: "var(--accent-primary)" }} />
        <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          Alert History
        </h2>
      </div>

      {alerts.length === 0 ? (
        <p className="text-sm p-4" style={{ color: "var(--text-muted)" }}>
          No alerts logged yet.
        </p>
      ) : (
        <ul className="divide-y" style={{ borderColor: "var(--border-color)" }}>
          {alerts.map((alert) => {
            const meta = RISK_LEVEL_META[alert.risk_level];
            return (
              <li key={alert.id} className="px-4 py-3">
                <div className="flex justify-between items-start gap-2">
                  <span className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
                    {villageNameById.get(alert.village_id) ?? `Village #${alert.village_id}`}
                  </span>
                  <span
                    className="text-xs font-medium px-2 py-0.5 rounded shrink-0"
                    style={{ color: meta.color, border: `1px solid ${meta.color}` }}
                  >
                    {meta.label}
                  </span>
                </div>
                <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                  score {alert.risk_score.toFixed(2)} · {formatTime(alert.timestamp)}
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
