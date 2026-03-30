# 08 Experiment Tracking

## Canonical Registry

Meaningful evaluation-report, modeling-baseline, and model-backtest runs append one record per run to:

- `outputs/reports/experiment_registry.jsonl`

The implemented writers append a new JSON object line for every successful `src.run_evaluation_report`, `src.run_modeling_baselines`, and `src.run_model_backtest` execution. Model-specific CLI runs also append records because they overwrite the same canonical model artifacts.

## Minimum Record Fields

- `experiment_id`
- `run_timestamp`
- `stage`
- `purpose`
- `date_range`
- `universe_preset`
- `benchmark_set`
- `feature_set`
- `signal_or_model`
- `portfolio_rules`
- `rebalance_frequency`
- `transaction_cost_bps`
- `artifacts_written`
- `result_summary`
- `interpretation`
- `status`
- `next_step`

## Current Writer Behavior

- preserves prior history by appending, not overwriting
- marks the current stage as `evaluation_report`
- records the deterministic signal baseline and configured feature set
- records benchmark-aware result summaries drawn from the implemented backtest artifacts
- stores exploratory interpretations and next-step guidance alongside each run
- modeling-stage records mark the stage as `modeling_baselines`
- modeling-stage records store the label definition, split window, selected model, and held-out classification diagnostics
- modeling-stage records do not imply a model-driven backtest has been completed
- model-backtest records mark the stage as `model_backtest`
- model-backtest records store the model type, held-out prediction splits used for formation, and benchmark-aware backtest metrics

## Tracking Rules

- Log every meaningful run that produces artifacts or is used for interpretation.
- Preserve prior history; do not overwrite old records silently.
- Mark runs as exploratory versus benchmark-grade.
- Do not claim a canonical benchmark result unless the run is actually logged and the supporting artifacts exist.
- If config hashing or versioning is added later, include it in the record.
