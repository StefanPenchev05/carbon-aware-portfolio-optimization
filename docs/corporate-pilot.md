# Corporate pilot — Task 03

Acquisition and verification: **3 November 2026**. The first genuine end-to-end corporate import is **Siemens AG**. The other two named companies were investigated, not silently added to the imported sample. No new ingestion framework, model, API or migration was needed.

## Result and scope

| Item | Acquired/imported |
|---|---:|
| Verified/imported real companies | 1: Siemens AG (Industrials) |
| Dated STOXX membership rows imported | 1, as of 30 September 2026 |
| Real price observations | 7 sparse unadjusted Xetra closes, 2022–2025 |
| Adjusted prices / complete daily series | 0 / none |
| Annual carbon records | 2: FY2023 and FY2024 |
| Populated scope cells | 4: Scope 1 and market-based Scope 2 for both years |
| Scope 3 | Not acquired for this minimal pilot |
| Missing publication dates | 0 |
| Rejected import rows / unsupported units | 0 / 0 |
| Descriptive year-label price/emissions matches | 3; 4 price observations unmatched |
| Prior-publication price-level matches | 2; 5 price observations unmatched |
| Usable daily returns / matched return-emissions pairs | **0 / 0** |

The descriptive counts are reporting-year-label matches produced by the existing alignment helper, not a calendar-year assumption about Siemens' October–September fiscal years. Two later price levels have a known prior disclosure, but neither count establishes valid return observations or statistical adequacy. No correlation was calculated. The three synthetic companies and 7,690 ECB FX quotes remain intact and distinct.

## Official dated membership evidence

