# Methodological decisions still open

No statistical or portfolio conclusions are supported by the samples.

| Decision | Current treatment / unresolved work |
|---|---|
| Corporate carbon exposure | Scopes remain separate; decide absolute, revenue-normalized, financed emissions or another measure before modeling. |
| Units and normalization | Preserve provider units; sample uses tCO2e. Unambiguous CO2e mass units convert in derived fields; original values remain. Comparability still requires matching methods/boundaries. |
| Missing observations | Null means unavailable, never zero. Decide eligibility and any defensible imputation later. |
| Annual/daily alignment | Descriptive and PIT modes exist. Date-only disclosures become available next day; missing dates are excluded from PIT. Fiscal boundaries remain unresolved. |
| Financial returns | Store reported close and optional adjusted close. Simple/log returns implemented for selected consistent price basis. No implicit adjusted-close fallback; choose dividend/corporate-action policy and verify calendar. |
| Index membership | Schema stores dated snapshots. No historical continuity inferred; acquire actual membership histories. |
| Currency conversion | Preserve observation currency. ECB EUR-reference FX acquired; conversion is opt-in with exact-date quotes. Choose base currency and valuation/calendar convention. |
| Portfolio constraints | Decide leverage, gross/net exposure, sector bounds, turnover, liquidity and shorting limits. |
| Carbon penalty for shorts | Decide signed versus gross exposure treatment to prevent misleading negative carbon exposure. |
| Look-ahead bias | Source retrieval/import times differ from disclosure date. PIT excludes unknown availability; resolve vintages, release times and stale-disclosure expiry before evaluation. |
| Survivorship bias | Include delisted names and dated constituents before historical evaluation. |
| Revisions and source conflicts | Immutable source versions; conflicting values fail within a version. Establish an authoritative source policy. |
| Sector classification | Three exact labels in CSVs for now; establish a documented real-world taxonomy and dated mappings. |
| Precision | Floating-point observations suit initial analytics; revisit decimal storage for accounting-grade requirements. |


Task 02 policy: original source classifications and sector mappings must be documented. Per-scope reported/estimated status is retained and unknown remains unknown; estimates are not promoted to disclosures. Scope 2 basis and organizational boundary differences still require scientific eligibility decisions. Candidate matched observations count any reported normalized scope but do not impose historical membership or a complete multi-scope panel. Returns default to adjusted close and a provisional weekday calendar unless an exchange calendar is supplied. Price gaps/missing values break the chain; no price or FX forward fill occurs. Exact prior-day disclosure availability is conservative because intraday release times are unavailable. An emission's reporting year alone does not establish fiscal-year start/end or causal timing.
