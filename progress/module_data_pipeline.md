# Module Progress: Data Pipeline

## Current State

- Implemented for the local-file-first monthly ingestion and panel-assembly workflow

## Files Touched

- `config/data.yaml`
- `config/paths.yaml`
- `src/utils/config.py`
- `src/data/__init__.py`
- `src/data/config.py`
- `src/data/universe.py`
- `src/data/io.py`
- `src/data/standardize.py`
- `src/data/market_data.py`
- `src/data/benchmarks.py`
- `src/data/fundamentals_data.py`
- `src/data/qc.py`
- `src/data/panel_assembly.py`
- `src/run_data_ingestion.py`
- `src/run_panel_assembly.py`
- `data/raw/README.md`
- `data/raw/market/prices_daily_sample.csv`
- `data/raw/benchmarks/benchmarks_daily_sample.csv`
- `data/raw/fundamentals/fundamentals_quarterly_sample.csv`
- `tests/data/test_data_pipeline.py`
- `tests/test_repo_skeleton.py`
- `README.md`
- `docs/02_system_architecture.md`
- `docs/03_data_schema.md`
- `docs/10_development_roadmap.md`
- `progress/current_status.md`

## Completed Work

- Added a dedicated data-stage config loader with raw-data path settings, benchmark defaults, month-end normalization rules, and fundamentals lag controls.
- Implemented local raw file discovery and persistence helpers for Parquet, JSON, and CSV artifacts.
- Implemented market-price ingestion that accepts daily or monthly raw files, standardizes to one row per ticker per month, and computes `monthly_return` from `adjusted_close`.
- Implemented benchmark ingestion for `SPY` and `QQQ` plus derived `equal_weight_universe` monthly benchmark construction.
- Implemented fundamentals standardization and monthly mapping using a documented `2`-month effective lag and a `12`-month max staleness cap.
- Implemented deterministic monthly panel assembly on the full universe-by-month grid with aligned primary benchmark returns.
- Implemented dataset QC JSON outputs and per-ticker/per-date coverage CSV outputs.
- Seeded deterministic local sample raw inputs so the implemented runners can be executed end to end inside the repo.

## Testing Status

- `tests/data/test_data_pipeline.py` now covers:
  - monthly resampling logic
  - monthly return calculation
  - duplicate key detection
  - benchmark alignment
  - one-row-per-ticker-per-month validation
  - fundamentals lagged monthly merge behavior
  - equal-weight benchmark construction
- `tests/test_repo_skeleton.py` was updated so the data-stage CLIs are tested as implemented runners rather than scaffold-only stubs.
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `14 passed` on 2026-03-28.

## Manual Verification Status

- `.\.venv\Scripts\python.exe -m src.run_data_ingestion` completed successfully on 2026-03-28.
- `.\.venv\Scripts\python.exe -m src.run_panel_assembly` completed successfully on 2026-03-28.
- Output row counts and QC summaries were manually reviewed for consistency with the seeded universe and sample date range.

## Known Issues / Risks

- Fundamentals are still subject to revised-history bias because the current source is not point-in-time safe.
- The raw-data adapter layer is still local-file-first only.
- The equal-weight universe benchmark is intentionally simple and does not yet include execution realism.

## Immediate Next Step

- Build `src.features` on top of `outputs/data/monthly_panel.parquet` with explicit lookbacks, lags, and feature QC outputs.