The [official SXXP factsheet view](https://stoxx.com/index/SXXP/?factsheet=true) lists SHELL, SIEMENS and NOVARTIS in its **Top 10 Components** table. Footnote 4 states composition as of **30 September 2026**. This verifies a single dated snapshot for all three candidates; only Siemens' membership row was imported. It does not establish membership throughout 2022–2025 and cannot support a survivorship-free historical universe.

The [older CurrentComponents PDF](https://www.stoxx.com/document/Bookmarks/CurrentComponents/SXXP.pdf) also lists all three but has no explicit composition date. Its PDF metadata says July 2023; document creation time is not a constituent effective date. It was inspected and **rejected as dated membership evidence**. It was not used to assign a historical as-of date.

The factsheet uses company names rather than an ISIN export. Matching therefore combines its distinct company/country entries with official issuer security identities below; no ticker-only financial matching was used. The SIEMENS line is distinct from Siemens Energy and Siemens Healthineers.

## Identity and share-class review

| Company | Selected ordinary-share identity | Exchange, ticker, quotation | Source classification and research mapping |
|---|---|---|---|
| Shell plc | GB00BP6MXD84; ordinary share, not US7802593050 ADS | London Stock Exchange / XLON, SHEL; underlying GBP, London prices normally GBX/GBp (pence) | STOXX Energy → Energy; integrated energy/oil and gas operations in issuer report |
| Siemens AG | DE0007236101; registered no-par ordinary shares, not US8261975010 ADR | Xetra / XETR, SIE; EUR per share | STOXX Industrial Goods and Services → Industrials; not the separately listed Siemens Energy or Healthineers securities |
| Novartis AG | CH0012005267; registered ordinary share, not US66987V1098 ADR | SIX Swiss Exchange / XSWX, NOVN; CHF per share | STOXX Healthcare; Pharmaceuticals mapping supported by Novartis' innovative-medicines business, not by Healthcare alone |

Primary identity links:

- Shell [investor relations](https://www.shell.com/investors.html), [share information](https://www.shell.com/investors/information-for-shareholders/share-information.html), [simplification and identifier notice](https://shell.gcs-web.com/news-releases/news-release-details/shell-sets-out-expected-timetable-simplification), and [LSE instrument page](https://www.londonstockexchange.com/en/quote/equity/SHEL/shell-plc). The issuer confirms GBP on LSE, EUR on Euronext, and USD for the NYSE ADS. The LSE page distinguishes GBX price quotations from GBP trade value; confirm the exported price unit rather than relying on a currency label. The unified ordinary line starts **31 January 2022**; do not assign earlier RDSA/RDSB prices to its ISIN or use the ADS (two ordinary shares) without explicit corporate-action treatment.
- Siemens [investor relations](https://www.siemens.com/en-us/company/investor-relations/), [basic data and key share figures](https://www.siemens.com/en-us/company/investor-relations/share-bonds-rating/basic-data-key-share-figures/), and [official exchange reference-data example](https://www.cashmarket.deutsche-boerse.com/resource/blob/1448460/692913ae4a0fee5db2280f734b7c7b22/data/T7_Release_7.0_Xetra_Instrument_Reference_Data_Guide.v.1.0.pdf). The issuer identifies SIE, ISIN, Xetra and EUR explicitly.
- Novartis [investor relations](https://www.novartis.com/investors), [ordinary-share/ADR overview](https://www.novartis.com/investors/share-data-and-analysis/share-overview), and [2024 Form 20-F](https://www.sec.gov/Archives/edgar/data/1114448/000137036825000004/nvs-20241231.htm). The issuer identifies NOVN SW, CHF and primary SIX listing. Preserve the Sandoz spin-off/corporate-action treatment when acquiring price history.

No Shell or Novartis company, price or emissions rows were imported. The names above are investigated candidates, not claims of dataset coverage.

## Real financial acquisition

The Siemens Basic Data page has a **Key share figures** table containing Xetra closing prices on dated AGM days and fiscal year-end closes. Seven source cells have usable weekday dates in 2022–2025: four AGM-day closes (one per year) and three fiscal year-end closes (2022, 2024, 2025). They were manually transcribed and checked against the original table; no values came from search snippets or a third-party quote service. Original EUR units and unadjusted status are preserved; adjusted_close remains null. There is no FX conversion, interpolation or forward fill.

The FY2023 year-end cell is labelled 30 September, which was a Saturday. It was **excluded** because the source does not establish the actual last-trading-session date in that label. We did not silently substitute 29 September. The private evidence record lists every included cell, date, column, value and validation decision.

This is a sparse set of genuine daily closing observations, **not a daily history**. It can demonstrate storage, querying and visualization but produces no daily returns. [Shell's share-price page](https://www.shell.com/investors/information-for-shareholders/share-prices.html) advertises charts/historical information but no validated permitted full-series export was acquired here. Bloomberg education pages were inaccessible (403); neither advertising nor terminal availability was treated as export permission. No authorized financial API credentials or vendor CSVs were supplied.

## Emissions: original report verification

Imported source: [Siemens Sustainability Report 2024](https://assets.new.siemens.com/siemens/assets/api/uuid:32a7154d-edba-47bc-8e9b-9761617ba774/sustainability-report.pdf), printed/PDF **page 67**, “Greenhouse gas emissions” table, FY2024 and FY2023 columns, Scope 1 and Scope 2 rows, footnotes 1–2. The page was rendered and visually checked; reporting methodology on pages **136–137** was read in full.

- Reporting entity: Siemens consolidated ongoing operations, including Siemens Healthineers and Innomotics unless explicitly excluded; minority interests generally excluded. This is group-wide, not a site or subsidiary disclosure. Do not substitute the separate DEGREE figures excluding Healthineers.
- Consolidation: financial-control approach. FY2024 runs 1 October 2023–30 September 2024; the FY2023 comparative is the issuer's prior fiscal-year column. Notes record the October–September fiscal convention; alignment remains labelled rather than claiming a calendar-year interval join.
- Original unit: **1,000 metric tons of CO2-equivalents**, stored as equivalent canonical `ktCO2e` with original numerical values. Original wording and units remain in the evidence and CSV notes. API normalized values in `tCO2e` are derived separately (×1,000); originals are not overwritten.
- Scope 2: market-based (table footnote 2). No location-based values are inferred. Scope 3 is omitted from the minimal acquisition, not zero.
- Status `reported`: these are issuer-disclosed aggregates, not externally modelled provider estimates. **This does not mean 100% measured**: page 137 permits estimation for unavailable primary data and extrapolation for smaller sites. The method/notes and per-cell evidence preserve this limitation. The quality percentage describes disclosure provenance, not measurement assurance.
- Availability: the dated [issuer release of 5 December 2024](https://press.siemens.com/global/en/pressrelease/siemens-achieves-strong-progress-sustainability-targets) explicitly describes the newly published 2024 report. Both FY2024 and the FY2023 comparative therefore use **2024-12-05** for this report vintage, not a guessed earlier availability for 2023. Date-only disclosures become usable the following day. Historical byte-level equivalence to the release-day PDF was not independently archived; current source hashes identify the version actually inspected.

Candidate sources investigated, not imported:

- Shell: [official 2024 Annual Report](https://www.shell.com/who-we-are/our-values/_jcr_content/root/main/section_874829968/list/list_item_copy.multi.stream/1752580693041/6c20b8111738b9a590ba145f0d1c4fa0e530dae0/shell-annual-report-2024.pdf), printed p107/PDF p109, “GHG emissions in million tonnes of CO2 equivalent” table, global operational-control rows, 2022–2024, separate market/location Scope 2. This must not be confused with the UK-only subrows, net totals/credits or a local Shell subsidiary. [Publication announcement](https://www.shell.com/news-and-insights/newsroom/news-and-media-releases/2025/shell-plc-publishes-2024-annual-report-and-accounts.html): 25 March 2025. The [2025 report](https://www.shell.com/sustainability/reporting-centre/_jcr_content/root/main/section_597740108/promo.multi.stream/1773292272508/5e49e127579b77081f032b6088b348694aac0d14/shell-annual-report-2025.pdf) is also available; no 2025 value was imported. Scope 3 categories/estimates must not be mistaken for a comparable measured total.
- Novartis: [official Integrated Report 2024](https://www.novartis.com/sites/novartiscom/files/novartis-integrated-report-2024.pdf), pp3,28,61, group environmental indicators for 2022–2024 with separate Scope 2 bases; pp3/61 state that 2024 includes estimated October–December data, whereas 2022/2023 are full-year actual performance data in this vintage. Scope 3 includes estimates/modelled activity; it must retain that distinction. Publication is established by the [31 January 2025 results release](https://www.novartis.com/news/media-releases/novartis-continues-strong-momentum-sales-growth-margin-expansion-reaches-key-innovation-milestones-2024) and [Form 6-K](https://www.sec.gov/Archives/edgar/data/1114448/000137036825000008/a250131nisar-6k.htm). Sandoz/continuing-operations and Abadia Retuerta boundary/restatement notes need to travel with any future extraction. No 2025 data acquired.
- Siemens [sustainability reporting centre](https://www.siemens.com/en-gb/company/sustainability/reports-figures/) also links a 2025 statement; it was identified but not transcribed into this first pilot. Missing 2022/2025 emissions are not filled.

## Retention, access and usage

All source PDFs/HTML, extracted CSVs and per-cell financial values remain in **ignored `data/private/`**, not in the public repository. The public [source index](../data/acquisition/corporate-pilot-sources.json) contains references/checksums and coverage, not a redistributable price dataset.

- [Siemens terms](https://www.siemens.com/global/en/general/terms-of-use.html) were read through the ordinary redirected page after web-tool timeouts. Sections 4.3–4.5 permit intended own-purpose use and restrict onward distribution. This pilot interprets local internal study of investor information as intended use; it does **not** claim an open-data, public-hosting or third-party redistribution licence. Obtain explicit permission before sharing the private bundle or publishing its contents.
- [Shell terms](https://www.shell.com/terms-of-use.html) are restrictive about copying and distribution; the report announcement separately advertises PDF downloads. No general research-database/republication permission is asserted, and no Shell data was ingested. An alternative original filing exists on [SEC EDGAR](https://www.sec.gov/Archives/edgar/data/1306965/000130696525000007/shel-20241231.htm); availability there alone is not a blanket copyright licence.
- [Novartis terms](https://www.novartis.com/terms-use), section3, allow own noncommercial access/use but do not establish unrestricted redistribution. No Novartis dataset was ingested or publicly republished.
- STOXX source references are a modest validation of three named constituents, not a harvested/repackaged constituent database. No historical constituent export was acquired. Its source copyright/usage rights remain in force.
- The user confirmed **Bloomberg export permission is not yet confirmed**. No login, terminal session, credential, authenticated API, subscription purchase or message to university/provider staff was used.

## Reproduce and validate the acquired local bundle

The acquired files are at `data/private/siemens_pilot_v1/`: `companies.csv`, `memberships.csv`, `prices.csv`, `emissions.csv`, `manifest.json`, `extraction-validation.json`, source snapshots and `quality-report.json`. The validation record identifies every numerical cell and source location; the immutable manifest hashes all imported CSVs and originals. Source terms/copyright notices are retained in the originals. The quality report is regenerable output, not hashed provider data.

From this workspace root:

```sh
docker compose up -d
for kind in companies memberships prices emissions; do
  docker compose exec -T backend python -m app.services.ingest "$kind" "/data/private/siemens_pilot_v1/${kind}.csv" --manifest /data/private/siemens_pilot_v1/manifest.json --real || break
done
backend/.venv/bin/python scripts/validate_corporate_pilot.py data/private/siemens_pilot_v1
python3 scripts/smoke.py
python3 scripts/smoke_research.py
```

Reimports must skip 1 company, 1 membership, 7 prices and 2 emissions; they must not overwrite or insert duplicates. The corporate verifier compares the API against the hashed local CSVs, checks original/normalized values, flags, dates and source references, then runs the existing returns/alignment helpers and reports counts. The two older smoke scripts now scope synthetic assertions to synthetic companies, allowing genuine corporate rows alongside them without weakening demo checks.

On another machine the private bundle is deliberately absent from Git. Under permitted local use, retrieve the exact primary references above, compare source SHA-256 with the public index, transcribe the specified cells and reproduce the evidence record and CSV schemas using the existing manual workflow. Do not assume a changing provider URL yields identical bytes. The current user's local bundle is complete for exact replay without new network access; no public right to redistribute it is implied.

## Human acquisition checklist: full daily prices

1. Ask the University of Luxembourg FinanceLab/LLC licence administrator to confirm in writing: permitted research/project use; export entitlement/limits; local PostgreSQL storage; permitted machines/users; retention period; whether thesis/public charts/derived results or external-hosted apps are allowed; raw-data redistribution restrictions. The user has not yet received this confirmation. [University source](https://www.uni.lu/wp-content/uploads/sites/8/2023/06/DSEFM_Course_Programme_2022-23_RG.pdf) documents institutional Bloomberg access, but is an older programme document, not a current export licence. No contact was made on the user's behalf.
2. If approved, use the authorized physical terminal/Excel add-in. Resolve each security in DES/security search by **ISIN**, and save the selected share class, exchange, source/pricing venue, Bloomberg identifier and quote currency/unit. Candidates: SHEL LN ordinary, Siemens SIE (issuer lists SIE GR; confirm the actual Xetra line/source rather than assuming a composite equals Xetra), NOVN SW ordinary. Reject the ADS/ADR alternatives.
3. Use the Historical End-of-Day wizard for **2022-01-01–2025-12-31**, daily frequency, trading days only, no missing-value fill, native local currency and explicitly selected price source/venue. For unified Shell start **2022-01-31** unless an independently documented predecessor-chain method is approved. Do not splice RDSA/RDSB into the new ISIN silently.
4. Retrieve `PX_LAST` (verify the field definition in terminal help/FLDS) twice if necessary: an unadjusted close export, and a provider-supported adjusted close export with split/capital-change and normal/abnormal cash-dividend switches explicitly recorded. Use the wizard's current options/help, save those exact settings, and never rely on an account default. An adjusted close is not automatically a total-return index. If adjustment semantics cannot be confirmed, leave adjusted_close blank. A university-operated [Excel function-builder guide](https://vodici.cek.ef.uni-lj.si/bbg-eng/Bloomberg-excel-add-in/function-builder) documents BDH historical retrieval; actual terminal entitlement/settings still require confirmation.
5. Export source columns **security identifier, ISIN, exchange/price source, trading date, raw close, adjusted close if supplied, quote currency, quote unit, adjustment flags/method, extraction timestamp**. Keep original exports and settings locally under the licence. Document field names, corporate actions, any provider restatements and calendar.
6. Convert to the existing `prices.csv` contract only after checks. If London export is GBX/GBp, preserve the original and explicitly divide both price columns by 100 to GBP in a separately documented transformation; never apply ECB GBP quotes to pence. EUR and CHF stay native until an explicitly justified, exact-date FX conversion. Validate Novartis' spin-off and Siemens' corporate-action history/adjustments rather than inferring them.
7. Check finite positive prices, duplicate dates/ISINs, trading sessions, no calendar padding, currency consistency, selected share class and first/last rows. Keep the original export immutable. Use a **new source bundle/version** and manifest (the existing company master remains its original source), import through the existing CLI and rerun quality reporting.
8. Acquire historical constituent snapshots and first-publication emissions vintages if the research requires point-in-time membership rather than this fixed later snapshot. Source dates, fiscal periods, consolidated boundaries and Scope 2 bases must all be justified before comparing firms.

## Verification and readiness

Executed regression results are recorded after the final run below. No correlations, optimizers, backtests or new dashboard were introduced.

**Technical readiness:** the first real corporate observations flow through manifest validation, PostgreSQL, API, normalized units and the existing Explorer.

**Statistical adequacy:** not enough for even a defensible small descriptive return/emissions correlation. Only two annual emissions records and seven sparse unadjusted prices exist, with zero daily return pairs. Repeating annual emissions against a handful of price levels would not fix the frequency, timing, trend or sample-size problems. Obtain a permitted consistent daily price series and additional comparable annual disclosures before a correlation experiment.

### Executed checks

- Backend: **53 Pytest tests passed**, including original-unit normalization and sparse/unadjusted return exclusion cases.
- Frontend: **5 Vitest tests passed**; strict TypeScript/production build and Prettier checks passed.
- Ruff lint and format checks passed for backend and verification scripts; Git whitespace check passed.
- Initial PostgreSQL imports inserted **1 / 1 / 7 / 2** company/membership/price/emissions records. Repeated imports inserted **zero**, skipping **1 / 1 / 7 / 2**.
- Corporate live API verifier passed against all hashed local CSVs, source references, original/normalized scope values, disclosure dates and counts. Both existing HTTP smoke scripts passed with corporate and synthetic data coexisting.
- Live Chromium at localhost:5174 displayed Siemens AG, the real-data flag, original classification, sparse unadjusted-price metadata, both price and emissions charts, original ktCO2e scope values and 2024-12-05 publication dates. Synthetic company entries remain separately named/labeled. Industrial filtering and synthetic selection were checked in the final browser pass.
- `git check-ignore` confirms all raw/derived source datasets are private/ignored. No raw financial data, report PDFs, credentials or exports were staged/committed.

Nonblocking pre-existing warnings: approximately 645 kB Vite main bundle and the Starlette/httpx TestClient deprecation. No migrations were necessary. The first generation command encountered the host default Python 3.10 (which lacks datetime.UTC); rerunning with the project's Python 3.12 environment succeeded before import. No acquisition values were changed to address a validation failure. Full daily-price acquisition remains blocked by missing confirmed institutional export permission, not by an application error.
