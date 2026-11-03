# Validation record — 3 November 2026

Executed locally with Python 3.12, Node 24, Docker Compose and PostgreSQL 16.

| Check | Result |
|---|---|
| Pytest: constraints, CSV validation, dates, idempotency, rollback, missing scopes, memberships, API filters/errors | 21 passed |
| Ruff lint and format check: app, tests, Alembic | Passed |
| Frontend Vitest: loading actual service results through mocked HTTP adapter, filtering, selection, errors/missing data | 4 passed |
| TypeScript strict check and Vite production build | Passed |
| npm audit | Zero known vulnerabilities after upgrading Vitest |
| Docker Compose image build/start and health | Passed |
| PostgreSQL initial Alembic upgrade | Passed |
| Upgrade → downgrade base → upgrade on separate carbon_migration_test database | Passed |
| Alembic check on PostgreSQL | No schema drift |
| Synthetic imports into PostgreSQL | 3 companies, 7 prices, 3 emissions inserted |
| Repeat same imports | 0 inserted; 3 / 7 / 3 skipped |
| python3 scripts/smoke.py | Passed against running Docker API/PostgreSQL |
| Live Chromium Company Explorer | Price and scope charts rendered; source/synthetic labels and null scope visible |
| Live sector filter and selected company | Pharmaceuticals yields one company and explicit missing-emissions state |
| Desktop and 390px mobile screenshots | Reviewed; responsive layout works |

Reproduce unit checks with README commands; run `python3 scripts/smoke.py` from the root after importing the documented synthetic fixture. The smoke script is read-only and expects exactly that sample dataset. Browser screenshots are local ignored artifacts in `output/playwright/`.

Nonblocking warnings: Vite reports a 644 kB minified main bundle, largely charting; consider lazy-loaded chart views when the dashboard grows. Starlette currently warns that its httpx TestClient adapter is deprecated; tests pass. No real datasets, provider access, license permissions or scientific conclusions have been validated. Real dataset analysis requires resolving the methodological checklist first.

A transient browser request failed while the API container was being rebuilt; reloading after startup succeeded. A missing favicon was fixed and the final page loaded without browser console errors. No essential check is blocked.


Task 02 validation supersedes these Phase 1 counts: see [real-data validation](real-data-validation.md) for 51 backend tests, five frontend tests, PostgreSQL migration/replay checks and acquisition blockers.
