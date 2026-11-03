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
