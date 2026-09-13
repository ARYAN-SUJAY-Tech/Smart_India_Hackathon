"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useData } from "@/context/DataContext";
import RiskSummaryBar from "@/components/dashboard/RiskSummaryBar";
import VillageList from "@/components/village/VillageList";
import AlertTimeline from "@/components/map/AlertTimeline";
import SensorIngestForm from "@/components/sensor/SensorIngestForm";
import VillageDetailPanel from "@/components/village/VillageDetailPanel";
import type { RiskLevel } from "@/lib/types";

// react-leaflet touches `window` at module load -- must be client-only.
const MapWidget = dynamic(() => import("@/components/map/MapWidget"), { ssr: false });

export default function DashboardPage() {
  const { villageRisks, loading } = useData();
  const [activeVillageId, setActiveVillageId] = useState<number | null>(null);
  const [riskFilter, setRiskFilter] = useState<RiskLevel | null>(null);

  // Re-derive from villageRisks (not a stashed snapshot) so the panel and
  // marker highlight stay live as the 5s risk poll comes in.
  const activeVillage = villageRisks.find((v) => v.id === activeVillageId) ?? null;
  const filteredVillages = riskFilter
    ? villageRisks.filter((v) => v.risk_level === riskFilter)
    : villageRisks;

  return (
    <div className="h-full flex flex-col">
      <RiskSummaryBar villages={villageRisks} activeFilter={riskFilter} onFilterChange={setRiskFilter}>
        <SensorIngestForm />
      </RiskSummaryBar>

      <div className="flex-1 min-h-0 flex flex-col md:flex-row">
        <aside
          className="w-full md:w-96 shrink-0 order-2 md:order-1 md:flex md:flex-col md:overflow-y-auto"
          style={{ borderRight: "1px solid var(--border-color)", backgroundColor: "var(--bg-surface)" }}
        >
          <VillageList villages={filteredVillages} activeId={activeVillageId} onSelect={(v) => setActiveVillageId(v.id)} />
          <div style={{ borderTop: "1px solid var(--border-color)" }}>
            <AlertTimeline />
          </div>
        </aside>

        <div className="relative flex-1 min-h-[60vh] md:min-h-0 order-1 md:order-2">
          <MapWidget
            villages={filteredVillages}
            activeVillage={activeVillage}
            onSelectVillage={(village) => setActiveVillageId(village.id)}
          />

          {loading && (
            <div
              className="absolute top-3 left-3 z-1000 text-sm px-3 py-1.5 rounded"
              style={{ backgroundColor: "var(--bg-surface)", color: "var(--text-muted)" }}
            >
              Loading villages…
            </div>
          )}

          {activeVillage && (
            <VillageDetailPanel village={activeVillage} onClose={() => setActiveVillageId(null)} />
          )}
        </div>
      </div>
    </div>
  );
}
