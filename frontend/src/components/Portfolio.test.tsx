// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { Portfolio } from "./Portfolio";
import { api } from "../services/api";
import type { PortfolioResponse, PortfolioReadiness } from "../types/portfolio";
vi.mock("../services/api", () => ({
  api: { portfolioReadiness: vi.fn(), portfolio: vi.fn() },
}));
vi.mock("recharts", async () => ({
  ...(await vi.importActual("recharts")),
  ResponsiveContainer: () => null,
}));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
const ready: PortfolioReadiness = {
  status: "ready",
  synthetic: true,
  provenance: "SYNTHETIC fixture only",
  blockers: [],
  available_companies: [1, 2, 3, 4].map((id) => ({
    id,
    name: `SYNTHETIC ${id}`,
    sector: "Energy",
  })),
  selected_count: 4,
  eligible_count: 4,
  price_count: 1000,
  adjusted_price_count: 1000,
  emission_count: 4,
  aligned_observations: 249,
  long_ids: [1, 2],
  short_ids: [3, 4],
};
test("real insufficiency disables optimization and synthetic mode remains explicit", async () => {
  vi.mocked(api.portfolioReadiness).mockResolvedValue({
    ...ready,
    status: "insufficient",
    synthetic: false,
    provenance: "Real pilot",
    blockers: ["No adjusted daily history"],
    available_companies: [{ id: 4, name: "Siemens AG", sector: "Industrials" }],
    selected_count: 1,
    eligible_count: 0,
    price_count: 7,
    adjusted_price_count: 0,
    aligned_observations: 0,
  });
  render(<Portfolio />);
  expect(await screen.findByText("No adjusted daily history")).toBeTruthy();
  expect(
    (
      screen.getByRole("button", {
        name: "Compare portfolios and sensitivity",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  expect(api.portfolio).not.toHaveBeenCalled();
  vi.mocked(api.portfolioReadiness).mockResolvedValue(ready);
  fireEvent.change(screen.getByLabelText("Dataset mode"), {
    target: { value: "synthetic" },
  });
  expect(await screen.findByText("SYNTHETIC fixture only")).toBeTruthy();
  expect(
    screen.getByText("SYNTHETIC demonstration · in-sample estimates"),
  ).toBeTruthy();
  expect(
    (
      screen.getByRole("button", {
        name: "Compare portfolios and sensitivity",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(false);
});
test("configuration controls reach the API and solver failures are displayed", async () => {
  vi.mocked(api.portfolioReadiness).mockResolvedValue(ready);
  vi.mocked(api.portfolio).mockResolvedValue({
    status: "solver_error",
    message: "Forced solver failure",
    readiness: { ...ready, blockers: [] },
  } as unknown as PortfolioResponse);
  render(<Portfolio />);
  fireEvent.change(screen.getByLabelText("Dataset mode"), {
    target: { value: "synthetic" },
  });
  await screen.findByText("SYNTHETIC fixture only");
  fireEvent.change(screen.getByLabelText("Risk aversion γ"), {
    target: { value: "5" },
  });
  fireEvent.change(screen.getByLabelText("Carbon penalty λ"), {
    target: { value: "0.25" },
  });
  fireEvent.change(screen.getByLabelText("Maximum position weight"), {
    target: { value: "0.3" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Compare portfolios and sensitivity" }),
  );
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Forced solver failure",
  );
  expect(vi.mocked(api.portfolio).mock.calls[0][1]).toMatchObject({
    data_mode: "synthetic",
    risk_aversion: 5,
    carbon_penalty: 0.25,
    max_weight: 0.3,
    company_ids: [1, 2, 3, 4],
  });
});
test("manual sleeves, selection and sensitivity settings are sent without overlap", async () => {
  vi.mocked(api.portfolioReadiness).mockResolvedValue(ready);
  vi.mocked(api.portfolio).mockResolvedValue({
    status: "infeasible",
    message: "Test infeasibility",
    readiness: { ...ready, blockers: [] },
  } as unknown as PortfolioResponse);
  render(<Portfolio />);
  fireEvent.change(screen.getByLabelText("Dataset mode"), {
    target: { value: "synthetic" },
  });
  await screen.findByText("SYNTHETIC fixture only");
  fireEvent.change(screen.getByLabelText("Candidate selection"), {
    target: { value: "manual" },
  });
  fireEvent.change(screen.getByLabelText("Sensitivity penalties"), {
    target: { value: "0, 0.2, 0.5" },
  });
  fireEvent.change(screen.getByLabelText("Candidate side for SYNTHETIC 2"), {
    target: { value: "short" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Compare portfolios and sensitivity" }),
  );
  await waitFor(() => expect(api.portfolio).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.portfolio).mock.calls[0][1]).toMatchObject({
    selection: "manual",
    long_ids: [1],
    short_ids: [2, 3, 4],
    penalties: [0, 0.2, 0.5],
  });
});
