# MarketResearch_ML

This repository is a reproducible market research and portfolio simulation framework for rules-based and later ML-assisted equity selection. The canonical analytic unit is one row per ticker per month.

## Current Status

The data-ingestion and monthly-panel foundation is implemented.

- `src.data` now ingests local raw market, benchmark, and fundamentals files
- processed monthly artifacts are written to `outputs/data/`
- QC summaries and coverage reports are produced alongside the processed artifacts
- feature engineering, signals, backtests, and modeling remain out of scope for the current implementation and are still scaffolded only

No benchmark-quality research result, trading claim, or out-of-sample ML claim is included.

## Canonical Research Preset

- Frequency: monthly
- Analytic unit: one row per ticker per month
- Initial universe: large-cap US tech plus a large-cap non-tech comparison group
- Explicit benchmarks: `SPY`, `QQQ`
- Derived benchmark: `equal_weight_universe`
- Initial portfolio form later in the roadmap: cross-sectional ranking, top `N=10`, equal weight, monthly rebalance

Seeded tickers in `config/universe.yaml`:

- Tech: `AAPL`, `MSFT`, `NVDA`, `AMZN`, `META`, `GOOGL`, `AVGO`, `ORCL`, `CRM`, `ADBE`
- Comparison: `JPM`, `JNJ`, `PG`, `UNH`, `HD`, `WMT`, `XOM`, `CVX`, `COST`, `KO`

## Raw Data Contract

The current pipeline is local-file-first. Raw inputs live under:

- `data/raw/market/`
- `data/raw/benchmarks/`
- `data/raw/fundamentals/`

Supported raw file types:

- `.csv`
- `.parquet`

Repo-local deterministic sample inputs are included so the ingestion and panel runners are immediately runnable without live connectors.

## Implemented Data Outputs

Primary processed artifacts:

- `outputs/data/prices_monthly.parquet`
- `outputs/data/fundamentals_monthly.parquet`
- `outputs/data/benchmarks_monthly.parquet`
- `outputs/data/monthly_panel.parquet`

QC and coverage artifacts:

- `outputs/data/prices_qc_summary.json`
- `outputs/data/fundamentals_qc_summary.json`
- `outputs/data/benchmarks_qc_summary.json`
- `outputs/data/panel_qc_summary.json`
- `outputs/data/ticker_coverage_summary.csv`
- `outputs/data/date_coverage_summary.csv`

## Config Foundation

The implemented data path uses these config files:

- `config/universe.yaml`: seeded universe, benchmarks, monthly calendar window
- `config/data.yaml`: raw-data locations, month-end convention, column priorities, benchmark defaults, fundamentals lag settings
- `config/paths.yaml`: canonical output directories and artifact paths
- `config/logging.yaml`: logging defaults

Later-stage config remains scaffolded for downstream work:

- `config/backtest.yaml`
- `config/features.yaml`
- `config/model.yaml`

## Data Logic Summary

- Monthly date convention: calendar month-end
- `adjusted_close`: the first available configured adjusted-close alias, with `close` as the last fallback in `config/data.yaml`
- `monthly_return`: `adjusted_close_t / adjusted_close_t-1 - 1` after collapsing raw daily or monthly observations to one month-end row per ticker using the last observation in the month
- `benchmark_return`: the same month-over-month return formula, aligned from the configured primary benchmark `SPY`
- Equal-weight benchmark: simple cross-sectional average of available universe constituent monthly returns for each month, with a chained synthetic adjusted-close series starting at `100.0`
- Fundamentals mapping: raw fundamentals observations are normalized to month-end, shifted forward by a conservative `2`-month effective lag, then mapped to the monthly calendar by ticker using backward as-of logic

Important caveat:

- Point-in-time-safe fundamentals are not solved. The current lagged monthly mapping is conservative, but revised-history bias remains a known risk until a true point-in-time source is added.

## CLI Entrypoints

Run ingestion:

```powershell
.\.venv\Scripts\python.exe -m src.run_data_ingestion
```

Run panel assembly:

```powershell
.\.venv\Scripts\python.exe -m src.run_panel_assembly
```

Other stage entrypoints remain scaffold-only for now:

```powershell
.\.venv\Scripts\python.exe -m src.run_feature_generation
.\.venv\Scripts\python.exe -m src.run_signal_generation
.\.venv\Scripts\python.exe -m src.run_backtest
.\.venv\Scripts\python.exe -m src.run_modeling_baselines
.\.venv\Scripts\python.exe -m src.run_logistic_regression
.\.venv\Scripts\python.exe -m src.run_random_forest
.\.venv\Scripts\python.exe -m src.run_evaluation_report
```

Recommended interpreter for repo work:

```powershell
.\.venv\Scripts\python.exe -m ...
```

## Verification

Automated verification:

- `.\.venv\Scripts\python.exe -m pytest -q`

Manual verification completed on 2026-03-28:

- `.\.venv\Scripts\python.exe -m src.run_data_ingestion`
- `.\.venv\Scripts\python.exe -m src.run_panel_assembly`

## Best Next Step

Implement `src.features` on top of `outputs/data/monthly_panel.parquet` with documented lookback windows, lag rules, and missingness handling.
