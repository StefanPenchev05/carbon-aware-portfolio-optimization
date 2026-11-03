# Architecture

A small monorepo separates a React/Vite client from a synchronous FastAPI service and PostgreSQL. The source declaration PDF is preserved unchanged. Routes validate HTTP inputs and use repositories for database access; import services validate tabular data independently of HTTP. No microservices, authentication or optimization abstractions are introduced.

Company identity uses unique ISIN, while ticker and exchange remain descriptive. Price uniqueness is company/date/source. Emissions uniqueness includes year/source/methodology/units to keep incompatible disclosures distinguishable. Scopes are nullable independently, and absent company-year records remain absent. Database foreign keys, nonnegative emissions constraints, positive price constraints and company/date query indexes complement Pydantic input validation.

Sources hold immutable name, reference, import timestamp, synthetic flag and notes. An observation's date/year supplies its original reporting period; prices preserve currency; emissions preserve units and methodology. Timestamp represents initial import of that source version, not verified provider retrieval time. Use a new source name for each version/retrieval batch. Index memberships are dated snapshots, not claims of continuous membership. No synthetic sample claims STOXX membership.

Pandas reads CSV cells as strings to preserve identifiers. Pydantic parses strict ISO dates and finite numeric observations. Each CLI invocation opens one transaction: exact duplicates skip, conflicting duplicates fail, and no incomplete batch commits. The CSV adapter can be complemented by provider-specific adapters that produce the same validated records. Imports are intended to run serially; concurrent collisions are still protected by database uniqueness but may require retry.

React fetches actual APIs, cancels stale requests and displays loading, error and missing-data states. Price series split by source/currency; emissions split by source/units/methodology, with separate scope bars. No scope totals, currency conversion or disclosure imputation is performed. Tables supplement charts. Synthetic status remains visible at company and observation level.

Alembic owns schema changes. Docker runs PostgreSQL and the API; Vite runs on the host for quick editing. Tests isolate business behavior with SQLite and validate the actual PostgreSQL lifecycle separately. Coverage queries favor readability for the small initial universe; aggregate SQL, pagination and large-file chunking can be introduced when measured scale warrants them.

Official implementation references: [FastAPI database guide](https://fastapi.tiangolo.com/tutorial/sql-databases/) and [Vite guide](https://vite.dev/guide/).
