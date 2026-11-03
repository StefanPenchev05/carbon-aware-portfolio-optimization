# Long–Short portfolio optimization — Task 05

This is an academic **in-sample estimation and optimization experiment**. It is not a historical backtest, forecast, recommendation or trading system. Real mode uses only eligible real observations; the separate eight-company synthetic demonstration never enters PostgreSQL and never mixes with Siemens.

## Formulation and conventions

Let L and S be fixed disjoint candidate groups covering the selected securities. Signed weights w are fractions of reference capital. Solve with CVXPY:

```
maximize  μᵀw − γ wᵀΣw − λ ∑ᵢ∈L cᵢ wᵢ
subject to
    0 ≤ wᵢ ≤ cap       i ∈ L
    −cap ≤ wᵢ ≤ 0      i ∈ S
    ∑ᵢ∈L wᵢ = long_gross
    ∑ᵢ∈S wᵢ = −short_gross
```

With γ ≥ 0, λ ≥ 0 and positive-semidefinite Σ, this is a concave maximization objective with affine constraints and passes CVXPY's disciplined convex programming check. There is no binary sign-selection variable, no equality on a convex absolute-value expression, and no redundant nonconvex gross constraint.

Gross exposure is long_gross + short_gross; net exposure is long_gross − short_gross. Default allocations are +0.5 and −0.5, giving 100% gross and zero net. This is **dollar neutrality, not market-beta neutrality**. Unequal sleeves are allowed and reported correctly. Short exposure is reported as a signed negative number; request `short_gross` is a positive magnitude. Candidate membership does not require each candidate to receive a strictly positive absolute weight. Carbon penalties can redistribute weights within the long sleeve but cannot move a security between the fixed sleeves.

Traditional optimization sets λ=0 and retains the same carbon-eligible universe, including when the penalty is zero. The carbon-aware comparison changes only λ: the selected universe, estimated means/covariance, carbon normalization, long/short groups, γ, caps and sleeve allocations are identical. Every experiment prepares inputs once before any solve. λ=0 comparisons reuse exactly the same result. The module boundary permits future signed-weight models or alternative carbon estimators without adding mixed-integer machinery now.

## Selection and feasibility

Automatic selection sorts estimated sample means descending, breaking exact ties by ascending immutable database/synthetic company ID. The upper ceil(N/2) are long candidates; the remainder are short candidates. Selection uses only the requested historical estimation window. Manual groups must be disjoint and partition every selected security; unknown, duplicate, overlapping or unassigned IDs are rejected rather than silently dropped. Selected-company filters are honored in both modes.

Each sleeve must have the required candidate count and `candidate_count × cap ≥ requested gross allocation`. These checks run before solving. The pure solver independently rechecks the partition and capacity. Defaults are four securities and two candidates per sleeve. Request floors permit two securities and one per sleeve for small, explicitly exploratory cases; one-company Siemens can never satisfy them. Per-position cap defaults to 0.25.

## Financial estimation and timing

Reuse `analysis.financial` and the existing return preparation helper. There is no duplicate price-return implementation. First selected price is a **baseline**; returns begin with the next valid session. Start/end must be reviewed price-calendar endpoints; all requested observations lie between them, and `end_date < as_of` strictly. Formation/as-of is when the proposed portfolio could be constructed using the estimates; no performance after formation is computed.

Every selected company requires:

- One explicitly selected price source with consistent currency and verified dividend/split/corporate-action adjustment semantics. There is no unadjusted-close fallback.
- A reviewed full session calendar, complete selected-window prices and at least 60 valid daily returns by default. User-configurable floor is 20; thresholds are prototype screening conventions, not universal adequacy guarantees.
- No forward fill or irregular sparse-return substitution. A missing required price, unexpected session, duplicate date or mixed regime rejects that asset and therefore the whole selected universe.

