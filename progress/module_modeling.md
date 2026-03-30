# Module Progress: Modeling

## Current State
- Implemented baseline stage with leakage-safe labels, fixed chronological splits, train-only preprocessing, logistic regression, random forest, canonical model artifacts, and an initial held-out model-driven backtest handoff

## Files Touched
- `config/model.yaml`
- `config/paths.yaml`
- `src/models/config.py`
- `src/models/labels.py`
- `src/models/datasets.py`
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
- Implemented explicit train, validation, and test windows from `config/model.yaml`
- Implemented train-only median imputation and scaling through a preprocessing pipeline
- Implemented logistic-regression and random-forest baseline runners
- Implemented prediction artifacts, feature-importance export, and metadata/QC output writing
- Added deterministic signal comparison context to prediction artifacts and model metadata when `signal_rankings.parquet` is available
- Appended exploratory modeling records to `outputs/reports/experiment_registry.jsonl`
- Implemented held-out model-score ranking conversion and a runnable model-driven backtest handoff through `src.run_model_backtest`

## Testing Status
- Added focused synthetic tests for:
  - forward-label alignment
  - duplicate-key detection
  - chronological split construction
  - preprocessing fit-on-train-only behavior
  - logistic-regression output shape
  - random-forest output shape
  - feature-importance export
  - final-month missing-label handling
  - held-out split filtering for model backtests
  - model-score ranking and top-N selection
- `tests/test_repo_skeleton.py` now runs:
  - `src.run_modeling_baselines`
  - `src.run_logistic_regression`
  - `src.run_random_forest`
  - `src.run_model_backtest`
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `49 passed` on 2026-03-29

## Manual Verification Status
- `.\.venv\Scripts\python.exe -m src.run_modeling_baselines` completed successfully on 2026-03-29
- `.\.venv\Scripts\python.exe -m src.run_model_backtest` completed successfully on 2026-03-29
- Resulting artifacts were manually checked:
  - `outputs/models/train_predictions.parquet`
  - `outputs/models/test_predictions.parquet`
  - `outputs/models/model_metadata.json`
  - `outputs/models/feature_importance.csv`
  - `outputs/models/model_signal_rankings.parquet`
  - `outputs/backtests/model_portfolio_returns.parquet`
  - `outputs/backtests/model_backtest_summary.json`

## Known Issues / Risks
- Current split windows are fixed date windows, not yet walk-forward folds
- The current model-driven backtest only spans the available held-out validation/test window
- Fundamentals remain lagged heuristics rather than point-in-time-safe history
- The seeded sample history is still short and uses deterministic local fixture data

## Immediate Next Step
- Expand the current held-out model backtest into walk-forward multi-window evaluation and add model-aware reporting comparable to the deterministic strategy report
