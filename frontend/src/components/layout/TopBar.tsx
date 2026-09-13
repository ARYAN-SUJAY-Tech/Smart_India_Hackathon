"use client";

import { useEffect, useState } from "react";
import { Waves } from "lucide-react";
import { useData } from "@/context/DataContext";
import { RISK_LEVEL_META } from "@/lib/riskLevels";

function useRelativeTime(date: Date | null): string {
  const [now, setNow] = useState<number>(() => Date.now());

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  if (!date) return "connecting…";
  const seconds = Math.max(0, Math.round((now - date.getTime()) / 1000));
  if (seconds < 2) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  return `${Math.round(seconds / 60)}m ago`;
}

export default function TopBar() {
  const { lastUpdated, error } = useData();
  const relativeTime = useRelativeTime(lastUpdated);

  return (
    <header
      className="sticky top-0 z-1000 h-16 flex items-center justify-between px-4 md:px-6 shrink-0"
      style={{
        backgroundColor: "var(--bg-surface)",
        borderBottom: "1px solid var(--border-color)",
      }}
    >
      <div className="flex items-center gap-3 min-w-0">
        <Waves size={22} style={{ color: "var(--accent-primary)" }} strokeWidth={2} />
        <div className="min-w-0">
          <h1 className="text-sm font-semibold leading-tight truncate" style={{ color: "var(--text-primary)" }}>
            Flood Watch
          </h1>
          <p className="text-xs leading-tight truncate hidden sm:block" style={{ color: "var(--text-muted)" }}>
            Flash Flood & Landslide Early Warning — SIH PS26192
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 text-xs shrink-0" style={{ color: error ? RISK_LEVEL_META.severe.color : "var(--text-muted)" }}>
        <span
          className="inline-block w-2 h-2 rounded-full"
          style={{
            backgroundColor: error ? RISK_LEVEL_META.severe.color : RISK_LEVEL_META.normal.color,
            boxShadow: error
              ? "none"
              : `0 0 0 3px color-mix(in srgb, ${RISK_LEVEL_META.normal.color} 25%, transparent)`,
          }}
        />
        <span className="hidden sm:inline">{error ? "Connection issue" : "Live"}</span>
        <span>{error ? `· ${error}` : `· ${relativeTime}`}</span>
      </div>
    </header>
  );
}