For different trading calendars, retain only **identical (previous_date, date) intervals** across all assets. End-date-only alignment could pair one-day with multi-day holiday returns; this implementation avoids that. Complete individual histories can lose intervals at this intersection, with per-asset drop counts reported. Common sample size must be at least max(min_observations, N+1). No pairwise-deletion covariance is used. An eligibility failure never silently changes the universe between traditional and carbon-aware results.

Daily simple return r = adjusted_price(t)/adjusted_price(t−1)−1. Historical baseline estimates:

```
μ_annual = 252 × arithmetic mean(daily simple returns)
Σ_sample_annual = 252 × sample covariance(daily simple returns, ddof=1)
Σ = (1−α)Σ_sample_annual + α diag(diag(Σ_sample_annual))
expected_return_annual = μ_annualᵀw
variance_annual = wᵀΣw
volatility_annual = sqrt(variance_annual)
```

Expected return is an **annualized arithmetic estimate**, not compounded or realized performance. The 252 convention matches existing analysis. Annualization assumes a stable daily process and ignores serial correlation; these are modeling assumptions. Historical means are noisy and candidate sorting introduces selection/estimation bias. There is no test period or post-formation performance claim.

All assets must have one common native currency perspective. Mixed currencies are rejected; ECB conversion is not silently added. These are returns relative to that currency and capital convention, not automatically EUR-investor returns.

## Covariance validity and shrinkage

Default α=0.05 shrinks off-diagonal covariances 5% toward a diagonal target while retaining sample variances. This is a transparent fixed academic stabilizer, not an estimated optimal shrinkage coefficient; request α∈[0,1], and the same value/matrix is used for every λ. Insufficient observations are rejected rather than rescued by shrinkage.

Dimensions, finiteness and symmetry are checked. Let scale=max(max(abs(Σ)),1e−12). A negative eigenvalue below −1e−10×scale is materially indefinite and rejected. Only negative eigenvalues within that relative roundoff tolerance are clipped to zero, with repair metadata. Singular positive-semidefinite covariance is allowed; bounded sleeves still keep the problem bounded. No arbitrary diagonal ridge conceals invalid covariance. Reported covariance, shrinkage, repair, sample size and window make the inputs reviewable.

## Carbon measurement and availability

Use **reported Scope 1 plus reported market-based Scope 2**, normalized through the existing converter to tCO2e. Both values must exist, be finite/nonnegative and have compatible reviewed organizational boundaries, methods and reporting-period interpretation. Unknown/provider-estimated provenance and location-based Scope 2 cannot substitute. An issuer's `reported` flag describes provenance and does not imply every underlying measurement is actual; issuer estimation/extrapolation notes remain in the original record. Scope 3 stays separate and does not enter this objective.

A local analyst review selects a single emission source/version, exact methodology and shared comparability group. `align_emissions(..., mode="point-in-time")` chooses the latest eligible year/vintage with a **known publication date strictly before as_of**. Date-only same-day disclosures are excluded. Later comparative restatements are not backdated. Original scope values, units, status, publication date, methodology, reporting year and source descriptions remain in output, separate from derived tCO2e and relative scores. No disclosure staleness limit or historical source-publication archive is inferred. Current adjusted-price/source vintages are not proof of what a historical investor knew; source-version review and historical membership remain unresolved for future backtests.

The carbon measure is evaluated at formation, not repeated against each daily return. A disclosure may occur within the estimation window if it was available before formation. This does not imply the portfolio existed during that window.

## Score normalization and environmental interpretation

Over the **entire fixed selected universe**, including short candidates:

```
cᵢ = (average_rank(emissions_tco2eᵢ) − 1) / (N−1)
C(w) = ∑ᵢ∈L cᵢ wᵢ
```

Ranks increase with emissions. Ties receive average ranks; if every measurement is equal all scores are 0.5. Scores lie in [0,1], and C lies approximately in [0,long_gross]. A zero score means lowest relative rank, not zero emissions. Changing the selected universe changes relative scores; comparisons only have the intended meaning within the same fixed experiment.

