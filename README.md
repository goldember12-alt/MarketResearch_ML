# MarketResearch_ML

This repository is a reproducible market research and portfolio simulation framework for rules-based and later ML-assisted equity selection. The canonical analytic unit is one row per ticker per month, and the first implementation target is a deterministic monthly ranking and top-N portfolio workflow with explicit benchmark comparison.

## Current Status

The repo is intentionally scaffolded, not fully implemented. The current deliverable is a clean project contract:

- canonical directories and artifact paths
- concrete research preset and benchmark definitions
- typed config loading shared by all CLI entrypoints
- stage-specific runner modules that expose expected inputs, outputs, and the next implementation step
- aligned docs and progress files that state what exists versus what is still only planned

No completed research result, benchmark outcome, or out-of-sample claim is included in this scaffold.

## Canonical Research Preset

- Frequency: monthly
- Analytic unit: one row per ticker per month
- Initial universe: large-cap US tech plus a large-cap non-tech comparison group
- Explicit benchmarks: `SPY`, `QQQ`
- Derived benchmark: `equal_weight_universe`
- Initial portfolio form: cross-sectional ranking, top `N=10`, equal weight, monthly rebalance
- Scaffold transaction cost default: `10` bps per rebalance trade and `0` bps slippage

Seeded tickers in `config/universe.yaml`:

- Tech: `AAPL`, `MSFT`, `NVDA`, `AMZN`, `META`, `GOOGL`, `AVGO`, `ORCL`, `CRM`, `ADBE`
- Comparison: `JPM`, `JNJ`, `PG`, `UNH`, `HD`, `WMT`, `XOM`, `CVX`, `COST`, `KO`

## Repository Layout

- `src/data/`: ingestion, standardization, panel assembly
- `src/features/`: leakage-safe feature generation
- `src/signals/`: deterministic scoring and ranking
- `src/portfolio/`: portfolio construction rules
- `src/backtest/`: return simulation and benchmark comparison
- `src/models/`: later ML baselines and model runners
- `src/evaluation/`: metrics, diagnostics, and period analysis
- `src/reporting/`: strategy report and experiment logging
- `config/`: universe, features, backtest, model, logging, and output-path config
- `docs/`: canonical project, schema, and methodology definitions
- `progress/`: current handoff state and module-level status
- `outputs/`: stage-specific artifact roots

## Canonical Artifacts

Primary artifacts are defined in `config/paths.yaml` and documented in `docs/03_data_schema.md`.

- `outputs/data/monthly_panel.parquet`
- `outputs/features/feature_panel.parquet`
- `outputs/backtests/backtest_summary.json`
- `outputs/models/model_metadata.json`
- `outputs/reports/strategy_report.md`
- `outputs/reports/experiment_registry.jsonl`

## Config Foundation

The scaffold uses these config files as the current operating contract:

- `config/universe.yaml`: seeded universe, benchmark set, calendar
- `config/backtest.yaml`: rebalance, portfolio, and cost assumptions
- `config/features.yaml`: initial feature families, lookbacks, lags, missingness policy
- `config/model.yaml`: label and chronology-safe validation defaults
- `config/paths.yaml`: canonical output directories and artifact paths
- `config/logging.yaml`: logging defaults

## CLI Entrypoints

The CLI modules are intentionally minimal but runnable. Each one loads the shared project contract, ensures the output directories exist, and prints the expected inputs, outputs, and next implementation step.

```powershell
.\.venv\Scripts\python.exe -m src.run_data_ingestion
.\.venv\Scripts\python.exe -m src.run_panel_assembly
.\.venv\Scripts\python.exe -m src.run_feature_generation
.\.venv\Scripts\python.exe -m src.run_signal_generation
.\.venv\Scripts\python.exe -m src.run_backtest
.\.venv\Scripts\python.exe -m src.run_modeling_baselines
.\.venv\Scripts\python.exe -m src.run_logistic_regression
.\.venv\Scripts\python.exe -m src.run_random_forest
.\.venv\Scripts\python.exe -m src.run_evaluation_report
```

Recommended interpreter for all repo work:

```powershell
.\.venv\Scripts\python.exe -m ...
```

Repo-local scratch paths:

- `.tmp/`
- `.cache/`

## Best Next Implementation Step

Implement `src.data` first:

1. add raw-to-standardized ingestion contracts for prices, fundamentals, and benchmarks
2. validate keyed schemas and date coverage
3. assemble `outputs/data/monthly_panel.parquet` with deterministic joins and benchmark alignment
