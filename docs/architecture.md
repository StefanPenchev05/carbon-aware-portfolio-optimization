# Architecture

A small monorepo separates a React/Vite client from a synchronous FastAPI service and PostgreSQL. The source declaration PDF is preserved unchanged. Routes validate HTTP inputs and use repositories for database access; import services validate tabular data independently of HTTP. No microservices, authentication or optimization abstractions are introduced.

Company identity uses unique ISIN, while ticker and exchange remain descriptive. Price uniqueness is company/date/source. Emissions uniqueness includes year/source/methodology/units to keep incompatible disclosures distinguishable. Scopes are nullable independently, and absent company-year records remain absent. Database foreign keys, nonnegative emissions constraints, positive price constraints and company/date query indexes complement Pydantic input validation.

Sources hold immutable name, reference, import timestamp, synthetic flag and notes. An observation's date/year supplies its original reporting period; prices preserve currency; emissions preserve units and methodology. Timestamp represents initial import of that source version, not verified provider retrieval time. Use a new source name for each version/retrieval batch. Index memberships are dated snapshots, not claims of continuous membership. No synthetic sample claims STOXX membership.

Pandas reads CSV cells as strings to preserve identifiers. Pydantic parses strict ISO dates and finite numeric observations. Each CLI invocation opens one transaction: exact duplicates skip, conflicting duplicates fail, and no incomplete batch commits. The CSV adapter can be complemented by provider-specific adapters that produce the same validated records. Imports are intended to run serially; concurrent collisions are still protected by database uniqueness but may require retry.

React fetches actual APIs, cancels stale requests and displays loading, error and missing-data states. Price series split by source/currency; emissions split by source/units/methodology/Scope 2 basis, with separate scope bars. No scope totals, automatic currency conversion or disclosure imputation is performed. Tables supplement charts. Synthetic status remains visible at company and observation level.

Alembic owns schema changes. Docker runs PostgreSQL and the API; Vite runs on the host for quick editing. Tests isolate business behavior with SQLite and validate the actual PostgreSQL lifecycle separately. Coverage queries favor readability for the small initial universe; aggregate SQL, pagination and large-file chunking can be introduced when measured scale warrants them.

Official implementation references: [FastAPI database guide](https://fastapi.tiangolo.com/tutorial/sql-databases/) and [Vite guide](https://vite.dev/guide/).


## Task 02 extensions

An additive migration preserves legacy records with unknown status/basis/adjustment and nullable disclosure/source-retrieval fields. Per-scope reported/estimated status, original disclosure references, source sector classification/mapping and publication dates are exposed through the existing response contracts. Emissions uniqueness now includes Scope 2 basis. Downgrading cannot collapse conflicting market/location records; resolve such rows explicitly before attempting downgrade. No records are silently merged.

Real CLI imports require a hashed manifest with retrieval timestamp, permission evidence and source reference. CSV and permitted raw snapshots are verified before ingestion. A source version's manifest digest is immutable. ISIN checksum checks complement exact matching; the company master chooses one listing and rejects a currency mismatch. No symbol-guessing adapter exists. Company/observation real-synthetic mismatch is rejected.

`ecb.py` is the only live adapter: it uses the provider's advertised historical XML download and writes an immutable bundle before database import. Corporate providers with unresolved access/terms use documented manual CSV preparation. `provenance.py` builds/checks bundles; `preparation.py` contains pure normalization, returns, exact-date opt-in FX conversion and descriptive/PIT alignment functions. Original emissions units/values remain stored; normalized fields are derived and returned separately.

CLI success audit rows commit with data; validation failures record rolled-back batch counts in a separate transaction where possible. Legacy imports and unreachable databases may lack audit records. `/api/data/coverage` retains its array shape and original fields with an added `quality` object. `/api/data/quality?synthetic=false` provides the aggregate research report; `synthetic=true` produces a separate demo report. Its candidate match count is not proof of statistical eligibility, verified calendars or historical membership. Services remain synchronous and sized for a small pilot; no correlation or portfolio code was added.
