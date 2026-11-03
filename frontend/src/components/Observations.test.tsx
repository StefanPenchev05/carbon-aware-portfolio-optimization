// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { Observations } from "./Observations";
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return { ...actual, ResponsiveContainer: () => null };
});
afterEach(cleanup);
it("shows per-scope estimates, basis, publication uncertainty and provenance", () => {
  render(
    <Observations
      prices={[]}
      emissions={[
        {
          year: 2024,
          scope1: 100,
          scope2: 200,
          scope3: null,
          units: "tCO2e",
          methodology: "Test-only disclosure",
          notes: "Test fixture, not acquired data",
          scope1_status: "reported",
          scope2_status: "estimated",
          scope3_status: "unknown",
          scope2_basis: "market-based",
          disclosure_date: null,
          disclosure_reference: "Fixture report page 5",
          source: {
            id: 1,
            name: "Test fixture",
            reference: "Fixture reference",
            synthetic: false,
            imported_at: "2026-01-02T00:00:00Z",
            retrieved_at: "2026-01-01T00:00:00Z",
            notes: "",
            license_reference: "Fixture usage conditions",
          },
        },
      ]}
    />,
  );
  expect(screen.getByText("100 (reported)")).toBeTruthy();
  expect(screen.getByText("200 (estimated)")).toBeTruthy();
  expect(screen.getByText("Unavailable")).toBeTruthy();
  expect(
    screen.getByRole("heading", { name: /Scope 2 market-based/ }),
  ).toBeTruthy();
  expect(
    screen.getByText(/Publication date unavailable; excluded/),
  ).toBeTruthy();
  expect(
    screen.getByText(/Usage terms: Fixture usage conditions/),
  ).toBeTruthy();
  expect(screen.getByText(/Real data/)).toBeTruthy();
});
