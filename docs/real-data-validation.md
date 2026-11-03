# Task 02: real-data validation and acquisition blockers

> Historical Task 02 snapshot. Task 03 has now acquired a private Siemens corporate pilot; see [current acquisition results](corporate-pilot.md). The older zero-company counts below describe the earlier run.
Review/acquisition date: **3 November 2026**. Infrastructure is delivered; a validated corporate correlation dataset is **not ready**.

## Sources and permissions

See [source review](data-sources.md) for primary links and the exact scope of each access decision. Confirmed facts: ECB permits attributed reuse; Mycelium limits systematic extraction; SRN's reviewed terms prohibit automated collection; STOXX provides an academic request form. Unavailable: university licences, a dated authorized constituent export, a verified price export and original checked emissions disclosures. No permission is inferred from an export button. No provider was contacted and no signup form was submitted.

## Selected companies and membership

**Zero real companies selected/imported; no verified membership dates.** The target remains roughly 12–18 across Energy, Industrials and Pharmaceuticals. A public top-components list does not supply the dated, ISIN-resolved selection evidence required here. The factsheets page advertises full component lists, but the fetched view did not expose a Europe 600 download link; this is an unresolved retrieval/permission issue, not a claim that every current constituent list is necessarily paywalled. No tentative company list is promoted to a pilot dataset, and no Healthcare-to-Pharmaceuticals shortcut was used.

The real-flagged rows in unit tests are isolated, explicitly documented software fixtures; their numeric values are not acquired observations and never enter the application database.

## Successfully acquired real data

Source: European Central Bank. Bundle: `data/real/ecb_2020_2025`.

- 7,690 FX observations: GBP, CHF, DKK, SEK and NOK, quoted in foreign units per EUR.
- Selected period: 2 January 2020 through 31 December 2025, 1,538 dates per currency.
- Original XML snapshot and exact CSV hashes, source, retrieval time and terms reference are retained in `manifest.json`.
- Transformation: select dates/currencies, reshape XML to CSV; do not alter quoted rate values. These are ECB reference observations, not executable transaction quotes.
- First import: 7,690 inserted. Repeat: zero inserted, 7,690 skipped.

## Actual quality report

Real company counts: Energy 0, Industrials 0, Pharmaceuticals 0. Real security prices 0; real corporate emissions 0; emissions years/scopes none; missing-publication counts 0 because there are no such records; reported/estimated percentages **null** because no denominator exists. Usable corporate matched observations 0. Real rejected import rows 0. FX rows 7,690. The original synthetic demo remains three companies, seven prices and three emissions records, separately labeled.

`quality-report.json` is a saved report of the local import state, not an immutable raw provider artifact. Regenerating it reflects the current database, including import attempts. Exact duplicate attempts are skipped; rejected-row metrics count whole rolled-back CLI batches and can count repeat attempts, not unique rejected source observations.

## Exclusions and unresolved questions

No restricted provider rows were collected for subsequent rejection. Mycelium/SRN exports were not ingested due to access terms; Yahoo terms were unavailable via HTTP 999 and Stooq showed browser verification. No restrictions were bypassed. Existing synthetic values remain unknown-status demonstration data and are not relabeled reported. Missing disclosure dates are excluded from point-in-time joins; unsupported emissions units are not normalized; ambiguous sources/bases/vintages require explicit selection. Missing price sessions break daily-return chains; without a supplied exchange calendar weekday expectations are provisional. Currency conversion is opt-in and requires exact-date matching quotes.

Still required: licensed constituent snapshot, security/issuer matching, source classification mapping, documented price adjustment and trading calendar, source-checked per-scope values, publication dates, fiscal boundaries, vintages/restatements and publication/storage rights. A permission statement in a manifest records the researcher's evidence; software does not certify a legal entitlement or source accuracy.

## Reproduce the exact acquired dataset

From the repository root, with `.env` configured as in the README:

