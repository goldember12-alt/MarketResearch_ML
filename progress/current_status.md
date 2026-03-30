# Current Status

## Current Milestone

- Data ingestion, canonical monthly-panel assembly, leakage-safe feature generation, deterministic signal generation, deterministic monthly backtesting, baseline evaluation reporting, and initial modeling baselines are implemented for the local-file-first workflow

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
- `src.evaluation` includes structured benchmark-aware evaluation summaries derived from the backtest artifacts.
- `src.reporting` includes:
  - markdown strategy-report rendering
  - experiment-registry record creation
  - JSONL append logic for meaningful evaluation-report and modeling-baseline runs
- `src.models` includes:
  - config loading for the modeling stage
  - forward-label construction from the monthly panel
  - deterministic modeling-dataset assembly and duplicate-key validation
  - config-driven fixed train/validation/test windows
  - train-only median-imputation and scaling preprocessing
  - logistic-regression and random-forest baseline runners
  - split-level classification metrics and compact QC metadata
- `src.run_evaluation_report.py` reads the backtest outputs and writes:
  - `outputs/reports/strategy_report.md`
  - `outputs/reports/experiment_registry.jsonl`
- `src.run_modeling_baselines.py` reads the feature panel, monthly panel, and deterministic signal context and writes:
  - `outputs/models/train_predictions.parquet`
  - `outputs/models/test_predictions.parquet`
  - `outputs/models/model_metadata.json`
  - `outputs/models/feature_importance.csv`

## Testing Status

- Focused modeling tests were added for:
  - forward-label alignment
  - duplicate-key detection
  - chronological split construction
  - preprocessing fit-on-train-only behavior
  - logistic-regression baseline output shape
  - random-forest baseline output shape
  - feature-importance export
  - final-month missing-label handling
- `tests/test_repo_skeleton.py` now runs:
  - `src.run_evaluation_report`
  - `src.run_modeling_baselines`
  - `src.run_logistic_regression`
  - `src.run_random_forest`
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `46 passed` on 2026-03-29.
- Pytest still emitted one cache warning because the environment could not create `.pytest_cache` paths under the workspace.

## Manual Verification Status

- `.\.venv\Scripts\python.exe -m src.run_evaluation_report` completed successfully on 2026-03-28.
- Resulting reporting artifacts were manually checked:
  - `strategy_report.md`: benchmark context, portfolio metrics, risk controls, caveats, interpretation, and next step present
  - `experiment_registry.jsonl`: append behavior confirmed and required high-level fields present
- `.\.venv\Scripts\python.exe -m src.run_modeling_baselines` completed successfully on 2026-03-29.
- Resulting modeling artifacts were manually checked:
  - `train_predictions.parquet`: train split only, model probabilities/classes, and deterministic comparison columns present
  - `test_predictions.parquet`: validation and test rows present with split indicators
  - `model_metadata.json`: label definition, split windows, preprocessing fit window, metrics, dropped-row summary, and caveats present
  - `feature_importance.csv`: importance export present for the fitted model
- Previous manual verification for `src.run_backtest` remains valid:
  - the backtest outputs used by reporting and modeling comparison context were present and aligned before the modeling run

## Immediate Next Step

- Route model scores into a model-driven portfolio construction and backtest path so the baseline models can be evaluated under the same benchmark, turnover, and reporting controls as the deterministic strategy.

## Known Risks / Open Issues

- The current raw-data path is local-file-first only. Live or vendor-specific source adapters are not implemented.
- Fundamentals are not point-in-time safe. The current upstream lag rules are conservative heuristics, not a complete point-in-time solution.
- Fundamentals-derived features and signals therefore still carry revised-history bias risk.
- The current sample raw files are deterministic local fixtures for pipeline verification, not benchmark-quality research data.
- The current backtest uses a simple linear turnover cost model and `0.0` cash return baseline.
- The current modeling stage is prediction-diagnostic only; model-driven holdings and portfolio evaluation are still deferred.
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
