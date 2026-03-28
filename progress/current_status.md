# Current Status

## Current Milestone

- Data-ingestion and canonical monthly-panel foundation implemented for the local-file-first workflow

## What Is Completed

- `src.data` now includes config-driven modules for raw file ingestion, standardization, benchmark construction, QC, and deterministic monthly panel assembly.
- `config/data.yaml` was added to define raw-data locations, column priorities, month-end convention, the primary benchmark, and fundamentals lag settings.
- `config/paths.yaml` and `src/utils/config.py` were extended to include data-stage QC and coverage artifacts.
- `src/run_data_ingestion.py` now ingests local raw market, benchmark, and fundamentals files and writes:
  - `outputs/data/prices_monthly.parquet`
  - `outputs/data/fundamentals_monthly.parquet`
  - `outputs/data/benchmarks_monthly.parquet`
  - `outputs/data/prices_qc_summary.json`
  - `outputs/data/fundamentals_qc_summary.json`
  - `outputs/data/benchmarks_qc_summary.json`
- `src/run_panel_assembly.py` now reads the processed data artifacts, constructs the full ticker-month grid, aligns the configured primary benchmark, validates one row per ticker per month, and writes:
  - `outputs/data/monthly_panel.parquet`
  - `outputs/data/panel_qc_summary.json`
  - `outputs/data/ticker_coverage_summary.csv`
  - `outputs/data/date_coverage_summary.csv`
- Deterministic local sample raw inputs were added under:
  - `data/raw/market/`
  - `data/raw/benchmarks/`
  - `data/raw/fundamentals/`
- The data docs and handoff files were updated to document:
  - month-end normalization
  - `monthly_return` and `benchmark_return` formulas
  - equal-weight benchmark construction
  - fundamentals effective-lag mapping
  - known point-in-time bias risk

## Testing Status

- Focused tests were added for:
  - monthly resampling logic
  - monthly return calculation
  - duplicate key detection
  - benchmark alignment
  - one-row-per-ticker-per-month validation
  - fundamentals-to-month lagged merge behavior
  - equal-weight benchmark construction
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `14 passed` on 2026-03-28.
- Pytest still emitted one cache warning because the environment could not create `.pytest_cache` paths under the workspace.

## Manual Verification Status

- `.\.venv\Scripts\python.exe -m src.run_data_ingestion` completed successfully on 2026-03-28 and wrote the required monthly processed artifacts plus QC JSON files.
- `.\.venv\Scripts\python.exe -m src.run_panel_assembly` completed successfully on 2026-03-28 and wrote the canonical monthly panel plus panel QC and coverage CSV outputs.
- Resulting artifact counts were manually checked:
  - `prices_monthly.parquet`: 120 rows, 20 tickers, 2024-01-31 through 2024-06-30
  - `benchmarks_monthly.parquet`: 18 rows, `SPY`, `QQQ`, and `equal_weight_universe`
  - `fundamentals_monthly.parquet`: 120 rows, full ticker-month coverage for the seeded universe over the sample range
  - `monthly_panel.parquet`: 120 rows, 20 tickers by 6 monthly dates, duplicate key count `0`

## Immediate Next Step

- Implement leakage-safe feature generation in `src.features` on top of `outputs/data/monthly_panel.parquet`, with documented lookback windows, lag rules, and missingness outputs.

## Known Risks / Open Issues

- The current raw-data path is local-file-first only. Live or vendor-specific source adapters have not been implemented.
- Fundamentals are not point-in-time safe. The current `2`-month effective lag is a conservative heuristic, not a complete point-in-time solution.
- The equal-weight universe benchmark is a simple research baseline and does not yet model investability, turnover, or transaction costs.
- The current sample raw files are deterministic local fixtures for pipeline verification, not a claim of production data coverage or benchmark-quality research scope.
- Downstream features, signals, backtests, evaluation, and modeling remain intentionally unimplemented in this milestone.

## Current Output Structure

- `outputs/data/prices_monthly.parquet`
- `outputs/data/fundamentals_monthly.parquet`
- `outputs/data/benchmarks_monthly.parquet`
- `outputs/data/monthly_panel.parquet`
- `outputs/data/prices_qc_summary.json`
- `outputs/data/fundamentals_qc_summary.json`
- `outputs/data/benchmarks_qc_summary.json`
- `outputs/data/panel_qc_summary.json`
- `outputs/data/ticker_coverage_summary.csv`
- `outputs/data/date_coverage_summary.csv`
- `outputs/features/feature_panel.parquet`
- `outputs/features/feature_qc_summary.json`
- `outputs/features/feature_missingness_summary.csv`
- `outputs/backtests/holdings_history.parquet`
- `outputs/backtests/trade_log.parquet`
- `outputs/backtests/portfolio_returns.parquet`
- `outputs/backtests/benchmark_returns.parquet`
- `outputs/backtests/backtest_summary.json`
- `outputs/models/train_predictions.parquet`
- `outputs/models/test_predictions.parquet`
- `outputs/models/model_metadata.json`
- `outputs/models/feature_importance.csv`
- `outputs/reports/strategy_report.md`
- `outputs/reports/experiment_registry.jsonl`
- `outputs/reports/performance_by_period.csv`
- `outputs/reports/risk_metrics_summary.csv`
- `outputs/paper_trading/`
