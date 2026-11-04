import type {
  BacktestConfiguration,
  BacktestReadiness,
  BacktestResponse,
} from "../types/backtest";
import type {
  PortfolioConfiguration,
  PortfolioReadiness,
  PortfolioResponse,
} from "../types/portfolio";
import type { Correlation, Data } from "../types/analysis";
import type { Company, Price, Emission } from "../types/data";
const base = import.meta.env.VITE_API_URL || "";
async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${base}/api${path}`, { signal });
  if (!response.ok)
    throw new Error(
      `Data request failed (${response.status}). Check that the API and database are running.`,
    );
  return response.json() as Promise<T>;
}
export const api = {
  evaluationReadiness: (mode: "real" | "synthetic", signal?: AbortSignal) =>
    get<BacktestReadiness>(`/backtest/readiness?data_mode=${mode}`, signal),
  evaluate: async (
    configuration: BacktestConfiguration,
    signal?: AbortSignal,
  ): Promise<BacktestResponse> => {
    const response = await fetch(`${base}/api/backtest/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(configuration),
      signal,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const detail = Array.isArray(body?.detail)
        ? body.detail.map((e: { msg: string }) => e.msg).join("; ")
        : body?.detail;
      throw new Error(
        detail || `Evaluation request failed (${response.status})`,
      );
    }
    return response.json() as Promise<BacktestResponse>;
  },
  portfolioReadiness: (mode: "real" | "synthetic", signal?: AbortSignal) =>
    get<PortfolioReadiness>(`/portfolio/readiness?data_mode=${mode}`, signal),
  portfolio: async (
    operation: "optimize" | "compare" | "sensitivity",
    configuration: PortfolioConfiguration,
    signal?: AbortSignal,
  ): Promise<PortfolioResponse> => {
    const response = await fetch(`${base}/api/portfolio/${operation}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(configuration),
      signal,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const detail = Array.isArray(body?.detail)
        ? body.detail.map((e: { msg: string }) => e.msg).join("; ")
        : body?.detail;
      throw new Error(
        detail || `Portfolio request failed (${response.status})`,
      );
    }
    return response.json() as Promise<PortfolioResponse>;
  },
  analysis: (query: URLSearchParams, signal?: AbortSignal) =>
    Promise.all([
      get<Data>(`/analysis/returns?${query}`, signal),
      get<Correlation>(`/analysis/correlations?${query}`, signal),
    ]),
  companies: (sector: string, signal?: AbortSignal) =>
    get<Company[]>(
      `/companies${sector ? `?sector=${encodeURIComponent(sector)}` : ""}`,
      signal,
    ),
  prices: (id: number, signal?: AbortSignal) =>
    get<Price[]>(`/companies/${id}/prices`, signal),
  emissions: (id: number, signal?: AbortSignal) =>
    get<Emission[]>(`/companies/${id}/emissions`, signal),
};
