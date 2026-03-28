# 06 Modeling Specification

## Position In The Workflow

Modeling is a later but first-class stage. It begins only after the deterministic feature, signal, and backtest workflow is in place and documented.

## Initial Baseline Runners

- deterministic score baseline
- logistic regression
- random forest

The scaffold exposes runner modules for these workflows, but no model training logic has been implemented yet.

## Current Label Scaffold

`config/model.yaml` currently defines:

- target type: `forward_excess_return_binary`
- horizon: `3` months
- benchmark: `SPY`
- validation scheme: walk-forward
- minimum train window: `36` months
- test window: `12` months

This is a starting contract, not a final modeling standard.

## Candidate Modeling Tasks

- classify whether a name outperforms the benchmark over the forecast horizon
- compare ML outputs against deterministic ranks on the same monthly panel

## Validation Rules

- split by time only
- no random row shuffling
- fit preprocessing on training data only
- keep feature engineering and label generation leakage-safe
- prefer walk-forward or expanding-window validation
- compare every model against deterministic baselines before claiming value

## Deferred Modeling Choices

- gradient boosting only if justified by a concrete need
- no deep learning in the initial implementation
- no complex ensembling until the baseline dataset and evaluation loop are trusted

## Minimum Deliverables For Any Model Run

- `outputs/models/train_predictions.parquet`
- `outputs/models/test_predictions.parquet`
- `outputs/models/model_metadata.json`
- `outputs/models/feature_importance.csv` when applicable

## Acceptance Standard

A model is only worth keeping if it improves out-of-sample results under the same benchmark, rebalance, cost, and reporting assumptions used for deterministic baselines.