The proxy penalizes **long-book holdings only**. Short-side emissions and scores are displayed for context but never subtracted from C or advertised as atmospheric offsets. The number is not revenue intensity, ownership-adjusted financed emissions, avoided emissions, real-world decarbonization or a complete environmental footprint. Absolute emissions reflect corporate scale and sector as well as operations. A future compatible denominator/ownership methodology would be a separate estimator, not a relabeling of ranks.

## Objective units and penalty scale

μ is annual decimal arithmetic return, Σ annual decimal-return variance, w and c dimensionless. γ converts the annual variance term into annual return-equivalent utility; λ is **annual return-equivalent cost per unit of weighted relative carbon score**. For example λ=0.01 and C=0.5 deduct 0.005, or 0.5 annual percentage points, from the objective. This is a chosen preference scale, not a carbon price or monetary environmental damage estimate. Defaults γ=3, λ=0.1 are illustrative and not recommendations.

Annual rather than daily objective units are used consistently. Changing annualization without rescaling parameters changes the model. UI expected-return/volatility/weight percentages multiply fractions by 100; carbon scores remain raw dimensionless values.

## Solver and numerical safeguards

Use explicitly selected **Clarabel** through CVXPY (locked dependencies include other CVXPY solvers, but no silent solver fallback). Check DCP before solving. Clarabel absolute/relative gap and feasibility tolerances are 1e−10, max_iter=300, warm starts disabled. Only `optimal` is accepted; `optimal_inaccurate`, infeasible, unbounded, exceptions, missing or nonfinite weights fail without a successful portfolio.

After solving independently verify dimensions, finiteness, sleeve signs, per-position caps and exact sleeve sums to **1e−7 absolute weight tolerance**. Recompute return, variance, volatility, gross/net and long-only carbon from the accepted raw weights. Report maximum constraint violation and solver status. Tiny sign/exposure residuals can remain within that tolerance; no discretionary rounding/reallocation changes the solution. Tiny negative derived variance/carbon from floating arithmetic is clipped only within tolerance. Failed comparisons/sensitivity runs return no partial successful portfolio set.

Semidefinite/zero-risk or γ=0 cases may have multiple optimal portfolios. Solver/version/platform changes may choose different weights among equivalent optima; deterministic IDs/seeds/solver settings improve reproducibility but do not prove unique solutions.

