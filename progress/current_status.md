# Current Status

## Current Milestone

- Data ingestion, canonical monthly-panel assembly, leakage-safe feature generation, deterministic signal generation, deterministic monthly backtesting, and baseline evaluation reporting are implemented for the local-file-first workflow

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
- `src.backtest` includes:
  - backtest-stage config loading
  - holdings construction from `signal_rankings.parquet`
  - monthly trade-log generation and turnover summaries
  - next-period return alignment using holdings formed at `t` and returns realized at `t+1`
  - turnover-based transaction cost application
  - benchmark alignment for `SPY`, `QQQ`, and `equal_weight_universe`
  - risk metrics, per-period comparison tables, and compact QC reporting
- `src.evaluation` now includes structured benchmark-aware evaluation summaries derived from the backtest artifacts.
- `src.reporting` now includes:
  - markdown strategy-report rendering
  - experiment-registry record creation
  - JSONL append logic for meaningful evaluation-report runs
- `src/run_evaluation_report.py` now reads the backtest outputs and writes:
  - `outputs/reports/strategy_report.md`
  - `outputs/reports/experiment_registry.jsonl`

## Testing Status

- Focused reporting tests were added for:
  - benchmark-aware evaluation summary construction
  - strategy report rendering
  - experiment-registry record creation and append behavior
- `tests/test_repo_skeleton.py` now runs `src.run_evaluation_report` as an implemented stage.
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `38 passed` on 2026-03-28.
- Pytest still emitted one cache warning because the environment could not create `.pytest_cache` paths under the workspace.

## Manual Verification Status

- `.\.venv\Scripts\python.exe -m src.run_evaluation_report` completed successfully on 2026-03-28.
- Resulting reporting artifacts were manually checked:
  - `strategy_report.md`: benchmark context, portfolio metrics, risk controls, caveats, interpretation, and next step present
  - `experiment_registry.jsonl`: append behavior confirmed and required high-level fields present
- Previous manual verification for `src.run_backtest` remains valid:
  - the backtest outputs used by reporting were present and aligned before the report run

## Immediate Next Step

- Implement chronology-safe modeling baselines and compare them against the deterministic signal benchmark using the now-implemented report and experiment-registry workflow.

## Known Risks / Open Issues

- The current raw-data path is local-file-first only. Live or vendor-specific source adapters are not implemented.
- Fundamentals are not point-in-time safe. The current upstream lag rules are conservative heuristics, not a complete point-in-time solution.
- Fundamentals-derived features and signals therefore still carry revised-history bias risk.
- The current sample raw files are deterministic local fixtures for pipeline verification, not benchmark-quality research data.
- The current backtest uses a simple linear turnover cost model and `0.0` cash return baseline.
- Very short sample histories make annualized metrics unstable and unsuitable for strong performance claims.
- Reporting is now implemented, but richer regime diagnostics and attribution are still deferred.

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
- `outputs/reports/strategy_report.md`
- `outputs/reports/experiment_registry.jsonl`
- `outputs/models/train_predictions.parquet`
- `outputs/models/test_predictions.parquet`
- `outputs/models/model_metadata.json`
- `outputs/models/feature_importance.csv`
- `outputs/paper_trading/`
