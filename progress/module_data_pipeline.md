# Module Progress: Data Pipeline

## Current State

- Implemented for the local-file-first monthly ingestion and panel-assembly workflow, with a config-driven `research_scale` raw-file selection path and the first upstream Alpha Vantage + SEC remote raw-data acquisition layer

## Files Touched

- `config/data.yaml`
- `config/remote_data.yaml`
- `config/execution.yaml`
- `config/evaluation.yaml`
- `config/paths.yaml`
- `src/utils/config.py`
- `src/data/__init__.py`
- `src/data/config.py`
- `src/data/universe.py`
- `src/data/io.py`
- `src/data/remote_config.py`
- `src/data/remote_io.py`
- `src/data/alphavantage.py`
- `src/data/sec_companyfacts.py`
- `src/data/standardize.py`
- `src/data/market_data.py`
- `src/data/benchmarks.py`
- `src/data/fundamentals_data.py`
- `src/data/qc.py`
- `src/data/panel_assembly.py`
- `src/run_data_ingestion.py`
- `src/run_fetch_remote_raw.py`
- `src/run_panel_assembly.py`
- `data/raw/README.md`
- `data/raw/market/prices_daily_sample.csv`
- `data/raw/benchmarks/benchmarks_daily_sample.csv`
- `data/raw/fundamentals/fundamentals_quarterly_sample.csv`
- `tests/data/test_data_pipeline.py`
- `tests/data/test_remote_fetch.py`
- `tests/test_repo_skeleton.py`
- `README.md`
- `docs/02_system_architecture.md`
- `docs/03_data_schema.md`
- `docs/10_development_roadmap.md`
- `progress/current_status.md`

## Completed Work

- Added a dedicated data-stage config loader with raw-data path settings, benchmark defaults, month-end normalization rules, and fundamentals lag controls.
- Implemented local raw file discovery and persistence helpers for Parquet, JSON, and CSV artifacts.
- Implemented execution-mode-aware raw file selection:
  - default `seeded` mode reads only sample-tagged raw files
  - `research_scale` mode prefers broader non-sample local raw files and falls back to sample-tagged raw files when broader history is absent
- Implemented market-price ingestion that accepts daily or monthly raw files, standardizes to one row per ticker per month, and computes `monthly_return` from `adjusted_close`.
- Implemented benchmark ingestion for `SPY` and `QQQ` plus derived `equal_weight_universe` monthly benchmark construction.
- Implemented fundamentals standardization and monthly mapping using a documented `2`-month effective lag and a `12`-month max staleness cap.
- Implemented deterministic monthly panel assembly on the full universe-by-month grid with aligned primary benchmark returns.
- Implemented dataset QC JSON outputs and per-ticker/per-date coverage CSV outputs.
- Added raw-file selection manifests to the dataset QC JSON outputs so longer-history runs are auditable.
- Enriched the raw-file selection manifests with per-file filesystem metadata plus observed raw row/date coverage so future broader-history runs can prove exactly which local files were used.
- Seeded deterministic local sample raw inputs so the implemented runners can be executed end to end inside the repo.
- Updated the project docs to define the next acquisition milestone:
- Implemented the first upstream remote-acquisition layer with:
  - `config/remote_data.yaml` for provider credentials, endpoints, overwrite policy, and output naming
  - Alpha Vantage market and benchmark fetchers that write latest non-sample raw files plus immutable snapshots and manifests
  - Alpha Vantage overview metadata fetches written under `data/raw/fundamentals/metadata`
  - SEC Company Facts raw JSON capture plus a conservative mapped quarterly fundamentals subset written to `data/raw/fundamentals/fundamentals_quarterly_sec_companyfacts.parquet`
  - machine-readable provider manifests capturing request scope, timestamps, output files, and partial-failure/throttle conditions
  - runnable `src.run_fetch_remote_raw`

## Testing Status

- `tests/data/test_data_pipeline.py` now covers:
  - monthly resampling logic
  - monthly return calculation
  - duplicate key detection
  - benchmark alignment
  - one-row-per-ticker-per-month validation
  - fundamentals lagged monthly merge behavior
  - equal-weight benchmark construction
  - research-scale raw-file selection preference and fallback behavior
  - raw-file manifest enrichment with per-file provenance and observed raw coverage
- `tests/data/test_remote_fetch.py` now covers:
  - remote fetch config loading
  - output naming and manifest path construction
  - dataset manifest JSON writing
  - Alpha Vantage monthly adjusted response parsing
  - Alpha Vantage overview response parsing
  - SEC ticker-to-CIK parsing
  - SEC user-agent resolution
  - SEC Company Facts conservative mapping logic
- `tests/test_repo_skeleton.py` was updated so the data-stage CLIs are tested as implemented runners rather than scaffold-only stubs.
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `70 passed` on 2026-03-30.

## Manual Verification Status

- `.\.venv\Scripts\python.exe -m src.run_data_ingestion` completed successfully on 2026-03-28.
- `.\.venv\Scripts\python.exe -m src.run_panel_assembly` completed successfully on 2026-03-28.
- `.\.venv\Scripts\python.exe -m src.run_fetch_remote_raw --help` completed successfully on 2026-03-30.
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion` completed successfully on 2026-03-30 after the remote-fetch implementation.
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion --execution-mode research_scale` completed successfully on 2026-03-30.
- `.\.venv\Scripts\python.exe -m src.run_panel_assembly --execution-mode research_scale` completed successfully on 2026-03-30.
- Output row counts and QC summaries were manually reviewed for consistency with the seeded universe and sample date range.
- Research-scale verification confirmed that broader local raw files were absent and that the new sample-fallback manifest fields were populated correctly.
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion --execution-mode research_scale` was rerun successfully on 2026-03-30 after the provenance upgrade.
- The refreshed dataset QC summaries now show the observed seeded fallback coverage:
  - `prices_daily_sample.csv`: `2580` raw rows, raw date span `2024-01-02` to `2024-06-28`
  - `benchmarks_daily_sample.csv`: `258` raw rows, raw date span `2024-01-02` to `2024-06-28`
  - `fundamentals_quarterly_sample.csv`: `60` raw rows, raw date span `2023-09-30` to `2024-03-31`
- Live provider fetches were not manually executed on 2026-03-30 because this workspace verification pass did not include Alpha Vantage credentials or SEC identity values.

## Known Issues / Risks

- Fundamentals are still subject to revised-history bias because the current source is not point-in-time safe.
- The downstream raw-data adapter layer is still local-file-first only by design; remote providers are upstream helpers, not downstream dependencies.
- The new SEC Company Facts mapping is intentionally conservative and leaves some canonical valuation fields unmapped.
- The `research_scale` path is ready, but genuinely longer-history execution remains blocked until broader non-sample local raw files are actually fetched or added.
- The equal-weight universe benchmark is intentionally simple and does not yet include execution realism.

## Immediate Next Step

- Run the first credentialed `src.run_fetch_remote_raw --provider alphavantage_sec --execution-mode research_scale` refresh, inspect the fetch manifests, and then rerun the downstream `research_scale` path on the fetched broader local raw coverage.
