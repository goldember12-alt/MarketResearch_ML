# Raw Data

This directory contains deterministic local sample inputs for the ingestion pipeline and now also serves as the landing zone for remote raw-data fetch outputs.

- `market/`: daily security prices for the seeded research universe
- `benchmarks/`: daily benchmark prices for `SPY` and `QQQ`
- `fundamentals/`: quarterly fundamentals used for monthly mapping with a conservative lag rule

Implemented remote-acquisition rules:

- remote acquisition will continue to write into these same directories rather than bypassing them
- Alpha Vantage is the implemented upstream source for security and benchmark price history
- SEC EDGAR / Company Facts is the implemented upstream source for filing-based fundamentals
- non-sample file names should be used for research-scale runs so they are preferred over `_sample` verification files
- the CLI writes latest non-sample files for ingestion plus immutable snapshot copies and JSON manifests for provenance
- downstream ingestion still reads only local raw `.csv` and `.parquet` files from the documented stage roots

Implemented remote raw-data paths:

- `market/prices_monthly_alphavantage.csv`
- `market/snapshots/`
- `market/manifests/prices_monthly_alphavantage_manifest.json`
- `benchmarks/benchmarks_monthly_alphavantage.csv`
- `benchmarks/snapshots/`
- `benchmarks/manifests/benchmarks_monthly_alphavantage_manifest.json`
- `fundamentals/fundamentals_quarterly_sec_companyfacts.parquet`
- `fundamentals/snapshots/`
- `fundamentals/manifests/fundamentals_quarterly_sec_companyfacts_manifest.json`
- `fundamentals/metadata/security_metadata_alphavantage_overview.csv`
- `fundamentals/metadata/snapshots/`
- `fundamentals/sec_companyfacts/raw/`
- `manifests/remote_fetch_alphavantage_sec_<timestamp>.json`
