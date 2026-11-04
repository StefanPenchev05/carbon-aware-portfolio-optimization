# Historical evaluation — Task 06

The engine performs walk-forward evaluation under an explicit **zero-cost signed-equity accounting convention**. Synthetic results demonstrate software behavior, not empirical strategy performance. Real Siemens data remains insufficient. This is neither live trading nor a claim of achievable returns.

## Architecture and reuse

`backtest_schedule.py` constructs calendar windows; `backtest_data.py` handles past-only universe/source eligibility and calls the existing `portfolio_data.prepare`; `backtest_execution.py` calls Task 05 `portfolio_experiment.execute` and its CVXPY/Clarabel optimizer without reproducing the objective. Holding returns reuse `prepare_returns`. `backtest_accounting.py` isolates cash/notional accounting; `backtest_metrics.py` separates subsequent financial/carbon measurements; `backtest_engine.py` shares plans across strategy/penalty comparisons. A repository reads mode-isolated observations and historical attestations; typed schemas and thin HTTP routes expose results. No observation migration, new ingestion or experiment persistence is introduced.

Task 05 remains an **in-sample** optimizer. Task 06 adds subsequent holding-period outcomes, with those categories separate in API fields and UI labels. A strategy’s `target_portfolio`/`in_sample` contains pre-holding estimates. `realized_period_return`, `daily.realized_return` and `financial` contain subsequent signed P&L results.

## Dates, training and execution

Defaults: synthetic evaluation 2024-01-02–2025-12-31, 126 training returns (127 baseline-inclusive prices), rolling windows, monthly rebalancing, γ=3, λ=0.1, sleeves +0.5/−0.5 and cap 0.25. All exposure/estimator parameters can be configured; net target equals long_gross − short_gross and gross target equals their sum. Equal sleeves mean dollar neutrality, not beta neutrality or absence of risk.

The first evaluation session and then the first session in each new calendar month/quarter are decisions. A truncated first period is allowed. The last date is a mark-to-market endpoint, not a new empty holding interval. Each decision d uses training through the **previous session**, strictly before d. Rolling windows have the requested number of return intervals; expanding windows share the first window’s initial baseline. Training must have at least min_observations (default 60) and enough aligned returns for Task 05’s N+1 covariance requirement. Insufficient initial history rejects the experiment.

Targets are decided before the rebalance close using earlier prices and date-only disclosures published strictly before d. Execution is modeled **at d’s closing total-return price**, without slippage; target notionals are scaled to that close’s equity. This is an idealized closing execution convention, not a claim that an actual trader could submit exact closing-NAV orders. The decision-day close is used only as an execution/valuation baseline, never to fit means/covariance or rank candidates. A perturbation of decision-day/future prices cannot change that decision’s construction inputs.

An old portfolio earns P&L through the next rebalance close. It is then replaced self-financing at that close, and the new portfolio earns returns from the following session. Thus holding intervals are `(decision, next_decision]`, or `(decision, final_end]`; no return is counted twice and none is discarded between periods. All evaluation dates must be reviewed session endpoints. The prototype supports at most three evaluation years and 36 decisions.

## Point-in-time eligibility and historical universe

Before construction at every d:

1. Apply the requested company/sector universe; unknown IDs reject the request rather than being silently substituted.
2. Consider only universe events with effective date ≤ d and publication date < d. Latest effective/known event determines inclusion. Entry/exit must be documented, with verified coverage of the evaluation period; tied ambiguous events are rejected. Membership is checked at decisions; a mid-holding membership change is acted on at the next rebalance, not through an invented immediate trade.
3. Select an explicitly reviewed price/emission source specification known before d. Historical corporate-action/adjusted-price vintage and stable historical sector classification evidence are mandatory. Current data labels alone are not point-in-time evidence.
4. Require complete consistently adjusted training history using the existing financial checks. Apply only prior published carbon disclosures through `align_emissions`. Missing/unknown/future/same-day disclosure dates are excluded; later vintages are not backdated. Source/version selection is explicit, not a scan for the most convenient future disclosure.
5. Build the common eligible universe, normalize reported Scope1 + market-based Scope2 ranks over that universe, and reuse Task 05’s annual mean/covariance estimation and deterministic candidate selection. Report company-specific exclusions at each decision and aggregate reason counts.

