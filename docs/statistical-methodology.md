# Statistical methodology — Task 04

This engine produces **exploratory descriptive associations**, not causal estimates, investable signals or validated portfolio strategies. Original observations remain unchanged. Real and explicitly synthetic observations are separated at source and company selection. Test fixtures are deterministic artificial observations, never research findings.

## Financial definitions

For consistently adjusted prices P, simple return is P(t)/P(t−1)−1 and log return is ln(P(t)/P(t−1)). The existing preparation helper rejects nonpositive/nonfinite prices, duplicated dates, mixed sources/currencies/adjustment regimes and unexpected weekend dates. Missing prices or expected sessions break the chain; there is no price or FX forward fill and no adjusted-close fallback to close. Provisional weekday-adjacent daily calculations are labelled; they do not establish exchange-calendar verification.

Cumulative simple return is product(1+r)−1. Pandas groups monthly/annual observed-window buckets; these are **partial-window summaries** when boundaries do not cover a complete month/year. Buckets are not annualized and are unavailable unless the entire selected window is complete and reviewed. The first price is a baseline, not a zero return. Returns are decimal fractions; UI percentages multiply by 100.

Annualized volatility is sample standard deviation of daily simple returns (ddof=1) × sqrt(252). It requires a complete reviewed session calendar, reviewed dividend/split/capital-action adjustment semantics and at least 60 valid daily returns by default. The 252 convention is a research convention, not an assertion of 252 actual sessions in each exchange year. Short but complete reviewed windows can yield exploratory cumulative return without volatility. Irregular sparse closes cannot yield daily volatility or annual correlation inputs.

Correlation financial windows are **calendar-year cumulative adjusted returns**, using the prior December final close as baseline and every session through the final December close of the selected year. No fiscal-year return convention is inferred from emission year labels. Reviewed calendar lists must enumerate the actual sessions, including the baseline. Date boundaries and inclusion are checked; calendar authenticity must be independently reviewed. All selected prices must be in that calendar; unexpected dates are rejected. Minimum thresholds cannot substitute for calendar completeness.

## Carbon measures and compatibility

Selected metrics: scope1, scope2, scope3, or explicitly scope1+2. The existing unit converter derives tCO2e (kg ×0.001, kt ×1,000, Mt ×1,000,000); original units/values remain available. Scope1+2 requires both values and an explicitly selected market-based or location-based Scope 2 basis. No substitution across bases; missing Scope 3 is not zero. Unknown provenance or unsupported units excludes the pair. Issuer-reported and estimated provenance remain distinguishable in the returned records; reported does not mean wholly measured.

Comparability requires an analyst-reviewed group identifying compatible organizational/consolidation boundaries, reporting-period interpretation and methodology for the selected scope. Different review groups are rejected together, including in panels. Textually identical method names alone do not prove compatibility. Exact methodology filtering is available. No revenue or other compatible denominator is stored, so intensity calculations are deliberately unavailable. Absolute emissions may mostly reflect company size; omitted size/industry variables limit interpretation.

## Timing and independent observations

Cross-section: exactly one company-return/carbon pair per selected year. Sector endpoint calculates separate Energy, Industrials and Pharmaceuticals cross-sections with the same thresholds. A coefficient is not exposed for a sparse sector merely because a pooled coefficient exists.

Panel: one company-year pair, descriptive coefficients only; at least three measurement years by default. Repeated firms/overlapping disclosures imply within-firm dependence; company-year count is not independent-company count. Duplicate company-year pairs are rejected, never averaged or counted as independent. Annual emissions are **never joined to each daily return for correlation**.

Point-in-time alignment reuses `align_emissions` at January 1, before the financial measurement window. Date-only publication must precede January 1 strictly; same-day/unknown/future availability is excluded. The most recent eligible reporting year/vintage within the explicitly selected source stream is used, preserving its actual disclosure year/date. Later comparative restatements are never backdated. Reviews select a specific immutable emission source/version and methodology; conflicting stream/vintage selection is rejected. There is no claim of intraday accuracy, first-publication completeness or automatic stale-disclosure expiry.

Retrospective (`descriptive`) mode selects the same **reporting-year label** as the financial window; it is explicitly marked potential look-ahead and does not assert fiscal/calendar interval equivalence. In both modes a review must establish the reporting-period interpretation. This is a fixed acquired universe, not a reconstructed historical STOXX universe. Survivorship, selection, omitted variables, sector composition, revision and publication biases remain.

## Statistical computation and inference

SciPy Pearson measures linear association using centered product moments. Spearman computes rank correlation with average ranks for ties. Pairwise missing/nonfinite values are excluded with counts; zero/near-zero variance, repeated company-period keys, too few companies/years/pairs or an invalid cross-section prevent calculation. The API returns coefficient null, not zero/NaN, for unavailable results. Valid pairs, unique companies, periods, exclusions and warnings accompany each result.

Default thresholds: 5 valid pairs, 5 distinct companies, 60 daily returns per annual input, 3 panel years. Query parameters may raise/lower exploratory thresholds, with floors 3/3/2/2. These are configurable screening conventions, **not power calculations or universal statistical guarantees**. `insufficient` blocks coefficients; `exploratory` allows descriptive coefficients or short complete reviewed financial windows; `computable` labels adequately sampled reviewed financial summaries. No correlation is promoted to confirmatory research merely by crossing a threshold.

