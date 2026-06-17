import { useState, useEffect, useCallback } from "react";
import { analyticsService } from "../services/api";
import type { AnalyticsResponse, InsightsResponse, KPISummary } from "../types";

interface AnalyticsState {
  analytics: AnalyticsResponse | null;
  insights: InsightsResponse | null;
  kpi: KPISummary | null;
  loading: boolean;
  error: string | null;
}

export function useAnalytics(datasetId: string | null) {
  const [state, setState] = useState<AnalyticsState>({
    analytics: null,
    insights: null,
    kpi: null,
    loading: false,
    error: null,
  });

  const fetchAll = useCallback(async () => {
    if (!datasetId) return;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const [analytics, insights, kpi] = await Promise.all([
        analyticsService.getAnalytics(datasetId),
        analyticsService.getInsights(datasetId),
        analyticsService.getKPI(datasetId),
      ]);
      setState({ analytics, insights, kpi, loading: false, error: null });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Failed to load analytics.";
      setState((s) => ({ ...s, loading: false, error: msg }));
    }
  }, [datasetId]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return { ...state, refetch: fetchAll };
}
