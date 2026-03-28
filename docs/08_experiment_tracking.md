# 08 Experiment Tracking

## Canonical Registry

Meaningful experiment runs should append one record per run to:

- `outputs/reports/experiment_registry.jsonl`

This file is part of the documented contract even though the writer logic is not implemented yet.

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

## Tracking Rules

- Log every meaningful run that produces artifacts or is used for interpretation.
- Preserve prior history; do not overwrite old records silently.
- Mark runs as exploratory versus benchmark-grade.
- Do not claim a canonical benchmark result unless the run is actually logged and the supporting artifacts exist.
- If config hashing or versioning is added later, include it in the record.
