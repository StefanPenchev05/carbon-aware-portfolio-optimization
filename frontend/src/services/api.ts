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
