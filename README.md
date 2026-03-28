# MarketResearch_ML

This repository is a reproducible market research and portfolio simulation framework for rules-based and later ML-assisted equity selection. The canonical analytic unit is one row per ticker per month.

## Current Status

The data foundation and leakage-safe feature layer are implemented.

- `src.data` ingests local raw market, benchmark, and fundamentals files and assembles the canonical monthly panel
- `src.features` generates leakage-safe monthly features from that panel
- data and feature QC artifacts are written to deterministic output paths
- signals, portfolio construction, backtesting, evaluation, and modeling remain intentionally downstream

No benchmark-quality research result, trading claim, or out-of-sample ML claim is included.

## Canonical Research Preset

- Frequency: monthly
- Analytic unit: one row per ticker per month
- Initial universe: large-cap US tech plus a large-cap non-tech comparison group
- Explicit benchmarks: `SPY`, `QQQ`
- Derived benchmark: `equal_weight_universe`

Seeded tickers in `config/universe.yaml`:

- Tech: `AAPL`, `MSFT`, `NVDA`, `AMZN`, `META`, `GOOGL`, `AVGO`, `ORCL`, `CRM`, `ADBE`
- Comparison: `JPM`, `JNJ`, `PG`, `UNH`, `HD`, `WMT`, `XOM`, `CVX`, `COST`, `KO`

## Implemented Raw Data Contract

The current pipeline is local-file-first. Raw inputs live under:

- `data/raw/market/`
- `data/raw/benchmarks/`
- `data/raw/fundamentals/`

Supported raw file types:

- `.csv`
- `.parquet`

Repo-local deterministic sample inputs are included so ingestion, panel assembly, and feature generation are runnable now without live connectors.

## Implemented Outputs

Processed data artifacts:

- `outputs/data/prices_monthly.parquet`
- `outputs/data/fundamentals_monthly.parquet`
- `outputs/data/benchmarks_monthly.parquet`
- `outputs/data/monthly_panel.parquet`

Data QC artifacts:

- `outputs/data/prices_qc_summary.json`
- `outputs/data/fundamentals_qc_summary.json`
- `outputs/data/benchmarks_qc_summary.json`
- `outputs/data/panel_qc_summary.json`
- `outputs/data/ticker_coverage_summary.csv`
- `outputs/data/date_coverage_summary.csv`

Feature artifacts:

- `outputs/features/feature_panel.parquet`
- `outputs/features/feature_qc_summary.json`
- `outputs/features/feature_missingness_summary.csv`

## Config Foundation

Implemented stage config files:

- `config/universe.yaml`
- `config/data.yaml`
- `config/features.yaml`
- `config/paths.yaml`
- `config/logging.yaml`

Later-stage config remains scaffolded:

- `config/backtest.yaml`
- `config/model.yaml`

## Data And Feature Logic Summary

Data-stage rules:

- monthly dates use calendar month-end
- monthly security and benchmark returns use `adjusted_close_t / adjusted_close_t-1 - 1`
- the equal-weight benchmark is the simple average of available constituent monthly returns, chained from `100.0`
- fundamentals are mapped with a conservative `2`-month effective lag and `12`-month staleness cap

Feature-stage rules:

- predictive feature inputs are lagged to use only information available through `t-1`
- price features currently include `ret_1m_lag1`, `mom_3m`, `mom_6m`, `mom_12m`, `drawdown_12m`, `vol_12m`, `beta_12m_spy`, `adjusted_close_lag1`, and `benchmark_return_lag1`
- fundamental features are shifted one monthly period and currently include lagged market-cap, valuation, profitability, growth, and balance-sheet metrics
- `numeric_fill` remains `none` so missingness stays visible instead of being silently imputed

Important caveat:

- Point-in-time-safe fundamentals are still not solved. The current lagged mapping is conservative, but revised-history bias remains a known risk.

## CLI Entrypoints

Run ingestion:

```powershell
.\.venv\Scripts\python.exe -m src.run_data_ingestion
```

Run panel assembly:

```powershell
.\.venv\Scripts\python.exe -m src.run_panel_assembly
```

Run feature generation:

```powershell
.\.venv\Scripts\python.exe -m src.run_feature_generation
```

Other stage entrypoints remain scaffold-only:

```powershell
.\.venv\Scripts\python.exe -m src.run_signal_generation
.\.venv\Scripts\python.exe -m src.run_backtest
.\.venv\Scripts\python.exe -m src.run_modeling_baselines
.\.venv\Scripts\python.exe -m src.run_logistic_regression
.\.venv\Scripts\python.exe -m src.run_random_forest
.\.venv\Scripts\python.exe -m src.run_evaluation_report
```

Recommended interpreter:

```powershell
.\.venv\Scripts\python.exe -m ...
```

## Verification

Automated verification:

- `.\.venv\Scripts\python.exe -m pytest -q`

Manual verification completed on 2026-03-28:

- `.\.venv\Scripts\python.exe -m src.run_data_ingestion`
- `.\.venv\Scripts\python.exe -m src.run_panel_assembly`
- `.\.venv\Scripts\python.exe -m src.run_feature_generation`

## Best Next Step

Implement `src.signals` to turn the feature panel into deterministic cross-sectional rankings before any backtesting or ML work.
