import { useEffect, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../services/api";
import type {
  PortfolioConfiguration,
  PortfolioReadiness,
  PortfolioResponse,
} from "../types/portfolio";

const initial: PortfolioConfiguration = {
  data_mode: "real",
  company_ids: [],
  start_date: "2024-01-02",
  end_date: "2024-12-31",
  as_of: "2025-01-02",
  risk_aversion: 3,
  carbon_penalty: 0.1,
  long_gross: 0.5,
  short_gross: 0.5,
  max_weight: 0.25,
  selection: "auto",
  long_ids: [],
  short_ids: [],
  carbon_metric: "scope1+2-market-based",
  penalties: [0, 0.01, 0.05, 0.1, 0.25],
  min_assets: 4,
  min_candidates: 2,
  min_observations: 60,
  shrinkage: 0.05,
};
const percent = (v: number) => `${(100 * v).toFixed(2)}%`;
const score = (v: number) => v.toFixed(4);
export function Portfolio() {
  const [configuration, setConfiguration] = useState(initial);
  const [readiness, setReadiness] = useState<PortfolioReadiness | null>(null);
  const [penalties, setPenalties] = useState("0, 0.01, 0.05, 0.1, 0.25");
  const [sides, setSides] = useState<Record<number, "long" | "short">>({});
  const [comparisonResponse, setComparison] =
    useState<PortfolioResponse | null>(null);
  const [sensitivityResponse, setSensitivity] =
    useState<PortfolioResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const request = useRef<AbortController | null>(null);
  const mode = configuration.data_mode;
  const label =
    mode === "synthetic"
      ? "SYNTHETIC demonstration · in-sample estimates"
      : "Real corporate data · in-sample estimates";
  useEffect(() => {
    const controller = new AbortController();
    request.current?.abort();
    setReadiness(null);
    setComparison(null);
    setSensitivity(null);
    setError("");
    setLoading(false);
    api
      .portfolioReadiness(mode, controller.signal)
      .then((r) => {
        if (controller.signal.aborted) return;
        setReadiness(r);
        setConfiguration((c) => ({
          ...c,
          company_ids: r.available_companies.map((a) => a.id),
        }));
        setSides(
          Object.fromEntries(
            r.available_companies.map((a, i) => [
              a.id,
              (
                r.long_ids.length
                  ? r.long_ids.includes(a.id)
                  : i < r.available_companies.length / 2
              )
                ? "long"
                : "short",
            ]),
          ),
        );
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(String(e));
      });
    return () => {
      controller.abort();
      request.current?.abort();
    };
  }, [mode]);
  function update<K extends keyof PortfolioConfiguration>(
    key: K,
    value: PortfolioConfiguration[K],
  ) {
    request.current?.abort();
    setLoading(false);
    setError("");
    setComparison(null);
    setSensitivity(null);
    setConfiguration((c) => ({ ...c, [key]: value }));
  }
  async function run() {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError("");
    setComparison(null);
    setSensitivity(null);
    const c = {
      ...configuration,
      penalties: penalties.split(",").map((s) => Number(s.trim())),
      long_ids:
        configuration.selection === "manual"
          ? configuration.company_ids.filter((id) => sides[id] === "long")
          : [],
      short_ids:
        configuration.selection === "manual"
          ? configuration.company_ids.filter((id) => sides[id] === "short")
          : [],
    };
    try {
      const [comparison, sensitivity] = await Promise.all([
        api.portfolio("compare", c, controller.signal),
        api.portfolio("sensitivity", c, controller.signal),
      ]);
      if (controller.signal.aborted) return;
      const failed = [comparison, sensitivity].find(
        (r) => r.status !== "success",
      );
      if (failed) {
        setError(
          `${failed.status}: ${failed.message} ${failed.readiness.blockers.join("; ")}`,
        );
        return;
      }
      setComparison(comparison);
      setSensitivity(sensitivity);
    } catch (e) {
      if (!controller.signal.aborted) setError(String(e));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }
  const comparison = comparisonResponse?.comparison;
  const sensitivity = sensitivityResponse?.sensitivity;
  const allocations =
    comparison?.traditional.positions.map((p, i) => ({
      name: p.name,
      traditional: p.weight,
      carbonAware: comparison.carbon_aware.positions[i].weight,
      change: comparison.difference.weights[String(p.company_id)],
    })) ?? [];
  return (
    <section aria-label="Portfolio optimization">
      <div className="intro">
        <h1>Portfolio optimization</h1>
        <p className="dataset-label">{label}</p>
        <p>
          Fixed long and short sleeves. Carbon penalty applies to the long book
          only. These are optimization estimates, not realized performance.
        </p>
      </div>
      <div className="portfolio-layout">
        <aside>
          <h2>Experiment settings</h2>
          <label>
            Dataset mode
            <select
              value={mode}
              onChange={(e) =>
                update("data_mode", e.target.value as "real" | "synthetic")
              }
            >
              <option value="real">Real corporate data</option>
              <option value="synthetic">SYNTHETIC demonstration</option>
            </select>
          </label>
          <label title="First price is the return baseline; use a reviewed trading session.">
            Estimation start
            <input
              type="date"
              value={configuration.start_date}
              onChange={(e) => update("start_date", e.target.value)}
            />
          </label>
          <label>
            Estimation end
            <input
              type="date"
              value={configuration.end_date}
              onChange={(e) => update("end_date", e.target.value)}
            />
          </label>
          <label title="All price observations must precede formation. Date-only emissions disclosures must also precede this date.">
            Formation date
            <input
              type="date"
              value={configuration.as_of}
              onChange={(e) => update("as_of", e.target.value)}
            />
          </label>
          <label title="Annual return units per unit annual variance; higher values penalize estimated variance more.">
            Risk aversion γ
            <input
              type="number"
              min="0"
              max="10000"
              step="0.5"
              value={configuration.risk_aversion}
              onChange={(e) => update("risk_aversion", Number(e.target.value))}
            />
          </label>
          <label title="Annual return-equivalent cost per unit of long-book rank score. Zero reproduces the traditional model.">
            Carbon penalty λ
            <input
              type="number"
              min="0"
              max="10"
              step="0.01"
              value={configuration.carbon_penalty}
              onChange={(e) => update("carbon_penalty", Number(e.target.value))}
            />
          </label>
          <label title="Absolute weight as a fraction of portfolio reference capital, e.g. 0.25 = 25%.">
            Maximum position weight
            <input
              type="number"
              min="0.01"
              max="1"
              step="0.01"
              value={configuration.max_weight}
              onChange={(e) => update("max_weight", Number(e.target.value))}
            />
          </label>
          <label>
            Long gross allocation
            <input
              type="number"
              min="0.01"
              max="2"
              step="0.05"
              value={configuration.long_gross}
              onChange={(e) => update("long_gross", Number(e.target.value))}
            />
          </label>
          <label>
            Short gross allocation (positive magnitude)
            <input
              type="number"
              min="0.01"
              max="2"
              step="0.05"
              value={configuration.short_gross}
              onChange={(e) => update("short_gross", Number(e.target.value))}
            />
          </label>
          <label>
            Candidate selection
            <select
              value={configuration.selection}
              onChange={(e) =>
                update("selection", e.target.value as "auto" | "manual")
              }
            >
              <option value="auto">Automatic: rank estimated returns</option>
              <option value="manual">Manual disjoint sleeves</option>
            </select>
          </label>
          <fieldset>
            <legend>Selected companies</legend>
            {readiness?.available_companies.map((a) => (
              <div className="portfolio-company" key={a.id}>
                <label>
                  <input
                    type="checkbox"
                    checked={configuration.company_ids.includes(a.id)}
                    onChange={(e) =>
                      update(
                        "company_ids",
                        e.target.checked
                          ? [...configuration.company_ids, a.id]
                          : configuration.company_ids.filter(
                              (id) => id !== a.id,
                            ),
                      )
                    }
                  />
                  {a.name} · {a.sector}
                </label>
                {configuration.selection === "manual" &&
                  configuration.company_ids.includes(a.id) && (
                    <label>
                      Candidate side for {a.name}
                      <select
                        value={sides[a.id] ?? "long"}
                        onChange={(e) => {
                          setSides((s) => ({
                            ...s,
                            [a.id]: e.target.value as "long" | "short",
                          }));
                          update("selection", "manual");
                        }}
                      >
                        <option value="long">Long</option>
                        <option value="short">Short</option>
                      </select>
                    </label>
                  )}
              </div>
            ))}
          </fieldset>
          <label title="Comma-separated annual return-equivalent penalties. The backend always includes λ=0.">
            Sensitivity penalties
            <input
              value={penalties}
              onChange={(e) => {
                setPenalties(e.target.value);
                update("penalties", []);
              }}
            />
          </label>
          <button
            className="run-portfolio"
            onClick={run}
            disabled={
              loading ||
              !readiness ||
              readiness.status !== "ready" ||
              !configuration.company_ids.length
            }
          >
            {loading ? "Solving…" : "Compare portfolios and sensitivity"}
          </button>
        </aside>
        <div className="portfolio-results">
          {!readiness && !error && (
            <p role="status">Checking dataset readiness…</p>
          )}
          {readiness && (
            <article>
              <h2>
                Dataset readiness ·{" "}
                {mode === "synthetic" ? "SYNTHETIC" : "real"}
              </h2>
              <p>
                {readiness.selected_count}{" "}
                {readiness.selected_count === 1 ? "security" : "securities"} ·{" "}
                {readiness.price_count} acquired prices ·{" "}
                {readiness.adjusted_price_count} adjusted prices ·{" "}
                {readiness.aligned_observations} aligned return intervals
              </p>
              <p className="provenance">{readiness.provenance}</p>
              {readiness.status !== "ready" && (
                <>
                  <p role="status">
                    {mode === "real"
                      ? "Real portfolio optimization is unavailable with the current verified inputs."
                      : "SYNTHETIC demonstration is unavailable for this configuration."}
                  </p>
                  <ul>
                    {readiness.blockers.map((b) => (
                      <li key={b}>{b}</li>
                    ))}
                  </ul>
                </>
              )}
            </article>
          )}
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          {comparison && comparisonResponse?.estimates && (
            <>
              <article>
                <h2>Traditional vs carbon-aware</h2>
                <p className="dataset-label">{label}</p>
                <p>
                  Estimation {comparisonResponse.estimates.start_date}–
                  {comparisonResponse.estimates.end_date}; formation{" "}
                  {comparisonResponse.estimates.as_of}.{" "}
                  {comparisonResponse.estimates.observations} aligned daily
                  intervals. {comparisonResponse.estimates.selection_method}.
                </p>
                <table>
                  <thead>
                    <tr>
                      <th>Annual estimate / exposure</th>
                      <th>Traditional λ=0</th>
                      <th>
                        Carbon-aware λ={comparison.carbon_aware.carbon_penalty}
                      </th>
                      <th>Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(
                      [
                        [
                          "Expected return",
                          comparison.traditional.expected_return_annual,
                          comparison.carbon_aware.expected_return_annual,
                          true,
                        ],
                        [
                          "Volatility",
                          comparison.traditional.volatility_annual,
                          comparison.carbon_aware.volatility_annual,
                          true,
                        ],
                        [
                          "Long-book carbon score",
                          comparison.traditional.carbon_exposure_score,
                          comparison.carbon_aware.carbon_exposure_score,
                          false,
                        ],
                        [
                          "Long exposure",
                          comparison.traditional.long_exposure,
                          comparison.carbon_aware.long_exposure,
                          true,
                        ],
                        [
                          "Short exposure",
                          comparison.traditional.short_exposure,
                          comparison.carbon_aware.short_exposure,
                          true,
                        ],
                        [
                          "Gross exposure",
                          comparison.traditional.gross_exposure,
                          comparison.carbon_aware.gross_exposure,
                          true,
                        ],
                        [
                          "Net exposure",
                          comparison.traditional.net_exposure,
                          comparison.carbon_aware.net_exposure,
                          true,
                        ],
                      ] as [string, number, number, boolean][]
                    ).map(([name, a, b, p]) => (
                      <tr key={name}>
                        <th>{name}</th>
                        <td>{p ? percent(a) : score(a)}</td>
                        <td>{p ? percent(b) : score(b)}</td>
                        <td>{p ? percent(b - a) : score(b - a)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p>
                  {comparison.carbon_aware.solver}:{" "}
                  {comparison.carbon_aware.solver_status}. Maximum constraint
                  violation{" "}
                  {comparison.carbon_aware.max_constraint_violation.toExponential(
                    2,
                  )}
                  .
                </p>
                <div
                  className="analysis-chart"
                  aria-label={`${label}: annual financial comparison`}
                >
                  <ResponsiveContainer>
                    <BarChart
                      data={[
                        {
                          metric: "Expected return",
                          traditional:
                            comparison.traditional.expected_return_annual,
                          carbonAware:
                            comparison.carbon_aware.expected_return_annual,
                        },
                        {
                          metric: "Volatility",
                          traditional: comparison.traditional.volatility_annual,
                          carbonAware:
                            comparison.carbon_aware.volatility_annual,
                        },
                      ]}
                    >
                      <XAxis dataKey="metric" />
                      <YAxis tickFormatter={percent} />
                      <Tooltip formatter={(v) => percent(Number(v))} />
                      <Legend />
                      <Bar dataKey="traditional" fill="#285ca8" />
                      <Bar
                        dataKey="carbonAware"
                        name="Carbon-aware"
                        fill="#167d8d"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </article>
              <article>
                <h2>Signed portfolio allocation</h2>
                <p>
                  {label} · Positive weights are long; negative weights are
                  short.
                </p>
                <div className="analysis-chart">
                  <ResponsiveContainer>
                    <BarChart data={allocations}>
                      <XAxis dataKey="name" hide />
                      <YAxis tickFormatter={percent} />
                      <Tooltip formatter={(v) => percent(Number(v))} />
                      <Legend />
                      <ReferenceLine y={0} stroke="#536b7d" />
                      <Bar dataKey="traditional" fill="#285ca8" />
                      <Bar
                        dataKey="carbonAware"
                        name="Carbon-aware"
                        fill="#167d8d"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <table>
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>Sleeve</th>
                      <th>Traditional</th>
                      <th>Carbon-aware</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.traditional.positions.map((p, i) => (
                      <tr key={p.company_id}>
                        <td>{p.name}</td>
                        <td>{p.sleeve}</td>
                        <td>{percent(p.weight)}</td>
                        <td>
                          {percent(comparison.carbon_aware.positions[i].weight)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </article>
              <article>
                <h2>Composition change</h2>
                <p>
                  {label} · Change in signed weight. A negative short-weight
                  change increases the short magnitude.
                </p>
                <p>
                  Total absolute weight change:{" "}
                  {percent(comparison.difference.composition_l1)} (not a
                  transaction-cost estimate).
                </p>
                <div className="analysis-chart">
                  <ResponsiveContainer>
                    <BarChart data={allocations}>
                      <XAxis dataKey="name" hide />
                      <YAxis tickFormatter={percent} />
                      <Tooltip formatter={(v) => percent(Number(v))} />
                      <ReferenceLine y={0} />
                      <Bar dataKey="change">
                        {allocations.map((a) => (
                          <Cell
                            key={a.name}
                            fill={a.change >= 0 ? "#167d8d" : "#9b5c35"}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </article>
              <article>
                <h2>Carbon inputs and normalization</h2>
                <p>
                  {label} · Universe-relative average ranks in [0,1]; original
                  measurements remain separate. Scope 3 is excluded. Short-side
                  scores are context only.
                </p>
                <table>
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>Original Scope 1 / 2 (market)</th>
                      <th>Combined tCO2e</th>
                      <th>Relative score</th>
                      <th>Disclosure</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparisonResponse.estimates.assets.map((a) => (
                      <tr key={a.company_id}>
                        <td>{a.name}</td>
                        <td>
                          {a.original_emission.scope1.toLocaleString()} /{" "}
                          {a.original_emission.scope2.toLocaleString()}{" "}
                          {a.original_emission.units}
                        </td>
                        <td>{a.emissions_tco2e.toLocaleString()}</td>
                        <td>{score(a.carbon_score)}</td>
                        <td>
                          {a.disclosure_year} · published {a.disclosure_date}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </article>
            </>
          )}
          {sensitivity && (
            <article>
              <h2>Carbon-penalty sensitivity</h2>
              <p>
                {label} · Same universe, estimates, candidate groups and
                constraints for all λ.
              </p>
              <div className="analysis-chart">
                <ResponsiveContainer>
                  <LineChart data={sensitivity.portfolios}>
                    <XAxis dataKey="carbon_penalty" type="number" name="λ" />
                    <YAxis yAxisId="financial" tickFormatter={percent} />
                    <YAxis
                      yAxisId="carbon"
                      orientation="right"
                      domain={[0, configuration.long_gross]}
                    />
                    <Tooltip
                      formatter={(v, name) =>
                        name === "Long-book carbon score (right axis)"
                          ? score(Number(v))
                          : percent(Number(v))
                      }
                      labelFormatter={(v) => `λ=${v}`}
                    />
                    <Legend />
                    <Line
                      yAxisId="financial"
                      dataKey="expected_return_annual"
                      name="Expected annual return"
                      stroke="#285ca8"
                    />
                    <Line
                      yAxisId="financial"
                      dataKey="volatility_annual"
                      name="Annual volatility"
                      stroke="#9b5c35"
                    />
                    <Line
                      yAxisId="carbon"
                      dataKey="carbon_exposure_score"
                      name="Long-book carbon score (right axis)"
                      stroke="#167d8d"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p>
                Carbon score nonincreasing within tolerance:{" "}
                {sensitivity.carbon_nonincreasing ? "yes" : "no"}. Strict
                reduction across the tested range:{" "}
                {sensitivity.carbon_reduced
                  ? "yes"
                  : "no — constraints or equal scores can prevent a change"}
                .
              </p>
              <table>
                <thead>
                  <tr>
                    <th>λ</th>
                    <th>Expected annual return</th>
                    <th>Annual volatility</th>
                    <th>Carbon score</th>
                    <th>Gross / net</th>
                    <th>Solver status</th>
                  </tr>
                </thead>
                <tbody>
                  {sensitivity.portfolios.map((p) => (
                    <tr key={p.carbon_penalty}>
                      <td>{p.carbon_penalty}</td>
                      <td>{percent(p.expected_return_annual)}</td>
                      <td>{percent(p.volatility_annual)}</td>
                      <td>{score(p.carbon_exposure_score)}</td>
                      <td>
                        {percent(p.gross_exposure)} / {percent(p.net_exposure)}
                      </td>
                      <td>{p.solver_status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </article>
          )}
          {comparisonResponse && (
            <article>
              <h2>Research limitations</h2>
              <ul>
                {comparisonResponse.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </article>
          )}
        </div>
      </div>
    </section>
  );
}
