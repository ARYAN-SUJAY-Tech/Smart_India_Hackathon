"use client";

import { useState, type FormEvent } from "react";
import { FlaskConical, Loader2, Send, X } from "lucide-react";
import { useData } from "@/context/DataContext";
import { ingestSensorReading } from "@/lib/api";

const inputStyle: React.CSSProperties = {
  backgroundColor: "var(--bg-base)",
  border: "1px solid var(--border-color)",
  color: "var(--text-primary)",
};

// This is a demo/testing affordance, not part of the real early-warning
// product surface -- it stands in for a real IoT/SMAP feed hitting
// POST /sensor/ingest directly. Kept visually secondary (a small pill
// button that opens a modal) so it never competes with actual risk/alert
// data for attention.
export default function SensorIngestForm() {
  const { villages, refreshVillageRisk } = useData();
  const [isOpen, setIsOpen] = useState(false);
  const [villageId, setVillageId] = useState<number | "">("");
  const [soilMoisture, setSoilMoisture] = useState("");
  const [rainfallMm, setRainfallMm] = useState("");
  const [waterLevelM, setWaterLevelM] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!villageId) return;

    setSubmitting(true);
    setStatus(null);
    try {
      await ingestSensorReading({
        village_id: villageId,
        soil_moisture: soilMoisture ? Number(soilMoisture) : undefined,
        rainfall_mm: rainfallMm ? Number(rainfallMm) : undefined,
        water_level_m: waterLevelM ? Number(waterLevelM) : undefined,
        source: "simulated",
      });
      setStatus("Reading submitted — risk score updated");
      await refreshVillageRisk(villageId);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Failed to submit reading");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm cursor-pointer whitespace-nowrap"
        style={{
          backgroundColor: "transparent",
          border: "1px solid var(--border-color)",
          color: "var(--text-secondary)",
        }}
        title="Simulate an IoT/SMAP sensor reading -- a demo/testing tool, not a live sensor"
      >
        <FlaskConical size={14} />
        <span className="hidden sm:inline">Simulate Sensor Reading</span>
        <span className="sm:hidden">Simulate</span>
      </button>

      {isOpen && (
        <div
          className="fixed inset-0 z-2000 flex items-center justify-center p-4"
          style={{ backgroundColor: "rgba(0,0,0,0.6)" }}
          onClick={() => setIsOpen(false)}
        >
          <div
            className="w-full max-w-sm rounded-lg shadow-2xl"
            style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-color)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3 p-4" style={{ borderBottom: "1px solid var(--border-color)" }}>
              <div>
                <h2 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                  Simulate Sensor Reading
                </h2>
                <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                  Demo tool — stands in for a real IoT/SMAP feed. Not a live sensor.
                </p>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="cursor-pointer p-1 -m-1 shrink-0 rounded hover:opacity-70"
                style={{ color: "var(--text-muted)" }}
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-4 space-y-3">
              <div className="space-y-1">
                <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                  Village
                </label>
                <select
                  value={villageId}
                  onChange={(e) => setVillageId(e.target.value ? Number(e.target.value) : "")}
                  required
                  className="w-full px-3 py-2 text-sm rounded"
                  style={inputStyle}
                >
                  <option value="">Select village</option>
                  {villages.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                  Soil Moisture (0.20 – 0.48)
                </label>
                <input
                  type="number"
                  step="any"
                  value={soilMoisture}
                  onChange={(e) => setSoilMoisture(e.target.value)}
                  placeholder="0.35"
                  className="w-full px-3 py-2 text-sm rounded"
                  style={inputStyle}
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                  Rainfall (mm)
                </label>
                <input
                  type="number"
                  step="any"
                  value={rainfallMm}
                  onChange={(e) => setRainfallMm(e.target.value)}
                  placeholder="45"
                  className="w-full px-3 py-2 text-sm rounded"
                  style={inputStyle}
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                  Water Level (m)
                </label>
                <input
                  type="number"
                  step="any"
                  value={waterLevelM}
                  onChange={(e) => setWaterLevelM(e.target.value)}
                  placeholder="1.2"
                  className="w-full px-3 py-2 text-sm rounded"
                  style={inputStyle}
                />
              </div>

              <button
                type="submit"
                disabled={submitting || !villageId}
                className="w-full flex items-center justify-center gap-2 py-2 rounded text-sm font-medium cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ backgroundColor: "var(--accent-primary)", color: "var(--text-on-accent)" }}
              >
                {submitting ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                Submit Reading
              </button>

              {status && (
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {status}
                </p>
              )}
            </form>
          </div>
        </div>
      )}
    </>
  );
}