Primary implementation references: [CVXPY DCP rules](https://www.cvxpy.org/tutorial/dcp/index.html), [CVXPY solver options/status](https://www.cvxpy.org/tutorial/solvers/index.html). Convexity is checked programmatically as well as by the formulation.

## Sensitivity and fair comparison

Default λ grid: [0,0.01,0.05,0.1,0.25]. It is configurable (1–20 finite entries in [0,10]); zero is always added and values sorted/deduplicated. Solve every value with identical financial data, scores, groups and constraints. Report all weights/positions, annual expected return/variance/volatility, carbon score, signed sleeves, gross/net, solver status and residuals. The zero-grid solution matches traditional optimization within numerical tolerance (identical cache reuse within an experiment).

At exact optima, increasing a nonnegative linear penalty cannot increase its penalized proxy with the same feasible set; numerical verification checks nonincrease to 1e−7. Strict improvement is not guaranteed: caps, fixed sleeves or equal scores may leave no room to change C. Report both nonincreasing and strictly-reduced flags. Return and risk need not move monotonically. No frontier point is an out-of-sample result.

Comparison reports changes in expected annual return, volatility, carbon score, signed long/short allocations, each signed weight and total absolute weight difference. That L1 composition distance is not an executed turnover or transaction-cost estimate.

## Synthetic data and example

`data/synthetic/portfolio-v1.json` is explicitly artificial, separate from `data/real`, `data/private` and all database observations. `synthetic_portfolio.py` generates it and the API's in-memory demonstration from NumPy seed **20261103**. Eight fictitious companies span the three project sectors. There are 261 simulated weekday prices per company (2,088 total), giving **260 common returns** from 2024-01-02 through 2024-12-31. The artificial calendar includes weekdays without real exchange holidays and must never approve a real series.

Center/scale seeded common-factor and idiosyncratic shocks to distinct annual sample means [0.22,0.18,0.14,0.10,0.02,−0.02,−0.06,−0.10] and volatilities [0.24,0.20,0.18,0.16,0.18,0.22,0.26,0.30]. Price paths compound those simulated daily returns. Annual synthetic emissions have different magnitudes, one consistent synthetic market-based boundary and explicit simulated publication dates. Automatic default groups are IDs 10001–10004 long and 10005–10008 short. Those names and IDs are not actual issuers/constituents.

Illustrative default output (γ=3, sleeves ±0.5, cap=0.25, α=0.05):

| SYNTHETIC in-sample estimate | Traditional λ=0 | Carbon-aware λ=0.1 |
|---|---:|---:|
| Annual arithmetic expected return | 13.3784% | 11.8225% |
| Annual volatility | 10.5835% | 9.3030% |
| Long-book relative carbon score | 0.419158 | 0.304402 |
| Gross / net | 100% / ~0% | 100% / ~0% |

These values validate software behavior, not an empirical carbon/return relationship. Runtime generation is checked against the stored version in tests. Reproduce with the locked NumPy/solver environment; floating-point/platform differences can affect final digits.

## Real-data readiness and analyst reviews

The current Siemens pilot has **one real company, seven sparse unadjusted closes, zero adjusted closes and two annual disclosures**. It cannot provide a multi-asset aligned return matrix or fund eligible long and short sleeves. Real optimization returns structured `insufficient`, with no weights/expected-performance outputs. The UI disables real-mode optimization for the current dataset. Synthetic and real company selections cannot cross modes; unknown selected IDs block the entire run.

Future eligible real data requires a local `PORTFOLIO_REVIEW_FILE`. Docker passes this optional environment variable and the existing read-only `/data` mount can expose `/data/private/portfolio-review.json`. No review is approved by default. Format:

```json
{
  "real": {
    "<company database ID>": {
      "expected_dates": ["<every reviewed price session, including the initial baseline>"],
      "price_source_id": 0,
      "emission_source_id": 0,
      "methodology": "<exact stored methodology>",
      "adjustment_verified": false,
      "carbon_period_verified": false,
      "comparability_group": "<reviewed compatible scope/boundary/period group>"
    }
  }
}
```

Placeholders are not runnable approval data. Retain reviewer identity, dated source/adjustment/calendar evidence, usage permission and boundary rationale alongside the local review. True flags are analyst attestations, not automatic certification. Full calendars may cover multiple estimation windows; selected endpoints must lie within them. A deliberately sparse calendar must not be used to promote sparse closes into daily history. Invalid review JSON/schema fails closed. Existing Task 04 `ANALYSIS_REVIEW_FILE` remains separate because its annual correlation windows have a different purpose. Original/private datasets and ingestion schemas are unchanged.

## API and UI

GET `/api/portfolio/readiness` accepts the request configuration as typed query parameters; default is real mode. POST `/api/portfolio/optimize`, `/compare`, `/sensitivity` accept a typed JSON `PortfolioRequest` (see `/docs`). Parameters include mode/company IDs, baseline/start/end/formation dates, γ, λ, position cap, sleeve allocations, automatic/manual groups, sensitivity grid, fixed carbon metric, min_assets, min_candidates, min_observations and covariance shrinkage.

Malformed/unknown fields, negative/nonfinite parameters, invalid dates and overlapping IDs return HTTP 422 validation errors. Valid research requests return typed HTTP 200 envelopes with explicit `success`, `insufficient`, `infeasible`, `invalid_inputs` or `solver_error` status; clients **must inspect status before showing results**. Only success has the corresponding result. Estimates include annual covariance, assets/original carbon/source details, window/sample/selection metadata. Operations are stateless calculations; POST does not save a portfolio or alter observations. CORS allows POST alongside existing GET.

The Portfolio tab provides dataset, company and manual-side controls, dates, γ/λ, caps, sleeve allocations and sensitivity grid. Result charts use actual backend responses: signed allocations, side-by-side financial estimates/carbon table, λ sensitivity with separate financial/carbon axes, and signed composition differences. Tables expose positions, emissions versus scores, solver status, dates and sample size. Synthetic labels appear at entry points and every result visualization. Missing/failed results show reasons; no functioning real-mode calculation is offered for today's insufficient data. Changing configuration clears old results and aborts stale requests.

## Reproduction and validation

From repository root:

```sh
# Dependencies and local service
# Keep the existing configured .env; do not overwrite it.
docker compose up --build -d backend

# Generate the independent, explicitly synthetic artifact (no database import)
cd backend
.venv/bin/python -m app.services.synthetic_portfolio --output ../data/synthetic/portfolio-v1.json
.venv/bin/pytest -q
.venv/bin/ruff check app tests alembic ../scripts
.venv/bin/ruff format --check app tests alembic ../scripts
cd ..
npm test --prefix frontend
npm run build --prefix frontend
npm run format:check --prefix frontend
python3 scripts/smoke.py
python3 scripts/smoke_research.py
python3 scripts/smoke_portfolio.py
backend/.venv/bin/python scripts/validate_corporate_pilot.py data/private/siemens_pilot_v1
```

Example stateless API request:

```sh
curl -s http://localhost:8000/api/portfolio/compare \
  -H 'Content-Type: application/json' \
  -d '{"data_mode":"synthetic","risk_aversion":3,"carbon_penalty":0.1,"max_weight":0.25}'
```

Tests independently verify a four-security diagonal-covariance solution (weights [0.3,0.2,−0.25,−0.25] at λ=0; [0.2,0.3,−0.25,−0.25] at λ=0.4), expected return/variance/volatility, exposure constraints and correct carbon direction. Other coverage includes zero-penalty identity, fixed-cap non-improvement, tied ranks, covariance validity/roundoff repair/shrinkage, missing/sparse prices and carbon, incompatible methods/currencies/bases, disclosure timing/vintages, calendar-interval alignment, selected/manual universes, solver failures/inaccurate status/invalid weights, HTTP validation/CORS, mode isolation and frontend controls/insufficient/error states. Existing regression suites remain required.

## Limitations and next milestone

No transaction costs, borrow availability/fees, market-beta constraint, liquidity, turnover optimization, live trading, brokerage connection, accounts or production portfolio management. Rank scores omit intensity, ownership and much environmental context; emissions comparability and disclosure timeliness still require human evidence. Absolute-scope inputs and noisy historical means create scale/selection sensitivities. Current data cannot support genuine empirical portfolio findings.

Next milestone: acquire permitted consistent adjusted histories and comparable first-publication carbon disclosures for a reviewed multi-company universe, validate calendars/vintages/currencies and formalize an out-of-sample evaluation protocol before implementing historical evaluation. Institutional Bloomberg export permission remains unconfirmed.

### Executed validation — 3 November 2026

- **126 backend tests and 9 frontend tests passed**, including the complete pre-existing suites. Nonfinite JSON inputs are rejected with sanitized 422 errors rather than causing response-serialization failures.
- Strict TypeScript and production build, Ruff lint/format, Prettier and Git whitespace checks passed.
- Rebuilt Docker backend passed portfolio readiness/optimization/comparison/sensitivity checks, both previous live API smoke scripts and the manifest-based private Siemens verifier. Real readiness: 1 security, 7 prices, 0 adjusted prices and 0 aligned return observations. No successful real portfolio was returned.
- Live Chromium confirmed the real-mode disabled action/reasons, switching to explicitly SYNTHETIC mode, eight selected companies, functional solve controls, all result sections and actual API numbers. Desktop and mobile layouts were inspected.
- No raw/private dataset, observation table or schema migration changed. Existing synthetic Explorer samples and ECB observations remain separate and pass their regression checks.

Nonblocking warnings remain the Starlette/httpx TestClient deprecation and Vite's main-chunk-size warning (approximately 682 kB). This prototype does not assert production bundle/performance suitability.
