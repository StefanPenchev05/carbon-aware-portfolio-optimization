# Carbon-Aware Portfolio Optimization and Financial Analytics Platform

University of Luxembourg · Bachelor Semester Project · Winter 2026/2027

This research platform will investigate relationships between corporate emissions and financial performance across Energy, Industrials and Pharmaceuticals in a selected STOXX Europe 600 universe. Research questions include whether these relationships differ by sector and how a carbon penalty changes a Long-Short portfolio's risk, return and exposure.

Milestone 1 provides a Company Explorer, provenance-aware CSV ingestion, data coverage API and PostgreSQL foundation. Correlation, optimization and historical evaluation are future work. Company/price/emissions samples remain **synthetic**, not actual constituents or historical disclosures. Task 02 adds real ECB FX reference data and research-quality import/preparation infrastructure. Task 03 adds a private Siemens pilot: one real company, seven sparse unadjusted Xetra closes and two Scope 1/2 reporting years; full daily return history remains unavailable. This is academic software, not investment advice.

## Architecture and files

- `backend/app`: FastAPI routes → repositories → SQLAlchemy; Pydantic validation and Pandas CSV adapter.
- `backend/alembic`: versioned PostgreSQL schema, without automatic table creation at runtime.
- `frontend/src`: React/TypeScript Company Explorer, typed HTTP service and Recharts views.
- `data/samples`: small explicitly synthetic CSVs.
- `backend/tests`, `frontend/src/App.test.tsx`: ingestion, constraints, API and interface tests.
- `docs`: architecture, source-acquisition checklist, assumptions and staged roadmap.

## Quick start

Prerequisites: Docker with Compose, Node.js 22+, npm; Python 3.12+ for host development. No provider API keys are needed. Commands below start in the repository root.

```sh
cp .env.example .env
# Set POSTGRES_PASSWORD in .env to a local development password.
docker compose up --build -d
```

The backend waits for PostgreSQL and runs `alembic upgrade head` before serving. API: http://localhost:8000/api/health; OpenAPI: http://localhost:8000/docs.

Import the demonstration dataset (companies first):

```sh
for kind in companies prices emissions; do
  docker compose exec backend python -m app.services.ingest "$kind" "/data/samples/synthetic_${kind}.csv" --source "Synthetic demonstration v1" --reference "data/samples" --synthetic
done
```

Then start the frontend:

```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to the local backend. Optionally set `VITE_API_URL` before starting Vite for another backend; its origin must be included in backend `CORS_ORIGINS` (JSON list).

## Host backend development

Keep the Compose database running. From `backend/`:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -c requirements.lock -e '.[test]'
# Export DATABASE_URL with the user/password/database configured in Compose:
# postgresql+psycopg://USER:PASSWORD@localhost:5432/DATABASE
alembic upgrade head
uvicorn app.main:app --reload
```

Stop the Compose backend first to free port 8000: `docker compose stop backend`. Host imports use `python -m app.services.ingest` with `../data/samples/...` paths and the same flags. Each invocation is one transaction; invalid rows, unknown ISINs or conflicting duplicates roll back that file. Exact duplicates are counted and skipped. Source identity is an immutable name plus matching metadata. Correct a disclosure through a separately named source/version, rather than silently replacing it. `--real` labels externally obtained data but does not certify it.

Migrations: `docker compose exec backend alembic current`. For a new schema change, use host `alembic revision --autogenerate -m 'description'`, review its operations, then `alembic upgrade head`. Back up real data before downgrading; `alembic downgrade base` removes tables and data.

## Tests and checks

```sh
cd backend
.venv/bin/pytest -q
.venv/bin/ruff check app tests alembic
.venv/bin/ruff format --check app tests alembic
cd ../frontend
npm test
npm run build
npm run format:check
```

Python unit/API tests use isolated SQLite databases, with foreign keys enabled; the actual application uses PostgreSQL. See `docs/validation.md` for executed PostgreSQL migration and integration checks. `npm run build` includes strict TypeScript checking. Dependencies are captured in `frontend/package-lock.json` and `backend/requirements.lock`.

## API

GET `/api/companies?sector=Energy`, `/api/companies/{id}`, `/api/companies/{id}/prices?start=2025-01-01&end=2025-12-31`, `/api/companies/{id}/emissions?start_year=2023&end_year=2024`, and `/api/data/coverage`. Bounds are inclusive. Unknown companies return 404, invalid ranges 422, known companies without observations return empty arrays. Responses include explicit source and synthetic status. Coverage reports record counts and whether any scope has a value. No combined emissions total is inferred.

