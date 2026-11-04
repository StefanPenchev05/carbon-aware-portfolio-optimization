# Roadmap

## Phase 1 — Foundation

PostgreSQL schema, migrations, provenance, validated CSV imports, coverage endpoints and Company Explorer. Confirm real research access and evaluate data quality before proceeding to analysis.

## Phase 2 — Correlation analysis

Define financial returns and emissions variables, implement publication-aware alignment, document missingness and normalization, then analyze statistical relationships and compare sectors. Include uncertainty, sample size and multiple-testing limitations. Test against small analytically known fixtures.

## Phase 3 — Portfolio optimization

Define traditional Long-Short objectives and constraints, add a documented carbon penalty, evaluate solver feasibility and sensitivity to penalty strength. Resolve short-position exposure treatment and prevent implicit leverage changes from confounding comparisons.

## Phase 4 — Complete interactive dashboard

Portfolio configuration, long/short position views, carbon-penalty controls and interactive traditional/carbon-aware comparisons. Expose assumptions, data provenance and optimizer feasibility to users.

## Phase 5 — Historical evaluation

Point-in-time returns, risk, carbon exposure and performance evaluation with transaction/shorting costs where justified. Address survivorship, look-ahead and revision bias; write research conclusions with limitations and reproducible experiments.

## Task 04 — exploratory analysis engine

Implemented read-only financial/carbon/correlation services, typed analysis endpoints, conservative evidence gates, Analysis tab and deterministic synthetic validation. See [statistical methodology](statistical-methodology.md) for formulas, threshold conventions and review configuration. Real Siemens remains statistically insufficient (no adjusted daily series, one company). Next: permitted complete price histories, comparable carbon disclosures across companies/years, reviewed calendars/boundaries and a justified inferential design. No optimizer or backtest has been added.

## Task 05 — fixed-sleeve Long–Short optimization

Implemented annual mean-variance optimization with CVXPY/Clarabel, a long-book relative carbon penalty, fixed-universe comparisons, penalty sensitivity, typed stateless API, Portfolio UI and deterministic eight-company synthetic validation. Real Siemens remains unavailable for optimization. See [portfolio methodology](portfolio-optimization.md). Next: permitted reviewed multi-asset daily histories, comparable publication-aware carbon disclosures and a formal evaluation protocol. Historical backtesting and trading remain unimplemented.

## Task 06 — historical evaluation engine

Implemented past-only rolling/expanding scheduling, monthly/quarterly decisions, dated historical-universe eligibility, optimizer reuse, self-financing signed P&L/drift, subsequent financial/carbon/turnover metrics, matched penalty comparisons, typed stateless API and Evaluation UI. Seeded historical scenarios are explicitly synthetic. Current real data cannot pass PIT/multi-asset readiness. See [historical evaluation](historical-evaluation.md). Next: permitted historical market/universe/disclosure evidence and independent validation/final-test protocols before empirical claims or penalty tuning.
