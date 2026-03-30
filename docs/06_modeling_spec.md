# 06 Modeling Specification

## Position In The Workflow

Modeling is a later but first-class stage that begins only after the deterministic feature, signal, backtest, and reporting workflow is in place.

The implemented baseline modeling stage now supports both:

- backward-compatible fixed date windows
- expanding walk-forward multi-window evaluation that accumulates a deterministic out-of-sample prediction history

The model-driven backtest consumes only the aggregated out-of-sample prediction artifact and remains exploratory because the current local sample history is still short.

## Implemented Baseline Runners

- deterministic score baseline comparison context from `outputs/signals/signal_rankings.parquet` when available
- logistic regression baseline
- random forest baseline

Runner behavior:

- `src.run_modeling_baselines` writes the configured `execution.selected_model` run to the canonical model output paths
- `src.run_logistic_regression` writes a logistic-regression run to those same canonical paths
- `src.run_random_forest` writes a random-forest run to those same canonical paths
- `src.run_model_backtest` reads the current canonical aggregated out-of-sample model predictions and writes separate `model_*` backtest artifacts

## Implemented Label Definition

Current default label in `config/model.yaml`:

- `target_type`: `forward_excess_return_top_n_binary`
- `horizon_months`: `1`
- `benchmark`: `SPY`
- `cross_sectional_top_n`: `10`

Exact convention:

- features are observed at month-end decision date `t`
- realized outcomes are taken from the next realized month-end `t+1`
- `forward_excess_return = monthly_return(t+1) - benchmark_return(t+1)`
- the binary label is `1` when the ticker ranks inside the top `10` future benchmark-relative returns across the decision-month cross-section, else `0`

This label is chosen because it aligns with the repo's canonical early-stage portfolio task: cross-sectional ranking and top-N selection.

Supported but not default label types:

- `forward_excess_return_positive_binary`
- `forward_raw_return_positive_binary`

## Dataset Construction

Required upstream inputs:

- `outputs/features/feature_panel.parquet`
- `outputs/data/monthly_panel.parquet`
- `config/model.yaml`

Optional comparison context:

- `outputs/signals/signal_rankings.parquet`

Implemented dataset rules:

- deterministic joins are keyed by `ticker`, `date`
- duplicate-key checks run on feature, panel, and signal inputs
- rows with missing future labels are dropped
- rows with fewer than the configured minimum non-missing model features are dropped
- retained rows carry:
  - `ticker`
  - decision `date`
  - `realized_label_date`
  - `benchmark_ticker`
  - realized forward raw, benchmark, and excess returns
  - deterministic signal context when available

The dataset builder now creates the full eligible modeling universe first. Fold assignment happens later inside the model runner so the same decision month can safely appear in the training history of later folds without being mislabeled in the base dataset.

## Chronological Split Logic

Supported schemes:

- `fixed_date_windows`
- `expanding_walk_forward`

### Fixed Date Windows

Backward-compatible fixed-window settings remain available through:

- `splits.fixed_date_windows.train`
- `splits.fixed_date_windows.validation`
- `splits.fixed_date_windows.test`

This path produces one fold with explicit train, validation, and test date windows.

### Expanding Walk-Forward

Current default settings in `config/model.yaml`:

- `scheme`: `expanding_walk_forward`
- `min_train_periods`: `2`
- `validation_window_periods`: `0`
- `test_window_periods`: `1`
- `step_periods`: `1`

Implemented behavior:

- each fold trains on all eligible decision months strictly earlier than its held-out prediction month
- preprocessing is fit separately inside each fold's training rows only
- held-out predictions are emitted only for the configured validation and test windows in that fold
- held-out months must be unique across folds
- `step_periods` must be at least `validation_window_periods + test_window_periods` so aggregated out-of-sample predictions do not duplicate decision dates

Current default walk-forward convention on the seeded sample:

- fold 1 train: `2024-02-29` through `2024-03-31`, test: `2024-04-30`
- fold 2 train: `2024-02-29` through `2024-04-30`, test: `2024-05-31`

Implemented chronology safeguards:

- no random shuffling
- fold training dates must end before that fold's validation or test dates begin
- validation and test dates within a fold must not overlap
- aggregated held-out decision dates across folds must be unique
- train-only preprocessing is refit separately inside each fold

