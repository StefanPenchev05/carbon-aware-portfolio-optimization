// @vitest-environment jsdom
import {
  cleanup,
  render,
  screen,
  waitFor,
  fireEvent,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { Analysis } from "./Analysis";
vi.mock("recharts", async () => {
  const actual = await vi.importActual("recharts");
  return { ...actual, ResponsiveContainer: () => null };
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
test("shows structured real-data insufficiency without displaying invented coefficients", async () => {
  const fetchMock = vi.fn(async (url: string) => ({
    ok: true,
    json: async () =>
      url.includes("/returns")
        ? { series: [], carbon: [] }
        : {
            status: "insufficient",
            message:
              "Insufficient verified corporate observations for statistical analysis.",
            valid_pairs: 0,
            distinct_companies: 0,
            coefficient_pearson: null,
            coefficient_spearman: null,
            exclusions: { "No reviewed annual series": 1 },
            warnings: ["At least 5 distinct companies required"],
            points: [],
          },
  }));
  vi.stubGlobal("fetch", fetchMock);
  render(<Analysis />);
  expect(
    await screen.findByText(
      "Insufficient verified corporate observations for statistical analysis.",
    ),
  ).toBeTruthy();
  expect(screen.getByText("No reviewed annual series: 1")).toBeTruthy();
  expect(screen.queryByText(/Pearson/)).toBeNull();
  fireEvent.change(screen.getByLabelText("Scope 2 basis"), {
    target: { value: "location-based" },
  });
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));
  expect(fetchMock.mock.calls[2][0]).toContain("basis=location-based");
});
