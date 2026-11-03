# Methodological decisions still open

No statistical or portfolio conclusions are supported by the samples.

| Decision | Current treatment / unresolved work |
|---|---|
| Corporate carbon exposure | Scopes remain separate; decide absolute, revenue-normalized, financed emissions or another measure before modeling. |
| Units and normalization | Preserve provider units; sample uses tCO2e. No conversions or cross-company normalization yet. |
| Missing observations | Null means unavailable, never zero. Decide eligibility and any defensible imputation later. |
| Annual/daily alignment | No forward filling or joining yet. Acquire publication dates and fiscal boundaries before point-in-time joins. |
| Financial returns | Store reported close and optional adjusted close. Choose simple/log returns, dividends and corporate-action treatment. |
| Index membership | Schema stores dated snapshots. No historical continuity inferred; acquire actual membership histories. |
| Currency conversion | Preserve observation currency. Choose base currency, FX source and valuation dates before comparisons. |
| Portfolio constraints | Decide leverage, gross/net exposure, sector bounds, turnover, liquidity and shorting limits. |
| Carbon penalty for shorts | Decide signed versus gross exposure treatment to prevent misleading negative carbon exposure. |
| Look-ahead bias | Source import time is not availability time. Extend with publication and vintage fields before historical evaluation. |
| Survivorship bias | Include delisted names and dated constituents before historical evaluation. |
| Revisions and source conflicts | Immutable source versions; conflicting values fail within a version. Establish an authoritative source policy. |
| Sector classification | Three exact labels in CSVs for now; establish a documented real-world taxonomy and dated mappings. |
| Precision | Floating-point observations suit initial analytics; revisit decimal storage for accounting-grade requirements. |