The web API never infers random/independent sampling from imported rows, so its p-values are null. The pure `correlate` function permits a two-sided Pearson p-value only with explicit independently justified sampling and bivariate-normal inference assumptions. Spearman asymptotic p-values additionally require n > 500; smaller samples retain null significance (no unrequested permutation procedure). Panels always suppress iid inference, regardless of flags. Multiple comparisons, selection of metrics/year/sector and dependence require a separate preregistered inferential design; no confidence intervals are asserted.

Primary algorithm references: [SciPy Pearson](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html) and [SciPy Spearman](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html). In particular, small-sample Spearman asymptotic significance is not automatically trustworthy.

## Analyst review configuration

No corporate series is approved automatically. With no review file, the app still displays stored prices/carbon and actual coverage, but excludes unreviewed annual inputs. `ANALYSIS_REVIEW_FILE` optionally names a **local JSON review file**; Docker can reference `/data/private/analysis-review.json` via the existing read-only data mount. Store reviewer identity, dated evidence and calendar/adjustment/boundary rationale alongside it locally; true flags are attestations, not machine-generated verification. Do not approve a sparse series by supplying a sparse calendar. No raw dataset or ingestion schema is changed. Invalid configuration returns 503 and fails closed.

Structure (placeholder values are explanatory, not usable data or approval):

```json
{
  "real": {
    "<database company ID>": {
      "years": {
        "2024": {
          "expected_dates": ["<previous December final close>", "<every 2024 exchange session through December>"],
          "price_source_id": 0,
          "emission_source_id": 0,
          "methodology": "<exact stored methodology>",
          "adjustment_verified": false,
          "carbon_period_verified": false,
          "comparability_group": "<reviewed scope/boundary/reporting-period group>"
        }
      },
      "display": {
        "expected_dates": ["<every selected display-window session>"],
        "adjustment_verified": false
      }
    }
  },
  "synthetic": {}
}
```

`display` is optional and separate from annual correlation windows because the display-year selection starts within the year. To review multiple display years use the pure service with the appropriate complete calendar; the current API display review is a single explicit window and will reject mismatched selections. Price-source disambiguation for display is conservative: multiple regimes reject rather than silently choose. Source/version and methodology are explicit for annual pairs. The engine retains native currencies; mixed-currency return perspectives are rejected for pooled correlations. ECB quotes remain untouched; base-currency return transformation requires an explicit future reviewed convention.

## API and UI

GET `/api/analysis/readiness`, `/returns`, `/correlations`, `/sectors`. OpenAPI `/docs` exposes typed query and response schemas. Defaults are real data, year 2023, cross-section, publication-aware, Scope1+2 market-based. Select `start_year=2024&end_year=2024` for 2024. Cross-sections require equal years; panels require `mode=panel`. Filters: company_id, sector, metric, basis, exact methodology, alignment, synthetic, and min_pairs/min_companies/min_daily_returns/min_panel_years. Both coefficients are returned together. Missing company selections yield explicit insufficient results, not fabricated zeros. Inventory counts on readiness describe all acquired observations for selected companies; analysis pairs and return display use the requested window.

The Analysis tab shows real data only, year/sector/company-display/scope/basis/methodology/alignment controls, raw close and provisional daily return charts, financial coverage and original-disclosure limitations. Correlation scatter/coefficient display requires a computable descriptive coefficient. Company display selection only narrows detail charts; the cross-section remains the selected sector universe. Explorer is preserved. Synthetic fixtures are test-only; there is no UI switch that could present them as corporate findings.

## Current Siemens readiness

Siemens has one real company, seven sparse **unadjusted** closes, zero adjusted prices, two annual Scope1/market-based Scope2 rows (FY2023/2024), no Scope3, and zero valid return/carbon pairs. Both comparative rows retain 2024-12-05 publication. Calendar, adjustment and cross-company comparability approvals are absent. Annual carbon cannot be multiplied by daily price-row count to increase n. The response/UI state is:

> Insufficient verified corporate observations for statistical analysis.

Needed next: permitted complete consistently adjusted daily prices with verified exchange calendars/adjustment settings; several distinct companies per sector and comparable annual disclosures over more years, compatible scope/boundary/fiscal-period evidence, historical vintages/publication dates and a justified sampling/inference design. Institutional Bloomberg export permission remains unconfirmed. Task 04 collects no new corporate data and changes none of the private raw files.

## Reproducible validation

`cd backend && .venv/bin/pytest -q`; `npm test --prefix frontend`; `npm run build --prefix frontend`; Ruff and Prettier checks. Deterministic explicitly synthetic fixtures cover +1/−1/orthogonal correlation, ties, constants, missingness, gaps/adjustments/currencies, sample volatility/cumulative math and overflow guards, panel significance suppression, pseudoreplication, future/unknown/same-day publication, retrospective labelling, normalized scopes/bases, sector sample sizes, invalid parameters/configuration and a fully reviewed synthetic annual API path. No test fixture is imported into the live database.

Executed on 3 November 2026: **75 backend tests and 6 frontend tests passed**; strict TypeScript/production build, Ruff (from backend project directory), Prettier and Git whitespace checks passed. Both existing live API smoke scripts and the manifest-based private Siemens verifier passed. All four analysis endpoints returned HTTP 200; live 2024 readiness confirmed one company, seven acquired prices, zero adjusted prices, two disclosures and zero eligible pairs. Chromium displayed the structured insufficiency, actual company coverage, selected carbon measure and publication/methodology details. Nonblocking existing warnings: Starlette/httpx TestClient deprecation and the Vite large main-chunk warning (about 662 kB after this change).
