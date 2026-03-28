# Current Status

## Current Milestone

- Data-ingestion, canonical monthly-panel assembly, and leakage-safe feature generation implemented for the local-file-first workflow

## What Is Completed

- `src.data` includes config-driven modules for raw file ingestion, standardization, benchmark construction, QC, and deterministic monthly panel assembly.
- `src.features` now includes:
  - feature-stage config loading
  - lagged and rolling price-feature generation
  - lagged market-cap, valuation, profitability, growth, and balance-sheet feature generation
  - feature QC summary generation
  - feature missingness summary generation
- `config/features.yaml` was extended to document the implemented feature families, lookbacks, lag periods, and beta benchmark.
- `src/run_feature_generation.py` now reads `outputs/data/monthly_panel.parquet` and writes:
  - `outputs/features/feature_panel.parquet`
  - `outputs/features/feature_qc_summary.json`
  - `outputs/features/feature_missingness_summary.csv`
- The docs and handoff files were updated to document:
  - the implemented feature schema
  - price-feature formulas
  - lag rules for predictive inputs
  - missingness behavior
  - remaining revised-history bias risk in fundamentals-derived features

## Testing Status

- Focused feature tests were added for:
  - lagged return and rolling momentum calculations
  - fundamentals one-period lag behavior
  - one-row-per-ticker-per-month preservation in the feature panel
  - feature missingness summary output
- `tests/test_repo_skeleton.py` now runs the feature-generation CLI as an implemented stage rather than a scaffold-only stage.
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `19 passed` on 2026-03-28.
- Pytest still emitted one cache warning because the environment could not create `.pytest_cache` paths under the workspace.

## Manual Verification Status

- `.\.venv\Scripts\python.exe -m src.run_feature_generation` completed successfully on 2026-03-28.
- Resulting feature artifacts were manually checked:
  - `feature_panel.parquet`: 120 rows, 20 tickers, 6 monthly dates
  - `feature_qc_summary.json`: 22 feature columns, duplicate key count `0`
  - `feature_missingness_summary.csv`: per-feature missingness and first valid dates present
- Current sample-history consequence was manually confirmed:
  - `mom_12m`, `drawdown_12m`, `vol_12m`, and `beta_12m_spy` remain fully missing on the current 6-month sample window, which is expected and visible in QC

## Immediate Next Step

- Implement `src.signals` to convert the feature panel into deterministic cross-sectional rankings with documented ranking logic and tie-breaking rules.

## Known Risks / Open Issues

- The current raw-data path is local-file-first only. Live or vendor-specific source adapters are not implemented.
- Fundamentals are not point-in-time safe. The current upstream lag rules are conservative heuristics, not a complete point-in-time solution.
- Fundamentals-derived features therefore still carry revised-history bias risk.
- The current sample raw files are deterministic local fixtures for pipeline verification, not benchmark-quality research data.
- Signals, portfolio construction, backtesting, evaluation, and modeling remain intentionally unimplemented in this milestone.

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
