# Current Status

## Current Milestone
- Project skeleton, config foundation, and documentation alignment for the monthly research pipeline

## What Is Completed
- Core repo structure is aligned around the documented stage boundaries: `src.data`, `src.features`, `src.signals`, `src.portfolio`, `src.backtest`, `src.models`, `src.evaluation`, and `src.reporting`.
- The canonical output roots exist and are now documented consistently: `outputs/data`, `outputs/features`, `outputs/backtests`, `outputs/models`, `outputs/reports`, and `outputs/paper_trading`.
- `config/universe.yaml` now defines a concrete seeded research universe, explicit benchmarks, and the monthly calendar.
- `config/backtest.yaml` now defines the initial top-10 equal-weight monthly rebalance baseline and transaction-cost assumptions.
- `config/paths.yaml` was added as the canonical artifact-path contract for data, feature, backtest, model, and reporting outputs.
- `src/utils/config.py` was added to load the shared project contract with typed dataclasses and resolve repo-relative output paths.
- `src/utils/stage_runner.py` was added so every CLI entrypoint shares one scaffold behavior.
- The CLI entrypoints under `src/run_*.py` are now runnable scaffold stages that load config, ensure output directories exist, and print expected inputs, outputs, and the next implementation step.
- `README.md` and the canonical docs in `docs/` were rewritten to match the operating contract in `AGENTS.md`.

## Testing Status
- Repo scaffold tests were updated to cover package imports, shared config loading, canonical artifact paths, and CLI scaffold execution.
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `6 passed` on 2026-03-28.
- Pytest emitted one cache warning because the sandbox could not create `.pytest_cache` paths under the workspace.

## Manual Verification Status
- The seeded universe, benchmark definitions, output paths, and stage runner behavior were reviewed for consistency against `AGENTS.md`.
- The docs were manually checked to ensure they describe scaffolded work only and do not claim completed research results.

## Immediate Next Step
- Implement `src.data` ingestion contracts and monthly panel assembly so `outputs/data/prices_monthly.parquet`, `outputs/data/fundamentals_monthly.parquet`, `outputs/data/benchmarks_monthly.parquet`, and `outputs/data/monthly_panel.parquet` become real artifacts.

## Known Risks / Open Issues
- Data-source selection and field coverage are still unresolved.
- Fundamentals may not be point-in-time safe initially, which creates revised-history risk until documented and mitigated.
- Signal-generation artifacts are scaffolded conceptually but not yet formalized as a persisted schema.
- Transaction-cost defaults are explicit but not yet empirically calibrated.

## Current Output Structure
- `config/universe.yaml`
- `config/backtest.yaml`
- `config/features.yaml`
- `config/model.yaml`
- `config/paths.yaml`
- `config/logging.yaml`
- `outputs/data/prices_monthly.parquet`
- `outputs/data/fundamentals_monthly.parquet`
- `outputs/data/benchmarks_monthly.parquet`
- `outputs/data/monthly_panel.parquet`
- `outputs/features/feature_panel.parquet`
- `outputs/features/feature_qc_summary.json`
- `outputs/features/feature_missingness_summary.csv`
- `outputs/backtests/holdings_history.parquet`
- `outputs/backtests/trade_log.parquet`
- `outputs/backtests/portfolio_returns.parquet`
- `outputs/backtests/benchmark_returns.parquet`
- `outputs/backtests/backtest_summary.json`
- `outputs/models/train_predictions.parquet`
- `outputs/models/test_predictions.parquet`
- `outputs/models/model_metadata.json`
- `outputs/models/feature_importance.csv`
- `outputs/reports/strategy_report.md`
- `outputs/reports/experiment_registry.jsonl`
- `outputs/reports/performance_by_period.csv`
- `outputs/reports/risk_metrics_summary.csv`
- `outputs/paper_trading/`