## Preprocessing

Implemented preprocessing rules:

- numeric feature selection is config-driven through `dataset.feature_columns`
- median imputation is fit on training rows only
- scaling is fit on training rows only
- preprocessing is applied through a fit/transform pipeline
- all-empty training columns are preserved through imputation rather than being dropped silently
- under multi-window evaluation, the preprocessing pipeline is refit independently in each fold

Current default preprocessing in `config/model.yaml`:

- `numeric_imputation_strategy`: `median`
- `scale_numeric`: `true`

## Implemented Model Features

The current default modeling feature list includes:

- lagged returns and momentum
- drawdown
- rolling volatility and beta
- lagged market cap
- valuation metrics
- profitability metrics
- growth metrics
- balance-sheet metrics

The model stage does not use:

- forward returns
- labels
- deterministic composite score

as predictive input features.

## Implemented Baseline Models

### Logistic Regression

- regularized binary logistic classifier
- config-driven `C`, solver, and max-iteration settings
- trained on fold-specific preprocessed training rows only

### Random Forest

- binary random-forest classifier
- config-driven tree count, depth, leaf size, and max-feature settings
- deterministic random state
- single-process execution for sandbox-safe reproducibility

## Evaluation And Metadata

Canonical outputs:

- `outputs/models/train_predictions.parquet`
- `outputs/models/test_predictions.parquet`
- `outputs/models/model_metadata.json`
- `outputs/models/feature_importance.csv`

Current prediction-artifact behavior:

- `train_predictions.parquet` contains the concatenated in-fold training predictions across folds
- `test_predictions.parquet` contains the concatenated out-of-sample prediction history across folds
- both artifacts include `fold_id`, `fold_index`, fold scheme, and fold window boundary columns
- under the current walk-forward settings, `test_predictions.parquet` is unique on `ticker`, `date` and is the canonical model-backtest input

Current metadata includes:

- label definition and settings
- split scheme and fold settings
- fold count and per-fold window definitions
- feature list used
- preprocessing choices and fold-fit summary
- model type and hyperparameters
- eligible dataset summary and dropped-row summary
- split-level classification metrics
- aggregated out-of-sample classification metrics
- deterministic baseline comparison context
- artifact paths, caveats, and next step guidance

Current evaluation metrics:

- row count
- positive-label count and rate
- predicted-positive count and rate
- accuracy
- balanced accuracy
- precision
- recall
- ROC AUC when defined
- average precision when defined

Deterministic comparison context:

- `deterministic_composite_score`
- `deterministic_selected_top_n`

These are carried into prediction artifacts and compared in `model_metadata.json` when `signal_rankings.parquet` is available.

## Feature Importance Export

Implemented export behavior:

- logistic regression writes absolute and signed standardized coefficients
- random forest writes impurity-based feature importances
- multi-window runs aggregate feature importance by mean across fitted folds and record `window_count`

The export is written to:

- `outputs/models/feature_importance.csv`

## Experiment Tracking

Successful modeling runs append a cautious exploratory record to:

- `outputs/reports/experiment_registry.jsonl`

These records document the label, feature set, split scheme, fold count, out-of-sample date range, fitted model, and classification diagnostics. They are still not benchmark-quality portfolio claims by themselves.

## Model-Driven Backtest Extension

The current repo now supports a multi-window model-driven backtest with these rules:

- source predictions come from `outputs/models/test_predictions.parquet`
- only configured out-of-sample splits are eligible for portfolio formation, currently `test`
- `predicted_probability` is reused as the ranking score
- the shared backtest engine applies the same top-N selection, weighting, turnover, cost, and benchmark logic used by the deterministic baseline
- outputs are written to separate `model_*` artifacts under `outputs/backtests/`

Current limitation:

- the seeded sample still yields only a short realized model-backtest window, so this stage is useful for pipeline verification and exploratory comparison only

## Deferred Work

Still deferred after this stage:

- longer-history walk-forward evaluation on richer research data
- richer model-aware reporting and attribution
- broader robustness analysis across regimes and universes
- hyperparameter search beyond simple baselines
- any deep learning model family
