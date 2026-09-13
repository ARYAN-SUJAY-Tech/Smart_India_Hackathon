"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { getAlerts, getRisks, getVillageRisk, getVillages } from "@/lib/api";
import type { Alert, Risk, Village, VillageRisk } from "@/lib/types";

const RISK_POLL_INTERVAL_MS = 5000;

interface DataContextValue {
  villages: Village[];
  villageRisks: VillageRisk[];
  alerts: Alert[];
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  refreshRisk: () => Promise<void>;
  refreshAlerts: () => Promise<void>;
  refreshVillageRisk: (villageId: number) => Promise<void>;
}

const DataContext = createContext<DataContextValue | null>(null);

function mergeVillagesWithRisk(
  villages: Village[],
  risks: Risk[]
): VillageRisk[] {
  const riskByVillageId = new Map(risks.map((r) => [r.village_id, r]));
  return villages.map((village) => {
    const risk = riskByVillageId.get(village.id);
    return {
      ...village,
      risk_score: risk?.risk_score ?? null,
      risk_level: risk?.risk_level ?? "normal",
      contributing_factors: risk?.contributing_factors ?? {},
      risk_timestamp: risk?.timestamp ?? null,
    };
  });
}

export function DataProvider({ children }: { children: React.ReactNode }) {
  const [villages, setVillages] = useState<Village[]>([]);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refreshRisk = useCallback(async () => {
    try {
      const data = await getRisks();
      setRisks(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load risk data");
    }
  }, []);

  const refreshAlerts = useCallback(async () => {
    try {
      const data = await getAlerts();
      setAlerts(data);
    } catch {
      // alert history is non-critical to the demo -- ignore transient failures
    }
  }, []);

  // GET /risk/{id} also logs an AlertLog row server-side (unlike the bulk
  // /risk/ the map poll uses), so this doubles as the "log this reading to
  // the alert timeline" call after a sensor submission.
  const refreshVillageRisk = useCallback(
    async (villageId: number) => {
      try {
        const risk = await getVillageRisk(villageId);
        setRisks((prev) => [...prev.filter((r) => r.village_id !== villageId), risk]);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load risk data");
      }
      await refreshAlerts();
    },
    [refreshAlerts]
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getVillages();
        if (!cancelled) setVillages(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load villages");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      const [riskResult, alertResult] = await Promise.allSettled([getRisks(), getAlerts()]);
      if (cancelled) return;
      if (riskResult.status === "fulfilled") {
        setRisks(riskResult.value);
        setError(null);
      } else {
        setError(
          riskResult.reason instanceof Error
            ? riskResult.reason.message
            : "Failed to load risk data"
        );
      }
      if (alertResult.status === "fulfilled") {
        setAlerts(alertResult.value);
      }
      setLastUpdated(new Date());
    };

    poll();
    const interval = setInterval(poll, RISK_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const villageRisks = useMemo(
    () => mergeVillagesWithRisk(villages, risks),
    [villages, risks]
  );

  const value = useMemo<DataContextValue>(
    () => ({
      villages,
      villageRisks,
      alerts,
      loading,
      error,
      lastUpdated,
      refreshRisk,
      refreshAlerts,
      refreshVillageRisk,
    }),
    [
      villages,
      villageRisks,
      alerts,
      loading,
      error,
      lastUpdated,
      refreshRisk,
      refreshAlerts,
      refreshVillageRisk,
    ]
  );

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}

export function useData(): DataContextValue {
  const ctx = useContext(DataContext);
  if (!ctx) throw new Error("useData must be used within DataProvider");
  return ctx;
}
