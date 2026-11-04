// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { Evaluation } from "./Evaluation";
import { api } from "../services/api";
import type { BacktestReadiness, BacktestResponse } from "../types/backtest";
vi.mock("../services/api", () => ({
  api: { evaluationReadiness: vi.fn(), evaluate: vi.fn() },
}));
vi.mock("recharts", async () => ({
  ...(await vi.importActual("recharts")),
  ResponsiveContainer: () => null,
}));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
const ready: BacktestReadiness = {
  status: "ready",
  synthetic: true,
  provenance: "SYNTHETIC historical fixture",
  blockers: [],
  company_count: 8,
  price_count: 8344,
  adjusted_price_count: 8344,
  scheduled_periods: 24,
  decision_dates: [],
  exclusions: {},
};
test("real historical insufficiency disables evaluation without invented charts", async () => {
  vi.mocked(api.evaluationReadiness).mockResolvedValue({
    ...ready,
    status: "insufficient",
    synthetic: false,
    provenance: "Real pilot",
    blockers: ["Historical membership unknown", "No adjusted daily prices"],
    company_count: 1,
    price_count: 7,
    adjusted_price_count: 0,
    scheduled_periods: 0,
  });
  render(<Evaluation />);
  expect(await screen.findByText("Historical membership unknown")).toBeTruthy();
  expect(
    (
      screen.getByRole("button", {
        name: "Run walk-forward comparison",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  expect(screen.queryByText("Subsequent cumulative P&L")).toBeNull();
  expect(api.evaluate).not.toHaveBeenCalled();
});
test("synthetic protocol controls reach actual service and failure clears results", async () => {
  vi.mocked(api.evaluationReadiness).mockResolvedValue(ready);
  vi.mocked(api.evaluate).mockResolvedValue({
    status: "insufficient",
    message: "Holding price missing",
    readiness: { ...ready, blockers: ["No survivor filtering"] },
  } as unknown as BacktestResponse);
  render(<Evaluation />);
  fireEvent.change(screen.getByLabelText("Evaluation dataset"), {
    target: { value: "synthetic" },
  });
  await screen.findByText("SYNTHETIC historical fixture");
  expect(screen.getByText("SYNTHETIC historical demonstration")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Training window"), {
    target: { value: "expanding" },
  });
  fireEvent.change(screen.getByLabelText("Training sessions"), {
    target: { value: "100" },
  });
  fireEvent.change(screen.getByLabelText("Rebalance frequency"), {
    target: { value: "quarterly" },
  });
  fireEvent.change(screen.getByLabelText("Evaluation carbon penalty λ"), {
    target: { value: ".25" },
  });
  fireEvent.change(screen.getByLabelText("Annual risk-free rate"), {
    target: { value: "" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Run walk-forward comparison" }),
  );
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Holding price missing",
  );
  expect(vi.mocked(api.evaluate).mock.calls[0][0]).toMatchObject({
    data_mode: "synthetic",
    window: "expanding",
    training_sessions: 100,
    frequency: "quarterly",
    carbon_penalty: 0.25,
    risk_free_rate: null,
  });
});
test("network failures display an error and permit retry", async () => {
  vi.mocked(api.evaluationReadiness).mockResolvedValue(ready);
  vi.mocked(api.evaluate).mockRejectedValue(new Error("Network failed"));
  render(<Evaluation />);
  fireEvent.change(screen.getByLabelText("Evaluation dataset"), {
    target: { value: "synthetic" },
  });
  await screen.findByText("SYNTHETIC historical fixture");
  fireEvent.click(
    screen.getByRole("button", { name: "Run walk-forward comparison" }),
  );
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Network failed",
  );
  await waitFor(() =>
    expect(
      (
        screen.getByRole("button", {
          name: "Run walk-forward comparison",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(false),
  );
});
