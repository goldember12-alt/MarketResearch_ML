# 06 Modeling Specification

## Position In The Workflow

Modeling is a later but first-class stage that begins only after the deterministic feature, signal, backtest, and reporting workflow is in place.

The implemented baseline modeling stage is label-diagnostic and prediction-oriented. It does not yet convert model scores into portfolio holdings or model-driven backtest results.

## Implemented Baseline Runners

- deterministic score baseline comparison context from `outputs/signals/signal_rankings.parquet` when available
- logistic regression baseline
- random forest baseline

Runner behavior:

- `src.run_modeling_baselines` writes the configured `execution.selected_model` run to the canonical model output paths
- `src.run_logistic_regression` writes a logistic-regression run to those same canonical paths
- `src.run_random_forest` writes a random-forest run to those same canonical paths

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

This label is chosen because it aligns with the repo’s canonical early-stage portfolio task: cross-sectional ranking and top-N selection.

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

## Chronological Split Logic

The current implementation supports explicit fixed date windows only:

- `scheme`: `fixed_date_windows`

Default configured windows:

- train: `2024-02-29` through `2024-03-31`
- validation: `2024-04-30`
- test: `2024-05-31`

Implemented chronology safeguards:

- train, validation, and test windows must be strictly ordered and non-overlapping
- split assignment uses decision dates only
- validation and test rows are never used during preprocessing fit
- the held-out test window remains chronologically after training and validation

## Preprocessing

Implemented preprocessing rules:

- numeric feature selection is config-driven through `dataset.feature_columns`
- median imputation is fit on training rows only
- scaling is fit on training rows only
- preprocessing is applied through a fit/transform pipeline
- all-empty training columns are preserved through imputation rather than being dropped silently

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
- trained on preprocessed training rows only

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

Current metadata includes:

- label definition and settings
- split windows
- feature list used
- preprocessing choices and fit window
- model type and hyperparameters
- row counts by split
- dropped-row summary
- split-level classification metrics
- deterministic baseline comparison context
- caveats and next step

Current evaluation metrics by split:

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

Both are written to the shared canonical path:

- `outputs/models/feature_importance.csv`

## Experiment Tracking

Successful modeling runs append a cautious exploratory record to:

- `outputs/reports/experiment_registry.jsonl`

These records are not model-driven backtest claims. They document the label, feature set, split window, fitted model, and held-out classification diagnostics only.

## Deferred Work

Still deferred after this baseline stage:

- walk-forward or expanding-window multi-fold validation
- model-driven score-to-portfolio conversion
- model-driven backtests under the same transaction cost assumptions
- richer benchmark-relative attribution and reporting
- hyperparameter search beyond simple baselines
- any deep learning model family
