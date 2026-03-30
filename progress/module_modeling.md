# Module Progress: Modeling

## Current State
- Implemented baseline stage with leakage-safe labels, fixed and expanding chronological splits, fold-local train-only preprocessing, logistic regression, random forest, canonical multi-window model artifacts, and an aggregated out-of-sample model-driven backtest handoff

## Files Touched
- `config/model.yaml`
- `config/paths.yaml`
- `src/models/config.py`
- `src/models/labels.py`
- `src/models/datasets.py`
- `src/models/windows.py`
- `src/models/preprocessing.py`
- `src/models/baselines.py`
- `src/models/evaluation.py`
- `src/models/qc.py`
- `src/models/pipeline.py`
- `src/models/backtest.py`
- `src/run_modeling_baselines.py`
- `src/run_logistic_regression.py`
- `src/run_random_forest.py`
- `src/run_model_backtest.py`
- `tests/models/test_modeling_baselines.py`
- `tests/models/test_model_backtest.py`
- `tests/test_repo_skeleton.py`

## Completed Work
- Implemented forward-label construction aligned to month-end decision date `t` and realized label date `t+1`
- Implemented the default `forward_excess_return_top_n_binary` label using future benchmark-relative returns
- Implemented deterministic joins from the feature panel and monthly panel with duplicate-key validation
- Implemented explicit fixed windows plus expanding walk-forward folds from `config/model.yaml`
- Implemented train-only median imputation and scaling through a preprocessing pipeline that is refit separately inside each fold
- Implemented logistic-regression and random-forest baseline runners
- Implemented aggregated train and out-of-sample prediction artifacts, fold-aware metadata/QC output writing, and mean-across-fold feature-importance export
- Added deterministic signal comparison context to prediction artifacts and model metadata when `signal_rankings.parquet` is available
- Appended exploratory modeling records to `outputs/reports/experiment_registry.jsonl`
- Implemented aggregated out-of-sample model-score ranking conversion and a runnable model-driven backtest handoff through `src.run_model_backtest`

## Testing Status
- Added focused synthetic tests for:
  - forward-label alignment
  - duplicate-key detection
  - expanding walk-forward split construction
  - preprocessing fit-on-train-only behavior
  - backward-compatible fixed-window logistic-regression output shape
  - aggregated out-of-sample prediction assembly
  - random-forest walk-forward output shape
  - fold-aggregated feature-importance export
  - final-month missing-label handling
  - aggregated out-of-sample split filtering for model backtests
  - model-score ranking and top-N selection
- `tests/test_repo_skeleton.py` now runs:
  - `src.run_modeling_baselines`
  - `src.run_logistic_regression`
  - `src.run_random_forest`
  - `src.run_model_backtest`
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `53 passed` on 2026-03-30

## Manual Verification Status
- `.\.venv\Scripts\python.exe -m src.run_modeling_baselines` completed successfully on 2026-03-30
- `.\.venv\Scripts\python.exe -m src.run_model_backtest` completed successfully on 2026-03-30
- Resulting artifacts were manually checked:
  - `outputs/models/train_predictions.parquet`
  - `outputs/models/test_predictions.parquet`
  - `outputs/models/model_metadata.json`
  - `outputs/models/feature_importance.csv`
  - `outputs/models/model_signal_rankings.parquet`
  - `outputs/backtests/model_portfolio_returns.parquet`
  - `outputs/backtests/model_backtest_summary.json`

## Known Issues / Risks
- The seeded sample still yields only two walk-forward held-out decision months, so realized-period coverage remains short
- Fundamentals remain lagged heuristics rather than point-in-time-safe history
- The seeded sample history is still short and uses deterministic local fixture data

## Immediate Next Step
- Add model-aware reporting comparable to the deterministic strategy report and extend walk-forward evaluation over longer history