The eligible universe can change with membership, available training history and disclosures. Such changes occur identically for all penalties. No eligibility rule consults future holding returns, future availability of prices or realized profitability. A later missing holding price causes an **all-or-nothing failure**; the engine never drops that asset or period and restarts to manufacture a surviving sample. Readiness includes a separate retrospective holding-data audit after past-only plans are formed; this audit checks completeness, not eligibility or construction.

A September 2026 STOXX snapshot is **never** treated as 2022–2025 membership. Real evaluation requires either a verified historical membership history or an explicitly documented historical research universe that makes no index-membership claim. The synthetic history uses the latter and is not called STOXX data. A retrospectively chosen fixed survivor sample would need a clear selection-bias justification; a current snapshot is not approved automatically.

## Calendars, corporate actions and currency

Training reuses identical `(previous_date,date)` return-interval alignment, not end-date-only joins or pairwise covariance deletion. The initial holding implementation requires the same reviewed session calendar for every held security. Missing or unexpected prices, altered price-adjustment/currency regimes or missing holding calendar coverage stop the experiment. Multi-exchange calendars with different holding holidays are unsupported rather than silently filled.

All selected assets and all rebalance periods must share one native currency reference. There is no implicit ECB conversion or forward fill. A currency change across decisions is rejected. A future base-currency implementation must incorporate correctly dated FX returns and financing conventions explicitly.

Adjusted-price units represent a verified consistent **total-return reinvestment unit**, not necessarily a literal fixed number of ordinary shares. Dividends are internally reinvested within this unit; short total-return liabilities include the corresponding dividend obligation. Real reviews must verify dividend/split/capital-action semantics and historical source vintage. Later revisions must not be approved as if available earlier merely because the underlying price date is old.

## Signed return accounting

Initial reference equity V₀=1. At a rebalance with equity V, target signed dollar notionals are nᵢ=Vwᵢ and cash is b=V−Σnᵢ. Positive n is long; negative n is a short liability. Short proceeds are included in the cash/collateral residual, **not added to equity a second time**. Cash may be negative under leveraged/non-neutral configurations; all cash interest, borrowing cost and short-proceeds rebates are assumed zero. No collateral segregation, margin constraints or borrow availability is asserted.

Between rebalance closes, adjusted-price units remain fixed:

```
nᵢ,t = nᵢ,t−1 × (1+rᵢ,t)
b_t = b_t−1
V_t = b_t + Σ nᵢ,t
P&L_t = Σ nᵢ,t−1 rᵢ,t
r_portfolio,t = P&L_t / V_t−1
wᵢ,t = nᵢ,t / V_t
```

No daily target-weight reset is hidden in the calculation. Weights, gross/net exposures and cash fractions drift. Caps and sleeve allocations are enforced at rebalances only. At the next trade, cash changes by minus the net change in signed notionals; no external capital is injected. Closed/exited securities appear in weight-change/turnover records even when no longer in the new universe.

Example: start +0.5 long/−0.5 short with cash=1. A +10% long return and +20% shorted-asset return produce n=(0.55,−0.60), equity=0.95 and portfolio return −5%. The short rise causes a loss. Drifted weights are 0.55/0.95 and −0.60/0.95, not ±0.5. If both assets next fall 10%, equity becomes 0.955. Rebalancing does not change that equity in the zero-cost model.

Nonpositive/nonfinite equity stops the whole experiment with `accounting_error`; no invalid compounded/annualized result or partially successful comparison is returned. This is especially relevant to short-loss risk. Zero net exposure does not make the book risk-free. The accounting module is isolated for future cost/financing/borrow extensions; no such costs are estimated or calibrated here.

