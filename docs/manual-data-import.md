# Manual real-data bundle workflow

Use only source material you are entitled to acquire, retain and use. Do not use these commands to bypass provider restrictions. This workflow accepts manually prepared exports and records source evidence; it does not independently validate a licence, source truth or sector mapping.

1. Obtain a dated membership snapshot and licensed price exports plus source-checked issuer disclosures. Match exact ISINs, record a single selected ticker/exchange/quotation currency per ISIN and verify the issuer/reporting perimeter. Ambiguous listings are not resolved automatically. Retain reports/exports only where permitted; otherwise include stable source references, vintage and page/table details in the manifest notes and disclosure references.
2. Place normalized CSVs in a new local directory, for example `data/private/pilot_v1/`. This directory is ignored by Git. Header-only templates in `data/templates/` describe the accepted fields; **they contain no acquired company data**. Enter original values and units. Include retrieval timestamp/timezone, source URL, permission evidence, original taxonomy and justified sector mapping. Multiple source providers should use separate bundles and source names. Company master metadata keeps its original source; later prices/disclosures can have their own sources.
3. Create the manifest from `backend/` (replace every placeholder with actual evidence). Every file argument is relative to the bundle directory:

```sh
.venv/bin/python -m app.services.provenance ../data/private/pilot_v1 \
  --source 'PROVIDER EXPORT VERSION' --reference 'ORIGINAL URL OR REFERENCE' \
  --retrieved-at 'ACTUAL_ISO_TIMESTAMP_WITH_TIMEZONE' \
  --license-reference 'TERMS URL OR LICENCE REFERENCE' \
  --permission 'EVIDENCE AND SCOPE OF PERMITTED RESEARCH USE' \
  --notes 'Snapshot effective date, permitted retention, source pages, mapping/transform decisions' \
  --files companies.csv memberships.csv prices.csv emissions.csv
```

If retention is permitted, add `--raw-files original_export.csv report.pdf` to hash local originals as well. Otherwise do not retain/repackage them; provide reproducible provider/version/document references in notes. Keep the original immutable bundle: changing its CSV or raw files fails replay validation. A revised manifest needs a new source version/name.

4. Apply migrations and import from the root:

```sh
for kind in companies memberships prices emissions; do
  docker compose exec backend python -m app.services.ingest "$kind" "/data/private/pilot_v1/${kind}.csv" --manifest /data/private/pilot_v1/manifest.json --real
done
docker compose exec backend python -m app.services.quality
```

Stop on a failed file; each file is atomic, the entire four-file loop is not one transaction. Exact duplicates skip, conflicting duplicates fail. CLI failures persist rejected batch counts when the CSV is readable and the database is reachable; malformed/unreadable files or connection failures may not produce audit rows and are still reported on stderr.

## CSV contracts

All dates are YYYY-MM-DD, optional numeric/date/reference cells may be blank, currencies are preserved three-letter quotation currencies. ISIN is required; real imports verify its checksum. Symbol-only feeds require an explicitly checked security mapping before CSV creation. Cross-dataset company/observation mixing is rejected.

- **Companies:** original taxonomy text/code in `original_sector`, taxonomy name in `classification_system`, research label in `sector`, and evidence in `sector_mapping_notes`. Real rows require all three mapping fields; software requires documentation but does not decide whether an issuer qualifies as Pharmaceuticals. Existing company metadata is immutable; conflicting company CSV rows are errors, even across source versions.
- **Memberships:** `as_of` is the actual constituent-snapshot date, not download date. This records snapshots, not continuous historical intervals.
- **Prices:** positive `close`, optional `adjusted_close`, and `adjustment_method` describing splits/dividends/provider adjustments. A populated adjusted value in real data requires known adjustment metadata. Currency must match the selected company listing; conversions must be explicit, documented and handled before importing as that listing. GBp is not silently treated as GBP. Weekends are rejected for this European pilot; exchange holidays require a verified session calendar for analysis.
- **Emissions:** each non-null scope value needs its own `reported` or `estimated` status in real imports; no provenance is inferred from magnitude. `disclosure_reference` is mandatory and should include report URL, table/page and vintage. `disclosure_date` may be blank but is then excluded from point-in-time analysis. Separate `market-based`, `location-based` and `unknown` Scope 2 bases; keep original methodologies. Real Scope 2 with unknown basis remains flagged unknown, never relabeled comparable. Units are retained verbatim; derived normalization supports explicitly listed unambiguous CO2-equivalent units only.
- **FX:** EUR-base ECB quotes are foreign currency units per EUR. No FX conversion runs automatically. The explicit helper divides foreign-currency values by an exact-date matching rate, with no forward fill.

Status defaults remain `unknown` for legacy synthetic CSVs. Source `imported_at` is ingestion time, while manifest `retrieved_at` is the actual acquisition time. Publication dates are separate. Sample data cannot be promoted to real by reimporting it with a different flag.

## Preparation interfaces

`prepare_returns(rows, price_field="adjusted_close", expected_dates=calendar)` accepts dictionaries with company_id, source_id, synthetic, date, close, adjusted_close, adjustment_method and currency. It sorts, rejects duplicates/ambiguous series, calculates simple/log returns for consecutive valid sessions and reports gaps/exclusions. Select unadjusted close explicitly when justified; there is no implicit fallback from missing adjusted prices.

`normalize_emissions(row)` preserves original values and adds `normalized_scopes` in tCO2e. Supported labels: kgCO2e/kgCO₂e (÷1000), tCO2e/tCO₂e/tonnes CO2e (unchanged), ktCO2e (×1000), MtCO2e (×1,000,000). Other strings, CO2-only figures and vague tons are unresolved. No intensity or scope sum is calculated.

`align_emissions(prices, emissions, mode="point-in-time")` requires an explicitly selected emissions source/methodology/basis stream per company/dataset. It uses the latest reporting year already disclosed, then the latest publication vintage; date-only publication is usable from the following day. Missing dates and synthetic/real mismatches cannot match. `mode="descriptive"` associates the reporting year and emits a timing warning; it is never marked temporally verified. No stale-disclosure expiry, restatement policy, fiscal-year interval mapping or historical-membership eligibility is inferred; resolve these before analysis.