## Troubleshooting

- Compose rejects empty `POSTGRES_PASSWORD`: populate `.env`; it is ignored by Git.
- Connection refused: inspect `docker compose ps` and `docker compose logs backend db`; check ports 5432 and 8000.
- Changed password on an existing volume: PostgreSQL keeps its original credentials. Restore the original password or deliberately recreate the disposable sample database; deleting the volume destroys data.
- Empty Explorer: run all three imports and check `/api/data/coverage`.
- Import fails: check the row-number error, ISO dates, required headers and source metadata. Empty optional numeric cells become null. Do not encode missing data as zero.
- Browser request fails: verify API health, Vite proxy and configured CORS origin.

## Next milestones and limitations

Phase 2: point-in-time returns/emissions alignment, correlation and sector comparisons. Phase 3: traditional and carbon-aware Long-Short optimization. Phase 4: interactive portfolio dashboard. Phase 5: historical evaluation. See `docs/roadmap.md` and `docs/assumptions.md` before methodological implementation.

No real security prices, corporate emissions, constituent membership or correlations have been acquired or verified. ECB FX reuse conditions were checked and a real attributed FX bundle is included. Tiny samples test software behavior only and cannot support research conclusions. Authentication, backtesting and production deployment are outside this milestone. Git is initialized locally; creating a GitHub remote is left to the project owner.


## Task 02 — real-data acquisition and preparation

Read [real-data validation and blockers](docs/real-data-validation.md), [source review](docs/data-sources.md) and [manual-import instructions](docs/manual-data-import.md). **The corporate dataset is not ready for Phase 2B correlations.** No real company or disclosure was manufactured to reach the pilot target.

Replay the acquired ECB snapshot with no provider connection:

```sh
docker compose up --build -d
docker compose exec backend python -m app.services.ingest fx /data/real/ecb_2020_2025/real_fx.csv --manifest /data/real/ecb_2020_2025/manifest.json --real
docker compose exec backend python -m app.services.quality
```

This imports 7,690 real GBP/CHF/DKK/SEK/NOK reference quotes for 2020–2025; repeated imports skip exact duplicates. Source: European Central Bank. Rates are foreign units per EUR, selected/reshaped from its XML feed without changing values; see the bundle manifest for attribution and terms. Existing sample-import commands remain valid.

New API: `/api/data/quality` (real by default) and `?synthetic=true` (demo). Existing `/api/data/coverage` keeps the list response and adds per-company quality details. Company/emission/price responses add original classifications, disclosure dates, status/basis, adjustment metadata and source retrieval/terms. The Explorer shows unknown/estimated status and missing publication dates explicitly.

Preparation helpers provide daily simple/log returns, gap/duplicate checks, original-preserving emissions normalization, and descriptive versus point-in-time alignment. No statistical analysis is implemented. Real CSV imports require a manifest and exact ISIN matching/checksum; units, currency, unknown dates and methodology differences remain explicit. Header-only templates are in `data/templates/`; restricted exports belong in ignored `data/private/`.

After loading both documented datasets, run `python3 scripts/smoke.py` and `python3 scripts/smoke_research.py` for live API/PostgreSQL regression checks. These scripts validate the fixed synthetic demo and ECB bundle while allowing separately sourced corporate observations. Vite may select the next port if 5173 is occupied; use the URL printed at startup (the Task 02 browser check used 5174).


## Task 03 — first corporate observations

See [corporate pilot](docs/corporate-pilot.md) for exact sources, verified 2026-09-30 membership, identity/share-class decisions, private replay commands, validation counts and the Bloomberg export checklist. The live Explorer now includes Siemens AG alongside explicitly synthetic examples. Original/normalized emissions are separate, the report's estimation/extrapolation limitations are retained, and sparse prices do not generate daily returns. No migration or replacement ingestion framework was needed.

The private source/CSV bundle is present locally under ignored `data/private/siemens_pilot_v1/`; it is deliberately absent from public Git. Only source references/checksums/coverage are in `data/acquisition/`. Replay locally with the commands in the pilot document. **Not ready for correlation analysis:** daily adjusted prices and enough comparable annual disclosures are still required. The user confirmed Bloomberg export permission remains unconfirmed.
