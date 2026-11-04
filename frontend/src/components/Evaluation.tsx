import { useEffect, useRef, useState } from "react";
import {
  Bar,
  BarChart,
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
  BacktestConfiguration,
  BacktestReadiness,
  BacktestResponse,
} from "../types/backtest";
const initial: BacktestConfiguration = {
  data_mode: "real",
  start_date: "2024-01-02",
  end_date: "2025-12-31",
  window: "rolling",
  training_sessions: 126,
  frequency: "monthly",
  risk_aversion: 3,
  carbon_penalty: 0.1,
  penalties: [0, 0.05, 0.1, 0.25],
  max_weight: 0.25,
  long_gross: 0.5,
  short_gross: 0.5,
  company_ids: [],
  sectors: [],
  min_assets: 4,
  min_candidates: 2,
  min_observations: 60,
  min_annual_observations: 252,
  shrinkage: 0.05,
  risk_free_rate: 0,
};
const pct = (v: number | null) =>
  v === null ? "Unavailable" : `${(100 * v).toFixed(2)}%`;
const num = (v: number | null) => (v === null ? "Unavailable" : v.toFixed(4));
export function Evaluation() {
  const [config, setConfig] = useState(initial);
  const [ready, setReady] = useState<BacktestReadiness | null>(null);
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [grid, setGrid] = useState("0, 0.05, 0.1, 0.25");
  const [ids, setIds] = useState("");
  const [step, setStep] = useState(0);
  const active = useRef<AbortController | null>(null);
  const mode = config.data_mode;
  const label =
    mode === "synthetic"
      ? "SYNTHETIC historical demonstration"
      : "Real historical evaluation";
  useEffect(() => {
    const c = new AbortController();
    setReady(null);
    setResult(null);
    setError("");
    setLoading(false);
    api
      .evaluationReadiness(mode, c.signal)
      .then((r) => {
        if (!c.signal.aborted) setReady(r);
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(String(e));
      });
    return () => {
      c.abort();
      active.current?.abort();
    };
  }, [mode]);
  function update<K extends keyof BacktestConfiguration>(
    key: K,
    value: BacktestConfiguration[K],
  ) {
    active.current?.abort();
    setLoading(false);
    setResult(null);
    setError("");
    setConfig((c) => ({ ...c, [key]: value }));
  }
  async function run() {
    active.current?.abort();
    const c = new AbortController();
    active.current = c;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const body = {
        ...config,
        penalties: grid
          .split(",")
          .filter((s) => s.trim())
          .map(Number),
        company_ids: ids
          .split(",")
          .filter((s) => s.trim())
          .map(Number),
      };
      const r = await api.evaluate(body, c.signal);
      if (c.signal.aborted) return;
      if (r.status !== "success") {
        setError(
          `${r.status}: ${r.message} ${r.readiness.blockers.join("; ")}`,
        );
        return;
      }
      setResult(r);
      setStep(0);
    } catch (e) {
      if (!c.signal.aborted) setError(String(e));
    } finally {
      if (!c.signal.aborted) setLoading(false);
    }
  }
  const baseline = result?.strategies.find((s) => s.carbon_penalty === 0);
  const aware = result?.strategies.find(
    (s) => s.carbon_penalty === result.configuration.carbon_penalty,
  );
  const performance =
    baseline && aware
      ? [
          { date: baseline.initial_date, traditional: 0, carbonAware: 0 },
          ...baseline.daily.map((d, i) => ({
            date: d.date,
            traditional: d.cumulative_return,
            carbonAware: aware.daily[i].cumulative_return,
          })),
        ]
      : [];
  const carbon =
    baseline && aware
      ? baseline.rebalances.map((r, i) => ({
          date: r.decision_date,
          traditional: r.target_portfolio.carbon_exposure_score,
          carbonAware:
            aware.rebalances[i].target_portfolio.carbon_exposure_score,
        }))
      : [];
  const b = baseline?.rebalances[step];
  const a = aware?.rebalances[step];
  const allocation =
    b && a
      ? b.target_portfolio.positions.map((p, i) => ({
          name: p.name,
          traditional: p.weight,
          carbonAware: a.target_portfolio.positions[i].weight,
        }))
      : [];
  return (
    <section aria-label="Historical evaluation">
      <div className="intro">
        <h1>Historical evaluation</h1>
        <p className="dataset-label">{label}</p>
        <p>
          Walk-forward training and subsequent signed portfolio P&amp;L. Zero
          trading, borrow and financing costs; weights drift between rebalance
          closes. No forecast or realizable-performance claim.
        </p>
      </div>
      <div className="portfolio-layout">
        <aside>
          <h2>Evaluation protocol</h2>
          <label>
            Evaluation dataset
            <select
              value={mode}
              onChange={(e) =>
                update("data_mode", e.target.value as "real" | "synthetic")
              }
            >
              <option value="real">Real corporate data</option>
              <option value="synthetic">SYNTHETIC history</option>
            </select>
          </label>
          <label>
            Evaluation start (first execution close)
            <input
              type="date"
              value={config.start_date}
              onChange={(e) => update("start_date", e.target.value)}
            />
          </label>
          <label>
            Evaluation end
            <input
              type="date"
              value={config.end_date}
              onChange={(e) => update("end_date", e.target.value)}
            />
          </label>
          <label>
            Training window
            <select
              value={config.window}
              onChange={(e) =>
                update("window", e.target.value as "rolling" | "expanding")
              }
            >
              <option value="rolling">Rolling</option>
              <option value="expanding">Expanding</option>
            </select>
          </label>
          <label title="Daily training returns, plus an initial price baseline. Training always ends before decision.">
            Training sessions
            <input
              type="number"
              min="60"
              max="756"
              value={config.training_sessions}
              onChange={(e) =>
                update("training_sessions", Number(e.target.value))
              }
            />
          </label>
          <label>
            Rebalance frequency
            <select
              value={config.frequency}
              onChange={(e) =>
                update("frequency", e.target.value as "monthly" | "quarterly")
              }
            >
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
            </select>
          </label>
          <label title="Annual mean-variance risk coefficient; identical for every penalty.">
            Evaluation risk aversion γ
            <input
              type="number"
              min="0"
              step=".5"
              value={config.risk_aversion}
              onChange={(e) => update("risk_aversion", Number(e.target.value))}
            />
          </label>
          <label title="Annual return-equivalent cost of the target long-book relative carbon score.">
            Evaluation carbon penalty λ
            <input
              type="number"
              min="0"
              max="10"
              step=".01"
              value={config.carbon_penalty}
              onChange={(e) => update("carbon_penalty", Number(e.target.value))}
            />
          </label>
          <label>
            Sector universe
            <select
              value={config.sectors[0] ?? ""}
              onChange={(e) =>
                update("sectors", e.target.value ? [e.target.value] : [])
              }
            >
              <option value="">All sectors</option>
              {["Energy", "Industrials", "Pharmaceuticals"].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <details>
            <summary>Exposure and sensitivity settings</summary>
            <label>
              Selected IDs (comma-separated; blank means all)
              <input
                value={ids}
                onChange={(e) => {
                  setIds(e.target.value);
                  update("company_ids", []);
                }}
              />
            </label>
            <label>
              Evaluation position cap
              <input
                type="number"
                min=".01"
                max="1"
                step=".01"
                value={config.max_weight}
                onChange={(e) => update("max_weight", Number(e.target.value))}
              />
            </label>
            <label>
              Evaluation long gross
              <input
                type="number"
                min=".01"
                max="2"
                step=".05"
                value={config.long_gross}
                onChange={(e) => update("long_gross", Number(e.target.value))}
              />
            </label>
            <label>
              Evaluation short gross magnitude
              <input
                type="number"
                min=".01"
                max="2"
                step=".05"
                value={config.short_gross}
                onChange={(e) => update("short_gross", Number(e.target.value))}
              />
            </label>
            <label>
              Evaluation sensitivity penalties
              <input
                value={grid}
                onChange={(e) => {
                  setGrid(e.target.value);
                  update("penalties", []);
                }}
              />
            </label>
            <label title="Effective annual assumption; blank disables Sharpe. Zero explicitly assumes no risk-free return.">
              Annual risk-free rate
              <input
                type="number"
                min="-.99"
                max="1"
                step=".01"
                value={config.risk_free_rate ?? ""}
                onChange={(e) =>
                  update(
                    "risk_free_rate",
                    e.target.value === "" ? null : Number(e.target.value),
                  )
                }
              />
            </label>
          </details>
          <button
            className="run-portfolio"
            disabled={loading || !ready || ready.status !== "ready"}
            onClick={run}
          >
            {loading ? "Evaluating…" : "Run walk-forward comparison"}
          </button>
        </aside>
        <div className="portfolio-results">
          {!ready && !error && (
            <p role="status">Checking historical evidence…</p>
          )}
          {ready && (
            <article>
              <h2>
                Historical readiness ·{" "}
                {mode === "synthetic" ? "SYNTHETIC" : "real"}
              </h2>
              <p>
                {ready.company_count} securities · {ready.price_count} prices ·{" "}
                {ready.adjusted_price_count} adjusted ·{" "}
                {ready.scheduled_periods} scheduled periods
              </p>
              <p className="provenance">{ready.provenance}</p>
              {ready.status !== "ready" && (
                <>
                  <p role="status">
                    Historical evaluation unavailable: insufficient verified
                    point-in-time inputs.
                  </p>
                  <ul>
                    {ready.blockers.map((x) => (
                      <li key={x}>{x}</li>
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
          {result && baseline && aware && (
            <>
              <article>
                <h2>Subsequent cumulative P&amp;L</h2>
                <p>
                  {label} · Initial reference equity 1{" "}
                  {result.reference_currency}, {result.configuration.start_date}
                  –{result.configuration.end_date}.{" "}
                  {baseline.financial.evaluation_periods} holding periods,{" "}
                  {baseline.financial.daily_observations} subsequent session
                  returns.
                </p>
                <div className="analysis-chart">
                  <ResponsiveContainer>
                    <LineChart data={performance}>
                      <XAxis dataKey="date" minTickGap={60} />
                      <YAxis tickFormatter={(v) => pct(Number(v))} />
                      <Tooltip formatter={(v) => pct(Number(v))} />
                      <Legend />
                      <ReferenceLine y={0} />
                      <Line
                        dataKey="traditional"
                        name="Traditional λ=0"
                        stroke="#285ca8"
                        dot={false}
                      />
                      <Line
                        dataKey="carbonAware"
                        name={`Carbon-aware λ=${result.configuration.carbon_penalty}`}
                        stroke="#167d8d"
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </article>
              <article>
                <h2>Realized risk and P&amp;L metrics</h2>
                <p>
                  {label} · Conditional zero-cost historical accounting; these
                  are subsequent outcomes, separate from the optimizer's
                  training estimates. Effective annual risk-free assumption:{" "}
                  {result.configuration.risk_free_rate === null
                    ? "none; Sharpe disabled"
                    : pct(result.configuration.risk_free_rate)}
                  .
                </p>
                <table>
                  <thead>
                    <tr>
                      <th>Metric</th>
                      <th>Traditional</th>
                      <th>Carbon-aware</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(
                      [
                        [
                          "Cumulative signed-equity return",
                          baseline.financial.cumulative_return,
                          aware.financial.cumulative_return,
                          "percent",
                        ],
                        [
                          "Annualized geometric return",
                          baseline.financial.annualized_return,
                          aware.financial.annualized_return,
                          "percent",
                        ],
                        [
                          "Annualized volatility",
                          baseline.financial.annualized_volatility,
                          aware.financial.annualized_volatility,
                          "percent",
                        ],
                        [
                          "Maximum drawdown (loss magnitude)",
                          baseline.financial.maximum_drawdown,
                          aware.financial.maximum_drawdown,
                          "percent",
                        ],
                        [
                          "Sharpe ratio",
                          baseline.financial.sharpe_ratio,
                          aware.financial.sharpe_ratio,
                          "number",
                        ],
                        [
                          "Total traded notional / equity (L1)",
                          baseline.financial.turnover_l1_total,
                          aware.financial.turnover_l1_total,
                          "number",
                        ],
                        [
                          "Average gross exposure (drifted)",
                          baseline.financial.average_gross_exposure,
                          aware.financial.average_gross_exposure,
                          "percent",
                        ],
                        [
                          "Average net exposure (drifted)",
                          baseline.financial.average_net_exposure,
                          aware.financial.average_net_exposure,
                          "percent",
                        ],
                        [
                          "Average long position count",
                          baseline.financial.average_long_positions,
                          aware.financial.average_long_positions,
                          "number",
                        ],
                        [
                          "Average short position count",
                          baseline.financial.average_short_positions,
                          aware.financial.average_short_positions,
                          "number",
                        ],
                      ] as [string, number | null, number | null, string][]
                    ).map(([name, x, y, format]) => (
                      <tr key={name}>
                        <th>{name}</th>
                        <td>{format === "percent" ? pct(x) : num(x)}</td>
                        <td>{format === "percent" ? pct(y) : num(y)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {baseline.financial.annualization_reason && (
                  <p>{baseline.financial.annualization_reason}</p>
                )}
              </article>
              <article>
                <h2>Long-book carbon proxy trajectory</h2>
                <p>
                  {label} · Target scores at each rebalance. Universe or ranking
                  changes:{" "}
                  {aware.carbon.score_definition_changed ? "yes" : "no"}.
                  Across-date levels do not measure emissions reduction.
                </p>
                <div className="analysis-chart">
                  <ResponsiveContainer>
                    <LineChart data={carbon}>
                      <XAxis dataKey="date" minTickGap={60} />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line dataKey="traditional" stroke="#285ca8" />
                      <Line
                        dataKey="carbonAware"
                        name="Carbon-aware"
                        stroke="#167d8d"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <p>
                  Mean rebalance score: traditional{" "}
                  {num(baseline.carbon.average_rebalance_score)}, carbon-aware{" "}
                  {num(aware.carbon.average_rebalance_score)}. Mean paired
                  difference{" "}
                  {num(aware.carbon.average_paired_difference_from_baseline)}.
                  Shorts never offset this proxy.
                </p>
              </article>
              <article>
                <h2>Allocation history and training audit</h2>
                <p>
                  {label} · Positive long / negative short target weights.
                  In-sample expectations below are not holding-period P&amp;L.
                </p>
                <label>
                  Rebalance date
                  <select
                    value={step}
                    onChange={(e) => setStep(Number(e.target.value))}
                  >
                    {baseline.rebalances.map((s, i) => (
                      <option value={i} key={s.decision_date}>
                        {s.decision_date}
                      </option>
                    ))}
                  </select>
                </label>
                {b && a && (
                  <>
                    <p>
                      Training {b.training_start}–{b.training_end};
                      decision/execution {b.decision_date}; holding through{" "}
                      {b.holding_end}. {b.in_sample.observations} training
                      returns; {b.eligible_ids.length} eligible securities.
                    </p>
                    <p>
                      In-sample expected annual returns:{" "}
                      {pct(b.target_portfolio.expected_return_annual)} /{" "}
                      {pct(a.target_portfolio.expected_return_annual)}.
                      Subsequent holding-period signed-equity returns:{" "}
                      {pct(b.realized_period_return)} /{" "}
                      {pct(a.realized_period_return)}.
                    </p>
                    <div className="analysis-chart">
                      <ResponsiveContainer>
                        <BarChart data={allocation}>
                          <XAxis dataKey="name" hide />
                          <YAxis tickFormatter={(v) => pct(Number(v))} />
                          <Tooltip formatter={(v) => pct(Number(v))} />
                          <Legend />
                          <ReferenceLine y={0} />
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
                          <th>Traditional target</th>
                          <th>Carbon-aware target</th>
                          <th>Carbon-aware pretrade drift</th>
                          <th>Carbon-aware change</th>
                        </tr>
                      </thead>
                      <tbody>
                        {b.target_portfolio.positions.map((p, i) => (
                          <tr key={p.company_id}>
                            <td>
                              {p.name} ({p.company_id})
                            </td>
                            <td>{pct(p.weight)}</td>
                            <td>
                              {pct(a.target_portfolio.positions[i].weight)}
                            </td>
                            <td>
                              {pct(
                                a.pretrade_weights[String(p.company_id)] ?? 0,
                              )}
                            </td>
                            <td>
                              {pct(a.weight_changes[String(p.company_id)] ?? 0)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <details>
                      <summary>
                        Exits, exclusions, original carbon and sector
                        allocations
                      </summary>
                      <p>
                        All traded signed-weight changes (includes exited
                        securities): {JSON.stringify(a.weight_changes)}
                      </p>
                      <p>Exclusions: {JSON.stringify(a.exclusions)}</p>
                      <table>
                        <thead>
                          <tr>
                            <th>Company</th>
                            <th>Original S1 / market S2</th>
                            <th>tCO2e</th>
                            <th>Score</th>
                            <th>Publication / reporting year</th>
                          </tr>
                        </thead>
                        <tbody>
                          {a.in_sample.assets.map((x) => (
                            <tr key={x.company_id}>
                              <td>{x.name}</td>
                              <td>
                                {x.original_emission.scope1} /{" "}
                                {x.original_emission.scope2}{" "}
                                {x.original_emission.units}
                              </td>
                              <td>{x.emissions_tco2e}</td>
                              <td>{num(x.carbon_score)}</td>
                              <td>
                                {x.disclosure_date} / {x.disclosure_year}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <table>
                        <thead>
                          <tr>
                            <th>Sector</th>
                            <th>Traditional long / short / net</th>
                            <th>Carbon-aware long / short / net</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(b.sector_allocations).map(
                            ([s, v]) => (
                              <tr key={s}>
                                <td>{s}</td>
                                <td>
                                  {pct(v.long)} / {pct(v.short)} / {pct(v.net)}
                                </td>
                                <td>
                                  {pct(a.sector_allocations[s].long)} /{" "}
                                  {pct(a.sector_allocations[s].short)} /{" "}
                                  {pct(a.sector_allocations[s].net)}
                                </td>
                              </tr>
                            ),
                          )}
                        </tbody>
                      </table>
                    </details>
                  </>
                )}
              </article>
              <article>
                <h2>Penalty sensitivity on the same evaluation protocol</h2>
                <p>
                  {label} · No “best λ” selection. These repeated comparisons do
                  not constitute an unbiased tuning procedure.
                </p>
                <div className="analysis-chart">
                  <ResponsiveContainer>
                    <LineChart
                      data={result.strategies.map((s) => ({
                        penalty: s.carbon_penalty,
                        return: s.financial.cumulative_return,
                        carbon: s.carbon.average_rebalance_score,
                      }))}
                    >
                      <XAxis dataKey="penalty" type="number" />
                      <YAxis
                        yAxisId="return"
                        tickFormatter={(v) => pct(Number(v))}
                      />
                      <YAxis yAxisId="carbon" orientation="right" />
                      <Tooltip />
                      <Legend />
                      <Line
                        yAxisId="return"
                        dataKey="return"
                        name="Cumulative signed return (left)"
                        stroke="#285ca8"
                      />
                      <Line
                        yAxisId="carbon"
                        dataKey="carbon"
                        name="Mean rebalance carbon score (right)"
                        stroke="#167d8d"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <table>
                  <thead>
                    <tr>
                      <th>λ</th>
                      <th>Cumulative signed return</th>
                      <th>Annual volatility</th>
                      <th>Mean target carbon proxy</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.strategies.map((s) => (
                      <tr key={s.carbon_penalty}>
                        <td>{s.carbon_penalty}</td>
                        <td>{pct(s.financial.cumulative_return)}</td>
                        <td>{pct(s.financial.annualized_volatility)}</td>
                        <td>{num(s.carbon.average_rebalance_score)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </article>
              <article>
                <h2>Assumptions and limitations</h2>
                <ul>
                  {[...result.assumptions, ...result.warnings].map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </article>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
