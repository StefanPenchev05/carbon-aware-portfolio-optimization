import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Legend,
} from "recharts";
import type { Price, Emission, Source } from "../types/data";
export function Provenance({ source }: { source: Source }) {
  return (
    <p className="provenance">
      <strong>
        {source.synthetic
          ? "Synthetic demonstration"
          : "Real data · verification required"}
      </strong>{" "}
      · {source.name}
      <br />
      <span>
        Reference: {source.reference} · Imported{" "}
        {new Date(source.imported_at).toLocaleDateString()}
      </span>
      {source.retrieved_at && (
        <>
          <br />
          Retrieved {new Date(source.retrieved_at).toISOString()}
        </>
      )}
      {source.license_reference && (
        <>
          <br />
          Usage terms: {source.license_reference}
        </>
      )}
      {source.notes && (
        <>
          <br />
          {source.notes}
        </>
      )}
    </p>
  );
}
export function Observations({
  prices,
  emissions,
}: {
  prices: Price[];
  emissions: Emission[];
}) {
  // Separate sources, currencies and methodologies; never connect incompatible series.
  const priceGroups = group(
    prices,
    (p) => `${p.source.id} / ${p.currency} / ${p.adjustment_method}`,
  );
  const emissionGroups = group(
    emissions,
    (e) => `${e.source.id} / ${e.units} / ${e.methodology} / ${e.scope2_basis}`,
  );
  return (
    <>
      <section>
        <h2>Closing prices</h2>
        <p>Daily close in the reported currency. No currency conversion.</p>
        {!prices.length && (
          <p className="empty">No price observations available.</p>
        )}
        {[...priceGroups].map(([key, rows]) => (
          <div key={key}>
            <h3>{rows[0].currency}</h3>
            <div className="chart" role="img" aria-label="Closing price chart">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rows}>
                  <CartesianGrid vertical={false} stroke="#e1e8ee" />
                  <XAxis dataKey="date" />
                  <YAxis domain={["auto", "auto"]} />
                  <Tooltip />
                  <Line
                    dataKey="close"
                    name="Close"
                    stroke="#285ca8"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <Provenance source={rows[0].source} />
            <p className="provenance">
              Adjustment metadata: {rows[0].adjustment_method ?? "unknown"}
            </p>
            <details>
              <summary>Price observations</summary>
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Close</th>
                    <th>Adjusted close</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((p) => (
                    <tr key={p.date}>
                      <td>{p.date}</td>
                      <td>{p.close}</td>
                      <td>{p.adjusted_close ?? "Unavailable"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          </div>
        ))}
      </section>
      <section>
        <h2>Carbon emissions</h2>
        <p>Scopes remain separate. Missing disclosures are never zero.</p>
        {!emissions.length && (
          <p className="empty">
            No emissions observations available for this company.
          </p>
        )}
        {[...emissionGroups].map(([key, rows]) => (
          <div key={key}>
            <h3>
              {rows[0].units} · {rows[0].methodology} · Scope 2{" "}
              {rows[0].scope2_basis ?? "unknown"}
            </h3>
            <div
              className="chart"
              role="img"
              aria-label="Emissions by scope chart"
            >
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rows}>
                  <CartesianGrid vertical={false} stroke="#e1e8ee" />
                  <XAxis dataKey="year" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  {["scope1", "scope2", "scope3"].map((scope, i) => (
                    <Bar
                      key={scope}
                      dataKey={scope}
                      name={`Scope ${i + 1}`}
                      fill={["#167d8d", "#699bb2", "#9ba9c7"][i]}
                      isAnimationActive={false}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
            <Provenance source={rows[0].source} />
            <table>
              <thead>
                <tr>
                  <th>Year</th>
                  <th>Scope 1</th>
                  <th>Scope 2</th>
                  <th>Scope 3</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((e) => (
                  <tr key={e.year}>
                    <td>{e.year}</td>
                    {[e.scope1, e.scope2, e.scope3].map((v, i) => (
                      <td key={i}>
                        {v === null
                          ? "Unavailable"
                          : `${v.toLocaleString()} (${[e.scope1_status, e.scope2_status, e.scope3_status][i] ?? "unknown"})`}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.map((e) => (
              <p key={e.year} className="provenance">
                {e.year}: {e.notes || "No quality notes supplied."}
                <br />
                {e.disclosure_date
                  ? `Disclosure date: ${e.disclosure_date}`
                  : "Publication date unavailable; excluded from point-in-time analysis."}
                {e.disclosure_reference && (
                  <>
                    <br />
                    Disclosure: {e.disclosure_reference}
                  </>
                )}
              </p>
            ))}
          </div>
        ))}
      </section>
    </>
  );
}

function group<T>(rows: T[], key: (row: T) => string): Map<string, T[]> {
  const result = new Map<string, T[]>();
  for (const row of rows) {
    const k = key(row);
    result.set(k, [...(result.get(k) || []), row]);
  }
  return result;
}
