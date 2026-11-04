import { Evaluation } from "./components/Evaluation";
import { Portfolio } from "./components/Portfolio";
import { Analysis } from "./components/Analysis";
import { useEffect, useState } from "react";
import { api } from "./services/api";
import type { Company, Price, Emission } from "./types/data";
import { Observations, Provenance } from "./components/Observations";
export default function App() {
  const [page, setPage] = useState("explorer");
  const [sector, setSector] = useState("");
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selected, setSelected] = useState<Company | null>(null);
  const [data, setData] = useState<{
    prices: Price[];
    emissions: Emission[];
  } | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setSelected(null);
    setCompanies([]);
    setData(null);
    api
      .companies(sector, controller.signal)
      .then((rows) => {
        setCompanies(rows);
        setSelected(rows[0] ?? null);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(String(e));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [sector]);
  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    setData(null);
    setError("");
    Promise.all([
      api.prices(selected.id, controller.signal),
      api.emissions(selected.id, controller.signal),
    ])
      .then(([prices, emissions]) => setData({ prices, emissions }))
      .catch((e) => {
        if (!controller.signal.aborted) setError(String(e));
      });
    return () => controller.abort();
  }, [selected]);
  return (
    <>
      <header>
        <div className="brand">Carbon-aware research</div>
        <span>University of Luxembourg · Winter 2026/27</span>
      </header>
      <main>
        <nav aria-label="Research pages" className="page-nav">
          <button
            aria-pressed={page === "explorer"}
            onClick={() => setPage("explorer")}
          >
            Explorer
          </button>
          <button
            aria-pressed={page === "analysis"}
            onClick={() => setPage("analysis")}
          >
            Analysis
          </button>
          <button
            aria-pressed={page === "portfolio"}
            onClick={() => setPage("portfolio")}
          >
            Portfolio
          </button>
          <button
            aria-pressed={page === "evaluation"}
            onClick={() => setPage("evaluation")}
          >
            Evaluation
          </button>
        </nav>
        {page === "evaluation" ? (
          <Evaluation />
        ) : page === "portfolio" ? (
          <Portfolio />
        ) : page === "analysis" ? (
          <Analysis />
        ) : (
          <>
            <div className="intro">
              <h1>Company explorer</h1>
              <p>
                Explore the financial and environmental data behind portfolio
                research.
              </p>
            </div>
            <div className="workspace">
              <aside>
                <label htmlFor="sector">Sector</label>
                <select
                  id="sector"
                  value={sector}
                  onChange={(e) => setSector(e.target.value)}
                >
                  <option value="">All sectors</option>
                  {["Energy", "Industrials", "Pharmaceuticals"].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
                <p className="count">
                  {companies.length}{" "}
                  {companies.length === 1 ? "company" : "companies"}
                </p>
                <nav aria-label="Companies">
                  {companies.map((c) => (
                    <button
                      key={c.id}
                      aria-pressed={selected?.id === c.id}
                      onClick={() => {
                        setData(null);
                        setSelected(c);
                      }}
                    >
                      <strong>{c.name}</strong>
                      <span>
                        {c.ticker} · {c.sector}
                      </span>
                    </button>
                  ))}
                </nav>
                {loading && <p role="status">Loading companies…</p>}
                {!loading && !companies.length && !error && (
                  <p>
                    No companies in this sector. Import a CSV dataset to begin.
                  </p>
                )}
              </aside>
              <article>
                {error && (
                  <p role="alert" className="error">
                    {error} Reload the page to retry.
                  </p>
                )}
                {selected && (
                  <>
                    <div className="company">
                      <h2>{selected.name}</h2>
                      <p>
                        {selected.sector} · {selected.exchange} ·{" "}
                        {selected.currency}
                      </p>
                      <p>
                        ISIN {selected.isin} · Ticker {selected.ticker}
                      </p>
                      {selected.original_sector && (
                        <p className="provenance">
                          Original classification: {selected.original_sector} (
                          {selected.classification_system ??
                            "taxonomy unavailable"}
                          )<br />
                          {selected.sector_mapping_notes}
                        </p>
                      )}
                      <Provenance source={selected.source} />
                    </div>
                    {data ? (
                      <Observations {...data} />
                    ) : (
                      !error && <p role="status">Loading observations…</p>
                    )}
                  </>
                )}
              </article>
            </div>
          </>
        )}
      </main>
      <footer>
        Academic research and experimentation. Data source labels describe
        provenance, not independent verification. No investment advice.
      </footer>
    </>
  );
}