## Realized financial metrics

All subsequent returns are conditional on the stated capital/execution assumptions, not unqualified realizable investment returns.

- Cumulative signed-equity return: V_end/V₀−1 = product(1+r_portfolio)−1.
- Annualized geometric return: (V_end/V₀)^(252/N)−1. This is **session-based 252/N annualization**, not ACT/365 calendar CAGR.
- Annualized volatility: sample standard deviation of subsequent daily portfolio returns (ddof=1) × sqrt(252).
- Maximum drawdown: max(1−V_t/running_peak(V)), including initial equity 1 in the peak history. Reported as a positive loss magnitude.
- Sharpe: mean(r_portfolio−r_f,daily) / sample_std(r_portfolio) × sqrt(252), with r_f,daily=(1+r_f,annual)^(1/252)−1. Risk-free rate is an explicit **benchmark assumption**, default 0; it does not accrue interest to the zero-cost book. `risk_free_rate=null` disables Sharpe. Zero variance also gives null Sharpe.
- Turnover: full L1 Σ|target_weight−drifted_pretrade_weight|, traded notional per pretrade equity. Includes initial establishment, excludes a terminal liquidation trade; it is not half-L1, realized fees or a transaction-cost estimate. Total and mean per rebalance are reported.
- Average gross/net exposures and active long/short counts: means of daily **post-return drifted** weights, with 1e−7 position-count threshold.

Annual return/volatility/Sharpe require a complete verified daily holding series and at least **252** returns by default; the API may raise this threshold but cannot lower it. Shorter or irregular series retain cumulative returns/drawdown/counts with annual statistics null and an explicit reason. Session annualization assumes stable moments and ignores serial correlation; sample length is a screen, not proof of estimator reliability. Historical results are never forecasts.

## Carbon metrics, sector and allocation changes

Reuse Task 05’s nonnegative universe-relative average-rank carbon scores and **target long-book** exposure only. Original scope measurements, units, normalized tCO2e, source/publication/reporting year and per-asset scores remain separate in `in_sample.assets`. Short holdings do not subtract carbon exposure or offset atmospheric emissions.

Report target score at every decision, arithmetic mean across rebalance points (not a time-weighted emissions quantity), and mean simultaneous difference from λ=0. This is not financed emissions, avoided emissions, carbon neutrality, intensity or real-world decarbonization. Within one date, strategies use the same universe and scores, so paired differences isolate that proxy’s objective effect. Across dates, constituent sets/ranks can change; `score_definition_changed` flags those changes. Even an unchanged rank score need not imply unchanged absolute emissions. No cumulative physical carbon saving is calculated.

Store every allocation, pretrade drift, signed change (including exits), turnover and signed long/short/net sector totals. The UI allows inspection of each date, with training estimates separate from subsequent holding-period P&L.

## Comparison and sensitivity

At every date all strategies share the eligible securities, training window, financial estimates/covariance, candidate selection, position caps, gross/net targets and carbon-score definition. Only λ changes. Compare adds λ=0 and selected λ to a configurable sensitivity grid; duplicate values are removed and sorted. A run request evaluates only the selected λ. No best-λ ranking, tuning, parameter search or empirical outperformance claim is made.

Up to six user grid entries plus the required zero/selected values are supported. All paths use identical historical periods. In-sample penalized scores should be nonincreasing with λ within solver tolerance; **realized returns/risk need not improve or move monotonically**. Selecting a winning λ from these same subsequent returns would bias the performance claim. Future tuning requires separate validation/final test periods or a properly nested procedure.

## Synthetic reference histories

`synthetic_history.py` and `data/synthetic/evaluation-v1.json` define a separate reference recipe, seed **20261106**, eight fictitious securities (IDs 20001–20008), and simulated weekdays 2022-01-03–2025-12-31. No real exchange holidays, STOXX membership or empirical company emissions are asserted. Runtime histories never enter PostgreSQL.

