# Current Status

## Current Milestone

- Data-ingestion, canonical monthly-panel assembly, leakage-safe feature generation, deterministic signal generation, and deterministic monthly backtesting are implemented for the local-file-first workflow

## What Is Completed

- `src.data` includes config-driven modules for raw file ingestion, standardization, benchmark construction, QC, and deterministic monthly panel assembly.
- `src.features` includes config loading, leakage-safe feature engineering, feature QC, and feature missingness summaries.
- `src.signals` includes:
  - signal-stage config loading
  - cross-sectional feature scoring with explicit directionality
  - available-feature weighted composite-score construction
  - deterministic tie-breaking
  - top-N selection flags
  - signal QC and selection summaries
- `src.backtest` now includes:
  - backtest-stage config loading
  - holdings construction from `signal_rankings.parquet`
  - monthly trade-log generation and turnover summaries
  - next-period return alignment using holdings formed at `t` and returns realized at `t+1`
  - turnover-based transaction cost application
  - benchmark alignment for `SPY`, `QQQ`, and `equal_weight_universe`
  - risk metrics, per-period comparison tables, and compact QC reporting
- `config/backtest.yaml` now also documents the backtest cash-handling policy.
- `config/paths.yaml` now routes the stage-level performance tables to:
  - `outputs/backtests/performance_by_period.csv`
  - `outputs/backtests/risk_metrics_summary.csv`
- `src/run_backtest.py` now reads:
  - `outputs/signals/signal_rankings.parquet`
  - `outputs/data/monthly_panel.parquet`
  - `outputs/data/benchmarks_monthly.parquet`
  and writes:
  - `outputs/backtests/holdings_history.parquet`
  - `outputs/backtests/trade_log.parquet`
  - `outputs/backtests/portfolio_returns.parquet`
  - `outputs/backtests/benchmark_returns.parquet`
  - `outputs/backtests/backtest_summary.json`
  - `outputs/backtests/performance_by_period.csv`
  - `outputs/backtests/risk_metrics_summary.csv`

## Testing Status

- Focused backtest tests were added for:
  - holdings construction from deterministic selections
  - equal-weight and capped-weight allocation behavior
  - next-period return alignment
  - trade-log generation and turnover calculation
  - transaction cost application
  - benchmark alignment
  - max drawdown
  - duplicate-key detection
  - empty selected-month handling
- `tests/test_repo_skeleton.py` now runs `src.run_backtest` as an implemented stage.
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `34 passed` on 2026-03-28.
- Pytest still emitted one cache warning because the environment could not create `.pytest_cache` paths under the workspace.

## Manual Verification Status

- `.\.venv\Scripts\python.exe -m src.run_backtest` completed successfully on 2026-03-28.
- Resulting backtest artifacts were manually checked:
  - `holdings_history.parquet`: 50 rows, duplicate `date`-`ticker` keys `0`
  - `trade_log.parquet`: 14 trade rows
  - `portfolio_returns.parquet`: 5 realized monthly periods from `2024-02-29` through `2024-06-30`
  - `benchmark_returns.parquet`: 15 aligned benchmark rows covering `SPY`, `QQQ`, and `equal_weight_universe`
  - `backtest_summary.json`: holding-period convention, config snapshot, metrics, and QC summary present
- Current sample-history consequence was manually confirmed:
  - the first realized backtest period is a cash-only month because the first signal month has no scoreable names and therefore no formed holdings

## Immediate Next Step

- Implement `src.evaluation` and `src.reporting` so the backtest artifacts feed benchmark-relative interpretation, experiment logging, and report generation.

## Known Risks / Open Issues

- The current raw-data path is local-file-first only. Live or vendor-specific source adapters are not implemented.
- Fundamentals are not point-in-time safe. The current upstream lag rules are conservative heuristics, not a complete point-in-time solution.
- Fundamentals-derived features and signals therefore still carry revised-history bias risk.
- The current sample raw files are deterministic local fixtures for pipeline verification, not benchmark-quality research data.
- The current backtest uses a simple linear turnover cost model and `0.0` cash return baseline.
- Very short sample histories make annualized metrics unstable and unsuitable for strong performance claims.

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
- `outputs/signals/signal_rankings.parquet`
- `outputs/signals/signal_qc_summary.json`
- `outputs/signals/signal_selection_summary.csv`
- `outputs/backtests/holdings_history.parquet`
- `outputs/backtests/trade_log.parquet`
- `outputs/backtests/portfolio_returns.parquet`
- `outputs/backtests/benchmark_returns.parquet`
- `outputs/backtests/backtest_summary.json`
- `outputs/backtests/performance_by_period.csv`
- `outputs/backtests/risk_metrics_summary.csv`
- `outputs/models/train_predictions.parquet`
- `outputs/models/test_predictions.parquet`
- `outputs/models/model_metadata.json`
- `outputs/models/feature_importance.csv`
- `outputs/reports/strategy_report.md`
- `outputs/reports/experiment_registry.jsonl`
- `outputs/paper_trading/`
