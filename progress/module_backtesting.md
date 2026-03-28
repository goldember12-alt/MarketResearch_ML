# Module Progress: Backtesting

## Current State

- Deterministic monthly backtest baseline implemented

## Files Touched

- `config/backtest.yaml`
- `config/paths.yaml`
- `src/backtest/__init__.py`
- `src/backtest/config.py`
- `src/backtest/holdings.py`
- `src/backtest/trades.py`
- `src/backtest/returns.py`
- `src/backtest/metrics.py`
- `src/backtest/qc.py`
- `src/run_backtest.py`
- `tests/backtest/test_backtest_pipeline.py`
- `tests/test_repo_skeleton.py`
- `README.md`
- `docs/02_system_architecture.md`
- `docs/03_data_schema.md`
- `docs/05_backtest_spec.md`
- `docs/07_evaluation_spec.md`
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
- Implemented portfolio and benchmark cumulative returns, risk metrics, per-period comparison output, and compact QC reporting.
- Replaced the scaffold backtest CLI with a runnable implementation that writes the canonical backtest artifacts.

## Testing Status

- `tests/backtest/test_backtest_pipeline.py` now covers:
  - holdings construction from rankings
  - equal-weight allocation
  - capped-weight residual cash handling
  - next-period return alignment
  - turnover calculation
  - transaction cost application
  - benchmark alignment
  - max drawdown
  - duplicate-key detection
  - empty selected-month behavior
- `tests/test_repo_skeleton.py` now exercises `src.run_backtest` as an implemented CLI.
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `34 passed` on 2026-03-28.

## Manual Verification Status

- `.\.venv\Scripts\python.exe -m src.run_backtest` completed successfully on 2026-03-28.
- `outputs/backtests/holdings_history.parquet`, `trade_log.parquet`, `portfolio_returns.parquet`, `benchmark_returns.parquet`, `performance_by_period.csv`, `risk_metrics_summary.csv`, and `backtest_summary.json` were manually reviewed for schema, date alignment, and output presence.

## Known Issues / Risks

- The first realized period is cash-only because the first signal month has no scoreable names in the current sample data.
- The current backtest assumes a `0.0` cash return and a simple linear turnover cost model.
- Fundamentals-derived inputs still inherit revised-history bias risk.
- The current local sample data are too short to support strong claims from annualized metrics.

## Immediate Next Step

- Implement evaluation and reporting layers that consume the backtest outputs, append experiment metadata, and formalize benchmark-relative interpretation.