The generator uses predetermined rising/falling regimes, both positive and negative returns, changed common-factor correlations/volatilities, dated annual disclosures, and no full-history mean-centering or calibration from future returns. Synthetic History 08 enters the declared universe on 2024-07-01 after a 2024-06-15 announcement; History 07 exits on 2025-07-01 after a 2025-06-15 announcement. The July 2024 disclosure cannot affect the January/July 1 decisions; it first becomes eligible later. Numerical tests additionally inject future/same-day disclosures, missing training/holding data, ruin, insufficient history and independently calculable P&L/drawdown examples.

Default evaluation has **24** monthly periods and **521** subsequent session returns. Illustrative synthetic output (not empirical findings):

| SYNTHETIC subsequent zero-cost result | λ=0 | λ=0.1 |
|---|---:|---:|
| Cumulative signed-equity return | −2.7617% | −1.3194% |
| Annualized geometric return | −1.3455% | −0.6404% |
| Annualized volatility | 10.3554% | 10.5406% |
| Maximum drawdown | 14.5578% | 14.5726% |
| Mean target relative carbon score | 0.268948 | 0.253856 |

The artificial comparison does not establish a carbon-aware advantage. Both paths lose capital, and risk measures differ in direction; changing the seeded scenario or assumptions can change every outcome. Floating-point/solver-platform differences may affect final digits.

## Real readiness and local historical evidence

Current Siemens: one real company, seven sparse unadjusted prices, zero adjusted daily history, two annual carbon records, and one much later membership snapshot. There is no adequate historical universe, historical sector/source/corporate-action review or multi-security training/holding matrix. Real endpoints return `insufficient` with no fabricated allocations or performance. The UI disables the current real-mode evaluation action.

`BACKTEST_REVIEW_FILE` optionally supplies a local JSON review, mounted via the existing read-only data directory (e.g. `/data/private/history-review.json` inside Docker). Nothing is approved by default. This is separate from the Task 05 one-time optimization review. Structure:

```json
{
  "calendar": ["<every reviewed common session, including training prehistory>"],
  "coverage_start": "<verified historical universe coverage start>",
  "coverage_end": "<verified historical universe coverage end>",
  "universe_kind": "documented-research-universe",
  "universe_reference": "<dated evidence and historical selection justification>",
  "membership_history_verified": false,
  "historical_classification_verified": false,
  "membership_events": [
    {"company_id": 0, "effective": "<effective date>", "published": "<known availability date>", "active": true}
  ],
  "reviews": {
    "<company ID>": [{
      "known_from": "<historical availability of this source specification>",
      "expected_dates": ["<every reviewed session for the selected price version>"],
      "price_source_id": 0,
      "emission_source_id": 0,
      "methodology": "<exact stored methodology>",
      "adjustment_verified": false,
      "carbon_period_verified": false,
      "comparability_group": "<compatible organization/method/reporting-period group>",
      "historical_price_vintage_verified": false,
      "evidence": "<dated price/corporate-action and source-vintage evidence>"
    }]
  }
}
```

Placeholders are explanatory, not runnable data. The alternative `universe_kind` is `historical-index-membership`; either requires actual evidence and dated event history, not an undated/current constituent list. Sector classification must be verified stable over the evaluated period for the stored company labels; changing historical classifications require a future dated-classification adapter rather than using today’s labels. Review flags/known-from dates are human attestations requiring retained source evidence, reviewer identity and usage permissions; they do not mechanically certify truth. Immutable source versions must support historical price/action and emissions vintages. Invalid review files fail closed. No raw/private observations or their manifests are modified.

## API and interface

