# Current Status

## Current Milestone

- Data ingestion, canonical monthly-panel assembly, leakage-safe feature generation, deterministic signal generation, deterministic monthly backtesting, baseline evaluation reporting, multi-window modeling baselines, aggregated out-of-sample model-driven backtesting, and overlap-aware model-aware reporting with exploratory subperiod diagnostics are implemented for the local-file-first workflow

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
  - markdown model-strategy-report rendering
  - machine-readable model comparison summary generation
  - machine-readable model subperiod comparison generation
  - overlap-aware deterministic-vs-model comparison reporting on shared realized dates only
  - held-out fold coverage diagnostics in model-aware reporting
  - overlap-window regime and subperiod diagnostics by fold, calendar bucket, and benchmark direction
  - experiment-registry record creation
  - JSONL append logic for meaningful evaluation-report, modeling-baseline, model-backtest, and model-evaluation-report runs
- `src.models` includes:
  - config loading for the modeling stage
  - forward-label construction from the monthly panel
  - deterministic modeling-dataset assembly and duplicate-key validation
  - config-driven fixed windows plus expanding walk-forward fold generation
  - fold-local train-only median-imputation and scaling preprocessing
  - logistic-regression and random-forest baseline runners
  - split-level and aggregated out-of-sample classification metrics with fold-aware metadata
  - aggregated out-of-sample model-score ranking conversion for backtesting
  - model-driven backtest summary and experiment-registry record construction
- `src.run_evaluation_report.py` reads the backtest outputs and writes:
  - `outputs/reports/strategy_report.md`
  - `outputs/reports/experiment_registry.jsonl`
- `src.run_model_evaluation_report.py` reads the current canonical model metadata plus model-driven backtest outputs and writes:
  - `outputs/reports/model_strategy_report.md`
  - `outputs/reports/model_comparison_summary.json`
  - `outputs/reports/model_subperiod_comparison.csv`
  - `outputs/reports/experiment_registry.jsonl`
- `src.run_modeling_baselines.py` reads the feature panel, monthly panel, and deterministic signal context and writes:
  - `outputs/models/train_predictions.parquet`
  - `outputs/models/test_predictions.parquet`
  - `outputs/models/model_metadata.json`
  - `outputs/models/feature_importance.csv`
- `src.run_model_backtest.py` reads held-out model predictions and writes:
  - `outputs/models/model_signal_rankings.parquet`
  - `outputs/backtests/model_holdings_history.parquet`
  - `outputs/backtests/model_trade_log.parquet`
  - `outputs/backtests/model_portfolio_returns.parquet`
  - `outputs/backtests/model_benchmark_returns.parquet`
  - `outputs/backtests/model_performance_by_period.csv`
  - `outputs/backtests/model_risk_metrics_summary.csv`
  - `outputs/backtests/model_backtest_summary.json`

## Testing Status

- Focused modeling tests were added for:
  - forward-label alignment
  - duplicate-key detection
  - expanding walk-forward split generation
  - preprocessing fit-on-train-only behavior
  - backward-compatible fixed-window baseline output shape
  - aggregated out-of-sample prediction assembly
  - random-forest walk-forward output shape
  - fold-aggregated feature-importance export
  - final-month missing-label handling
- Focused model-backtest tests were added for:
  - aggregated out-of-sample split filtering
  - model-score ranking and top-N selection
- Focused model-evaluation comparison tests were added for:
  - overlap-aware deterministic-vs-model comparison logic
  - held-out fold coverage diagnostics
  - comparison-convention metadata
  - overlap-window subperiod and regime diagnostics
- `tests/backtest/test_backtest_pipeline.py` now also covers explicit realized-period-end override behavior for sparse ranking inputs.
- `tests/test_repo_skeleton.py` now runs:
  - `src.run_evaluation_report`
  - `src.run_modeling_baselines`
  - `src.run_logistic_regression`
  - `src.run_random_forest`
  - `src.run_model_backtest`
  - `src.run_model_evaluation_report`
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `56 passed` on 2026-03-30.
- Pytest still emitted one cache warning because the environment could not create `.pytest_cache` paths under the workspace.

## Manual Verification Status

- `.\.venv\Scripts\python.exe -m src.run_evaluation_report` completed successfully on 2026-03-28.
- Resulting reporting artifacts were manually checked:
  - `strategy_report.md`: benchmark context, portfolio metrics, risk controls, caveats, interpretation, and next step present
  - `experiment_registry.jsonl`: append behavior confirmed and required high-level fields present
