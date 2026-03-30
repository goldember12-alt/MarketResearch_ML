# Module Progress: Backtesting

## Current State

- Deterministic monthly backtest baseline and aggregated out-of-sample model-driven backtest are implemented, with coverage-aware summaries ready for longer-history `research_scale` runs

## Files Touched

- `config/backtest.yaml`
- `config/execution.yaml`
- `config/evaluation.yaml`
- `config/model.yaml`
- `config/paths.yaml`
- `src/backtest/__init__.py`
- `src/backtest/config.py`
- `src/backtest/holdings.py`
- `src/backtest/trades.py`
- `src/backtest/returns.py`
- `src/backtest/metrics.py`
- `src/backtest/qc.py`
- `src/models/backtest.py`
- `src/run_backtest.py`
- `src/run_model_backtest.py`
- `tests/backtest/test_backtest_pipeline.py`
- `tests/models/test_model_backtest.py`
- `tests/test_repo_skeleton.py`
- `README.md`
- `docs/02_system_architecture.md`
- `docs/03_data_schema.md`
- `docs/05_backtest_spec.md`
- `docs/07_evaluation_spec.md`
- `docs/08_experiment_tracking.md`
- `docs/10_development_roadmap.md`
- `progress/current_status.md`

## Completed Work

- Added a dedicated backtest-stage config loader and logging setup.
- Implemented holdings construction from deterministic signal selections.
- Implemented explicit monthly rebalance summaries with cash tracking.
- Implemented month-to-month trade-log generation and turnover calculation.
- Implemented leakage-safe next-period return alignment using holdings formed at month-end `t` and realized returns at month-end `t+1`.
- Implemented a linear turnover-based transaction cost model.
- Implemented benchmark alignment for `SPY`, `QQQ`, and `equal_weight_universe`.
- Implemented portfolio and benchmark cumulative returns, risk metrics, per-period comparison output, compact QC reporting, and explicit coverage counts in backtest summaries.
- Replaced the scaffold backtest CLI with a runnable implementation that writes the canonical deterministic backtest artifacts.
- Added explicit realized-period-end support inside holdings construction for sparse ranking inputs.
- Implemented `src.run_model_backtest` to convert aggregated out-of-sample model predictions into cross-sectional rankings and run them through the shared backtest engine.
- Added separate `model_*` backtest artifacts so model-driven runs do not overwrite deterministic baseline backtest outputs.

## Testing Status

- `tests/backtest/test_backtest_pipeline.py` now covers:
  - holdings construction from rankings
  - equal-weight allocation
  - capped-weight residual cash handling
  - next-period return alignment
  - explicit realized-period-end override behavior
  - turnover calculation
  - transaction cost application
  - benchmark alignment
  - max drawdown
  - duplicate-key detection
  - empty selected-month behavior
- `tests/models/test_model_backtest.py` now covers:
  - aggregated out-of-sample split filtering
  - model-score ranking and top-N selection
  - duplicate-key detection on model predictions
- `tests/test_repo_skeleton.py` now exercises:
  - `src.run_backtest`
  - `src.run_model_backtest`
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `61 passed` on 2026-03-30.

## Manual Verification Status

- `.\.venv\Scripts\python.exe -m src.run_backtest` completed successfully on 2026-03-28.
- `.\.venv\Scripts\python.exe -m src.run_model_backtest` completed successfully on 2026-03-30.
- `.\.venv\Scripts\python.exe -m src.run_backtest --execution-mode research_scale` completed successfully on 2026-03-30.
- `.\.venv\Scripts\python.exe -m src.run_model_backtest --execution-mode research_scale` completed successfully on 2026-03-30.
- Deterministic and model-driven backtest artifacts were manually reviewed for schema, date alignment, output presence, and summary content.

## Known Issues / Risks

- The current backtest assumes a `0.0` cash return and a simple linear turnover cost model.
- Fundamentals-derived inputs still inherit revised-history bias risk.
- The current local sample data are too short to support strong claims from annualized metrics.
- The current model-driven backtest now spans aggregated out-of-sample windows, but the realized sample is still short.
- Broader-history backtest interpretation remains blocked until the upstream `research_scale` path has non-sample local raw files to consume.

## Immediate Next Step

- Rerun the backtest stages on broader non-sample local raw history so the new coverage-aware summaries become materially informative.