GET `/api/backtest/readiness` takes typed request/query fields. POST `/api/backtest/run` and `/compare` take typed `BacktestRequest` JSON. See `/docs`. Inputs cover mode, evaluation range, rolling/expanding training sessions, monthly/quarterly frequency, risk/carbon parameters, caps/sleeves, companies/sectors, observation thresholds, shrinkage, risk-free assumption and sensitivity grid.

Malformed/unknown/nonfinite parameters return 422; valid research requests return structured HTTP 200 envelopes with `success`, `insufficient`, `infeasible`, `invalid_inputs`, `solver_error` or `accounting_error`. Inspect status before reading results. Failures contain **no partial strategy set**. Readiness carries provenance, blocker/exclusion reasons and schedule dates. Successful paths include dated target allocations/estimates, original carbon data, drift/turnover, realized daily P&L, metrics and assumptions.

The Evaluation tab contains functional protocol controls, real/synthetic labels at entry and every visualization, cumulative signed P&L, target carbon trajectories, realized risk metrics, per-date allocation/training audit, sector/original-carbon detail and penalty sensitivity. Annualized unavailable results are labelled rather than replaced with zero. Changing a protocol clears old results and aborts stale requests. No chart is decorative or disconnected from computed API results.

## Reproduction

From the workspace root, retain the existing configured `.env`:

```sh
docker compose up --build -d backend
cd backend
.venv/bin/pytest -q
.venv/bin/ruff check app tests alembic ../scripts
.venv/bin/ruff format --check app tests alembic ../scripts
cd ..
npm test --prefix frontend
npm run build --prefix frontend
npm run format:check --prefix frontend
python3 scripts/smoke_backtest.py
python3 scripts/smoke_portfolio.py
python3 scripts/smoke.py
python3 scripts/smoke_research.py
backend/.venv/bin/python scripts/validate_corporate_pilot.py data/private/siemens_pilot_v1
```

Example:

```sh
curl -s http://localhost:8000/api/backtest/compare \
  -H 'Content-Type: application/json' \
  -d '{"data_mode":"synthetic","training_sessions":126,"frequency":"monthly","carbon_penalty":0.1,"penalties":[0,0.1]}'
```

## Research limitations and next actions

Historical means/covariance estimates remain noisy; repeated inspection of these results creates selection/parameter-overfitting risk. PIT filters cannot recover unarchived vintages or correct false source dates. Missing disclosures change eligibility; incomplete universe coverage, current surviving issuer selection and today’s labels can bias results. Real historical membership, stable classifications, corporate actions and usage permissions must be evidenced. Carbon ranks are relative, not environmental impact.

Costs, short-borrow availability/fees, recalls, collateral segregation, margin calls, financing, taxes, execution slippage and liquidity are omitted. No deep-learning forecast, best-penalty optimization, brokerage/live trading or cloud deployment is implemented. Next: acquire permitted multi-security adjusted histories, complete dated universe/source/disclosure evidence and a reviewed historical dataset; then reserve independent validation/final test data before tuning parameters or making empirical comparisons. Bloomberg export permission remains unconfirmed.

### Executed validation — 3 November 2026

**154 backend tests and 12 frontend tests passed**, including all prior suites. Strict TypeScript/production build, Ruff lint/format, Prettier and Git whitespace checks passed. Live Docker/API verification passed the default 24-period/521-return comparison, expanding/quarterly 8-period protocol, explicit null risk-free/Sharpe handling, short-window annualization suppression and the API’s 252-session annualization floor. The existing portfolio, Explorer/FX smoke checks and private Siemens manifest verifier passed unchanged.

Chromium confirmed the disabled real action and specific PIT/data blockers, switching to explicitly synthetic history, functional API-driven evaluation, all result sections, reference currency and training/holding labels. Desktop and mobile result layouts were inspected; mobile page width remains within its viewport. No raw/private dataset or observation schema changed. Nonblocking warnings remain the Starlette/httpx TestClient deprecation and Vite’s main-chunk warning (about 699 kB).
