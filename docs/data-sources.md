# Real-data source review — 3 November 2026

Only official provider pages were used for the access review. Access to a public web page is not treated as permission to harvest or redistribute a database. No accounts, licences or access requests were created or sent.

| Source | Confirmed information / decision |
|---|---|
| [STOXX Europe 600](https://stoxx.com/index/sxxp/) and [academic data](https://www.stoxx.com/academic-data) | Official index page gives an overview and top components, not an acquired dated full-universe snapshot. Academic request form lists Europe 600 quarterly components/weights for five years and requires affiliation/project details. The [factsheets page](https://www.stoxx.com/factsheets) advertises full components, but its retrieved table did not expose a Europe 600 file link. No request or entitlement supplied; no membership dataset imported. |
| [Mycelium data](https://mycelium.global/data), [methodology](https://mycelium.global/methodology), [terms](https://mycelium.global/emissions-data-terms-of-use) | Advertises downloadable reported/estimated emissions and original-report links, with registry/LEI identity. Terms allow noncommercial modest extracts with attribution but require a licence for systematic extraction. No automated records acquired. ISIN matching and original-document verification remain necessary. |
| [SRN open data](https://www.srnav.com/data/) and [binding terms](https://www.srnav.com/terms) | Landing page offers FY2024/2025 exports, report-page references, identifiers and analyst-check flags; it identifies AI-unchecked values. The reviewed terms prohibit automated collection and database creation. No export was ingested; written permission is needed for the proposed workflow. Its displayed selection also does not establish our three-sector universe. |
| [ECB reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html) and [copyright](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html) | Advertised historical XML feed retrieved successfully. ECB allows information reuse with attribution, accurate reproduction and notice of modifications. Included bundle selects five currencies and 2020–2025 dates without changing rate values. Quotes are foreign units per EUR; not transaction prices. |
| [Yahoo terms](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) | Provider terms fetch returned HTTP 999 in the research tool. Access, pilot coverage, adjustment conventions and reuse rights could not be confirmed. No Yahoo adapter/data added. |
| [Stooq](https://stooq.com/t/) | Provider responded with a JavaScript verification page. Terms and permitted download method were not established. No bypass or download attempted. |

## Acquired bundle

`data/real/ecb_2020_2025/` contains the ECB raw XML, normalized-column CSV (values unchanged), retrieval timestamp, source URL, usage conditions and SHA-256 checksums. The full raw feed is an immutable-at-retrieval source snapshot; only requested dates/currencies are imported. Raw feed coverage may extend outside the selected import period.

No real company, security-price, emissions or index-membership rows were acquired. Reported/estimated percentages for real corporate emissions are unavailable, not zero percent. Self-authored software fixtures are excluded from acquired-data claims.

## Required next acquisitions

- [ ] Obtain an authorized dated constituent snapshot with ISIN and source sector taxonomy. Choose 12–18 eligible securities across the three categories after verifying membership, not before.
- [ ] Record a source classification and justified research-category mapping for each company. Healthcare is not automatically Pharmaceuticals; issuer activities and finer classification must support the mapping.
- [ ] Obtain adjusted-price exports with ISIN, exchange, quotation units/currency, adjustment convention, trading calendar and permitted research/storage use. Confirm whether GBp/GBX prices need explicit pence-to-pound conversion; never rename them GBP without conversion evidence.
- [ ] Obtain issuer emissions report references with page/table identifiers, Scope 2 basis, per-scope reported/estimated status, annual periods and actual public disclosure dates. Check consolidated issuer boundaries against the listed security and record restatements.
- [ ] Verify whether each original report or vendor export may be retained locally and whether redistribution is permitted. Keep restricted material outside Git and use a source manifest when raw snapshot retention is not permitted.
- [ ] Have the academic supervisor approve selection, exclusions, alignment, currency and scope-comparability choices before correlation analysis.
