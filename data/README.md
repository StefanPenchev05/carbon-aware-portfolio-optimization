# CSV datasets

Company examples are only `samples/synthetic_*.csv`. Task 02 also includes an attributed real ECB FX bundle in `real/ecb_2020_2025/`, with raw snapshot and checksums. Every company and numeric observation is fabricated. Three companies, seven daily prices, three annual emissions records. These are not actual securities, index constituents, historical market prices or corporate disclosures.

Import order: companies → prices → emissions. Column definitions are the Pydantic CSV schemas in `backend/app/schemas/data.py`. Headers must contain all required fields and no unknown fields. Dates use YYYY-MM-DD, year uses an integer, currencies use three uppercase letters. Numeric optional cells may be blank; missing scopes are null. Negative emissions, nonpositive prices and nonfinite numbers are rejected. Units/methodology are required even when scope values are missing. Files are UTF-8 CSV, with quoting for text containing commas.

Provenance is supplied by mandatory CLI source/reference flags and explicit `--synthetic` or `--real`. Use source notes for dataset limitations and new source versions for revisions. The importer never infers that `--real` means independently verified. Exact duplicates are skipped, conflicting duplicates fail the transaction. Do not commit proprietary raw datasets without permission. See `docs/data-sources.md` for acquisition requirements.

Optional `memberships` imports accept `isin,index_name,as_of` (YYYY-MM-DD). Import companies first. Use only documented dated snapshots; no membership samples are invented.


Real company-data bundles require verified file hashes, source/retrieval/licence references and explicit per-scope status. See `docs/manual-data-import.md` and header-only `templates/`. The templates do not represent acquired data. `data/private/` is ignored to keep restricted material local. Original emissions values are retained; APIs expose derived tCO2e normalization only for supported unambiguous labels. Date-only disclosures are usable the following day in PIT preparation; unknown dates remain unverified.