```sh
docker compose up --build -d
docker compose exec backend python -m app.services.ingest fx /data/real/ecb_2020_2025/real_fx.csv --manifest /data/real/ecb_2020_2025/manifest.json --real
docker compose exec backend python -m app.services.quality
curl 'http://localhost:8000/api/data/quality'
curl 'http://localhost:8000/api/data/quality?synthetic=true'
```

Replay uses the committed snapshot and verifies checksums; it requires no provider connection. Repeating the import is idempotent. To regenerate the saved report from the host:

```sh
docker compose exec -T backend python -m app.services.quality > data/real/ecb_2020_2025/quality-report.json
```

For a **new** live acquisition, from `backend/` with its environment installed:

```sh
.venv/bin/python -m app.services.ecb ../data/real/ecb_new_snapshot --start 2020-01-01 --end 2025-12-31 --currencies GBP CHF DKK SEK NOK
```

The output directory must not exist. The feed can be revised, so a new acquisition is not guaranteed byte-identical to the saved bundle. On Python.org macOS installations with missing CA certificates, configure the system trust store or run with `SSL_CERT_FILE="$(.venv/bin/python -m certifi)"` in an environment containing certifi; never disable TLS verification. That CA-path configuration was used for the executed host acquisition after the initial default trust store failed.

Manual company-data acquisition/replay is documented in [manual workflow](manual-data-import.md). It is the supported route until a provider's permission and format are confirmed.

## Executed validation

| Executed check | Result |
|---|---|
| Full Pytest regression, including returns, missing data, status/basis, ISIN/currency matching, manifest tampering/immutability, CLI rollback audit, alignment and quality | **51 passed** |
| Frontend Vitest: existing behavior plus estimated/reported status, basis, missing dates and usage/source metadata | **5 passed** |
| Strict TypeScript + Vite production build | Passed |
| Ruff lint and format, frontend Prettier check, Git whitespace check | Passed |
| npm audit | Zero known vulnerabilities |
| PostgreSQL new migration applied to existing populated demo | Passed; old data preserved |
| New migration upgrade → downgrade to Phase 1 → upgrade on separate carbon_migration_test database | Passed |
| Alembic schema check on live and disposable PostgreSQL databases | No drift |
| Docker Compose image build/start | Passed |
| Legacy synthetic CLI reimports after migration | 0 inserted; 3 companies / 7 prices / 3 emissions skipped |
| Real ECB CSV/manifest replay in host and Docker CLI | 7,690 inserted initially, repeat imports 0 inserted / 7,690 skipped |
| `python3 scripts/smoke.py` | Passed against live PostgreSQL API |
| `python3 scripts/smoke_research.py` | Passed: real FX counts, zero real corporate rows, preserved synthetic panel and additive emission metadata |
| Live Chromium Explorer | Renders both charts, unknown status, Scope 2 basis and missing-publication warnings; mobile multi-company grid overflow found, fixed and screenshot reviewed |

Unit tests use isolated software fixtures, not verified external disclosures. The acquired ECB snapshot is separately checksum-verified and imported into PostgreSQL. Migration tests ran on a separate disposable database, preserving the live synthetic demo and FX data. Run smoke scripts after importing the documented synthetic demo and ECB bundle; they intentionally assert that exact pilot state.

Resolved execution issues: the initial host ECB attempt failed on a missing local CA trust path; specifying the installed certifi CA bundle succeeded with TLS verification enabled. An early newly added test failed due to a missing test import, which was corrected before the full passing run. A browser navigation to port 5173 timed out during a Vite disconnect; a subsequent live browser check against the started Vite server on **5174** succeeded. Port 5173 was already occupied, so the test server selected 5174. No provider access controls were bypassed.

Remaining nonblocking warnings: Vite main bundle is approximately 645 kB minified; Starlette emits a deprecated-httpx-adapter warning for TestClient. No required executable infrastructure check remains blocked. Corporate-data acquisition remains explicitly blocked as described above.

## Readiness

**Not ready for Phase 2B correlation analysis.** The code supports returns, alignment and quality reporting; there is no real matched corporate panel to analyze. Obtain approved source exports and complete the acquisition checklist before drawing statistical conclusions.
