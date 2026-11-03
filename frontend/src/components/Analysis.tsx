import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ScatterChart,
  Scatter,
} from "recharts";

import type { Correlation, Data } from "../types/analysis";
import { api } from "../services/api";
const value = (n: number | null, percent = false) =>
  n === null
    ? "Unavailable"
    : percent
      ? `${(100 * n).toFixed(2)}%`
      : n.toLocaleString(undefined, { maximumFractionDigits: 4 });
export function Analysis() {
  const [year, setYear] = useState(2024);
  const [sector, setSector] = useState("");
  const [company, setCompany] = useState("");
  const [metric, setMetric] = useState("scope1+2");
  const [methodology, setMethodology] = useState("");
  const [basis, setBasis] = useState("market-based");
  const [alignment, setAlignment] = useState("point-in-time");
  const [data, setData] = useState<Data | null>(null);
  const [correlation, setCorrelation] = useState<Correlation | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setCorrelation(null);
    setError("");
    const query = new URLSearchParams({
      start_year: String(year),
      end_year: String(year),
      metric,
      basis,
      alignment,
    });
    if (methodology) query.set("methodology", methodology);
    if (sector) query.set("sector", sector);
    api
      .analysis(query, controller.signal)
      .then(([d, c]: [Data, Correlation]) => {
        setData(d);
        setCorrelation(c);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(String(e));
      });
    return () => controller.abort();
  }, [year, sector, metric, basis, alignment, methodology]);
  const selected =
    data?.series.filter((s) => !company || String(s.company_id) === company) ??
    [];
  return (
    <section aria-label="Statistical analysis">
      <div className="intro">
        <h1>Statistical analysis</h1>
        <p>
          Real corporate data · exploratory research · native-currency annual
          returns
        </p>
      </div>
      <div className="analysis-filters">
        <label>
          Year
          <input
            type="number"
            min="1900"
            max="2199"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          />
        </label>
        <label>
          Sector
          <select
            value={sector}
            onChange={(e) => {
              setSector(e.target.value);
              setCompany("");
            }}
          >
            <option value="">All sectors</option>
            {["Energy", "Industrials", "Pharmaceuticals"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          Company display
          <select value={company} onChange={(e) => setCompany(e.target.value)}>
            <option value="">All companies</option>
            {data?.series.map((s) => (
              <option key={s.company_id} value={s.company_id}>
                {s.company}
              </option>
            ))}
          </select>
        </label>
        <label>
          Carbon scope
          <select value={metric} onChange={(e) => setMetric(e.target.value)}>
            {["scope1+2", "scope1", "scope2", "scope3"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          Methodology (exact text, optional)
          <input
            value={methodology}
            onChange={(e) => setMethodology(e.target.value)}
          />
        </label>
        <label>
          Scope 2 basis
          <select value={basis} onChange={(e) => setBasis(e.target.value)}>
            <option>market-based</option>
            <option>location-based</option>
          </select>
        </label>
        <label>
          Alignment
          <select
            value={alignment}
            onChange={(e) => setAlignment(e.target.value)}
          >
            <option value="point-in-time">
              Publication-aware at year start
            </option>
            <option value="descriptive">
              Retrospective reporting-year label
            </option>
          </select>
        </label>
      </div>
      {error && <p role="alert">{error}</p>}
      {!data && !error && <p role="status">Loading analysis…</p>}
      {correlation && (
        <article>
          <h2>Carbon and annual performance</h2>
          {correlation.message && <p role="status">{correlation.message}</p>}
          <p>
            {correlation.valid_pairs} valid pairs ·{" "}
            {correlation.distinct_companies} distinct companies ·{" "}
            {correlation.status}
          </p>
          <ul>
            {Object.entries(correlation.exclusions).map(([reason, count]) => (
              <li key={reason}>
                {reason}: {count}
              </li>
            ))}
            {correlation.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
          {correlation.coefficient_pearson !== null && (
            <>
              <p>
                Pearson {value(correlation.coefficient_pearson)} · Spearman{" "}
                {value(correlation.coefficient_spearman)} · Significance
                unavailable
              </p>
              <div className="analysis-chart">
                <ResponsiveContainer>
                  <ScatterChart>
                    <XAxis type="number" dataKey="x" name="Carbon (tCO2e)" />
                    <YAxis type="number" dataKey="y" name="Annual return" />
                    <Tooltip />
                    <Scatter data={correlation.points} fill="#167d8d" />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </article>
      )}
      {selected.map((s) => (
        <article key={s.company_id}>
          <h2>{s.company}</h2>
          <p>
            {s.price_count} prices · {s.valid_returns} provisional daily returns
            · Coverage {value(s.completeness, true)}
          </p>
          <p>
            Verified cumulative return {value(s.cumulative_return, true)} ·
            Annualized volatility {value(s.annualized_volatility, true)}
          </p>
          <ul>
            {s.blockers.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
          <h3>
            Observed closes (unadjusted) ·{" "}
            {s.daily[0]?.currency ?? "currency unavailable"}
          </h3>
          <div className="analysis-chart">
            <ResponsiveContainer>
              <LineChart data={s.daily}>
                <XAxis dataKey="date" />
                <YAxis domain={["auto", "auto"]} />
                <Tooltip />
                <Line dataKey="close" stroke="#285ca8" connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <h3>Daily returns (provisional unless reviewed)</h3>
          {s.valid_returns ? (
            <div className="analysis-chart">
              <ResponsiveContainer>
                <LineChart data={s.daily}>
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line
                    dataKey="simple_return"
                    stroke="#167d8d"
                    connectNulls={false}
                  />
                  <Line
                    dataKey="log_return"
                    stroke="#285ca8"
                    connectNulls={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p>No valid daily returns in the selected window.</p>
          )}
          <h3>Carbon disclosures · tCO2e</h3>
          <table>
            <thead>
              <tr>
                <th>Year</th>
                <th>Selected scope</th>
                <th>Publication</th>
                <th>Methodology / limitation</th>
              </tr>
            </thead>
            <tbody>
              {data?.carbon
                .filter((e) => e.company_id === s.company_id)
                .map((e) => (
                  <tr key={e.id}>
                    <td>{e.year}</td>
                    <td>{value(e.value)}</td>
                    <td>{e.disclosure_date ?? "Unknown"}</td>
                    <td>
                      {e.methodology} {e.issue}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </article>
      ))}
    </section>
  );
}