- `.\.venv\Scripts\python.exe -m src.run_modeling_baselines` completed successfully on 2026-03-30.
- Resulting modeling artifacts were manually checked:
  - `train_predictions.parquet`: concatenated fold-level train predictions present with `fold_id` and fold-window columns
  - `test_predictions.parquet`: aggregated out-of-sample rows present for decision dates `2024-04-30` and `2024-05-31`, with split `test` only
  - `model_metadata.json`: split scheme `expanding_walk_forward`, fold count `2`, out-of-sample date range, preprocessing fold summary, metrics, dropped-row summary, and caveats present
  - `feature_importance.csv`: fold-aggregated importance export present for the fitted model
- `.\.venv\Scripts\python.exe -m src.run_model_backtest` completed successfully on 2026-03-30.
- Resulting model-driven backtest artifacts were manually checked:
  - `model_signal_rankings.parquet`: aggregated out-of-sample prediction rows ranked cross-sectionally by model score for decision dates `2024-04-30` and `2024-05-31`
  - `model_portfolio_returns.parquet`: realized model-driven returns aligned to the explicit `t+1` realized dates
  - `model_risk_metrics_summary.csv`: portfolio and benchmark metrics present
  - `model_backtest_summary.json`: model type, split scheme, fold count, prediction splits used, shared backtest metrics, and caveats present
- `.\.venv\Scripts\python.exe -m src.run_model_evaluation_report` completed successfully on 2026-03-30.
- Resulting model-aware reporting artifacts were manually checked:
  - `model_strategy_report.md`: model diagnostics, fold coverage, overlap-aware deterministic comparison, regime/subperiod diagnostics, benchmark comparison, risk controls, caveats, interpretation, and next step present
  - `model_comparison_summary.json`: comparison convention, fold diagnostics, overlap-only deterministic-vs-model metrics, and subperiod diagnostics metadata present
  - `model_subperiod_comparison.csv`: overlap segments present for fold, calendar, and benchmark-direction breakdowns
  - `experiment_registry.jsonl`: append behavior confirmed for `model_evaluation_report` with overlap comparison and subperiod content in `result_summary`
- `.\.venv\Scripts\python.exe -m src.run_logistic_regression` was rerun successfully on 2026-03-30 after the automated suite to restore the canonical selected-model artifacts to the default `logistic_regression` state before rerunning `src.run_model_backtest` and `src.run_model_evaluation_report`.
- Previous manual verification for `src.run_backtest` remains valid:
  - the backtest outputs used by reporting and modeling comparison context were present and aligned before the modeling run

## Immediate Next Step

- Extend the realized overlap history so the new regime and subperiod diagnostics can be evaluated over materially longer windows and support stronger attribution for model-driven runs.

## Known Risks / Open Issues

- The current raw-data path is local-file-first only. Live or vendor-specific source adapters are not implemented.
- Fundamentals are not point-in-time safe. The current upstream lag rules are conservative heuristics, not a complete point-in-time solution.
- Fundamentals-derived features and signals therefore still carry revised-history bias risk.
- The current sample raw files are deterministic local fixtures for pipeline verification, not benchmark-quality research data.
- The current backtest uses a simple linear turnover cost model and `0.0` cash return baseline.
- The current model-driven backtest now uses aggregated out-of-sample windows, but realized-period coverage is still short.
- Very short sample histories make annualized metrics unstable and unsuitable for strong performance claims.
- Regime and subperiod diagnostics are now implemented, but longer-history overlap evaluation and richer attribution are still deferred.

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
- `outputs/backtests/model_holdings_history.parquet`
- `outputs/backtests/model_trade_log.parquet`
- `outputs/backtests/model_portfolio_returns.parquet`
- `outputs/backtests/model_benchmark_returns.parquet`
- `outputs/backtests/model_backtest_summary.json`
- `outputs/backtests/model_performance_by_period.csv`
- `outputs/backtests/model_risk_metrics_summary.csv`
- `outputs/reports/strategy_report.md`
- `outputs/reports/model_strategy_report.md`
- `outputs/reports/model_comparison_summary.json`
- `outputs/reports/model_subperiod_comparison.csv`
- `outputs/reports/experiment_registry.jsonl`
- `outputs/models/train_predictions.parquet`
- `outputs/models/test_predictions.parquet`
- `outputs/models/model_metadata.json`
- `outputs/models/feature_importance.csv`
- `outputs/models/model_signal_rankings.parquet`
- `outputs/paper_trading/`
