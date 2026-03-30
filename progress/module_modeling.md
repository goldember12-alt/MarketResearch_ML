# Module Progress: Modeling

## Current State
- Implemented baseline stage with leakage-safe labels, fixed chronological splits, train-only preprocessing, logistic regression, random forest, and canonical model artifacts

## Files Touched
- `config/model.yaml`
- `src/models/config.py`
- `src/models/labels.py`
- `src/models/datasets.py`
- `src/models/preprocessing.py`
- `src/models/baselines.py`
- `src/models/evaluation.py`
- `src/models/qc.py`
- `src/models/pipeline.py`
- `src/run_modeling_baselines.py`
- `src/run_logistic_regression.py`
- `src/run_random_forest.py`
- `tests/models/test_modeling_baselines.py`
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
- `tests/test_repo_skeleton.py` now runs:
  - `src.run_modeling_baselines`
  - `src.run_logistic_regression`
  - `src.run_random_forest`
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `46 passed` on 2026-03-29

## Manual Verification Status
- `.\.venv\Scripts\python.exe -m src.run_modeling_baselines` completed successfully on 2026-03-29
- Resulting artifacts were manually checked:
  - `outputs/models/train_predictions.parquet`
  - `outputs/models/test_predictions.parquet`
  - `outputs/models/model_metadata.json`
  - `outputs/models/feature_importance.csv`

## Known Issues / Risks
- Current split windows are fixed date windows, not yet walk-forward folds
- Current modeling metrics are classification diagnostics only; no model-driven portfolio backtest exists yet
- Fundamentals remain lagged heuristics rather than point-in-time-safe history
- The seeded sample history is still short and uses deterministic local fixture data

## Immediate Next Step
- Route model scores into a model-driven signal or holdings path and evaluate them through the existing benchmark-aware backtest/reporting workflow
