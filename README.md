# MarketResearch_ML

This repository is a reproducible market research and portfolio simulation framework for rules-based and later ML-assisted equity selection. The canonical analytic unit is one row per ticker per month.

## Current Status

The deterministic baseline workflow is now implemented through evaluation reporting, and the initial modeling-baselines stage is now implemented:

- `src.data` ingests local raw market, benchmark, and fundamentals files and assembles the canonical monthly panel
- `src.features` generates leakage-safe monthly features from that panel
- `src.signals` converts the feature panel into deterministic cross-sectional rankings
- `src.backtest` converts those rankings into monthly holdings, turnover, portfolio returns, and benchmark comparisons
- `src.evaluation` builds a benchmark-aware summary from the backtest artifacts
- `src.reporting` writes a human-readable strategy report and appends an experiment-registry record
- `src.models` builds leakage-safe labels, chronological splits, train-only preprocessing, baseline classifiers, and model metadata artifacts

No benchmark-quality research conclusion, live-trading claim, or out-of-sample ML claim is included.

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

Repo-local deterministic sample inputs are included so ingestion, panel assembly, feature generation, signal generation, backtesting, and evaluation reporting are runnable now without live connectors.

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

Signal artifacts:

- `outputs/signals/signal_rankings.parquet`
- `outputs/signals/signal_qc_summary.json`
- `outputs/signals/signal_selection_summary.csv`

Backtest artifacts:

- `outputs/backtests/holdings_history.parquet`
- `outputs/backtests/trade_log.parquet`
- `outputs/backtests/portfolio_returns.parquet`
- `outputs/backtests/benchmark_returns.parquet`
- `outputs/backtests/backtest_summary.json`
- `outputs/backtests/performance_by_period.csv`
- `outputs/backtests/risk_metrics_summary.csv`

Reporting artifacts:

- `outputs/reports/strategy_report.md`
- `outputs/reports/experiment_registry.jsonl`

Modeling artifacts:

- `outputs/models/train_predictions.parquet`
- `outputs/models/test_predictions.parquet`
- `outputs/models/model_metadata.json`
- `outputs/models/feature_importance.csv`

## Config Foundation

Implemented stage config files:

- `config/universe.yaml`
- `config/data.yaml`
- `config/features.yaml`
- `config/signals.yaml`
- `config/backtest.yaml`
- `config/paths.yaml`
- `config/logging.yaml`
- `config/model.yaml`

## Logic Summary

Data-stage rules:

- monthly dates use calendar month-end
- monthly security and benchmark returns use `adjusted_close_t / adjusted_close_t-1 - 1`
- the equal-weight benchmark is the simple average of available constituent monthly returns, chained from `100.0`
- fundamentals are mapped with a conservative `2`-month effective lag and `12`-month staleness cap

Feature-stage rules:

- predictive feature inputs are lagged to use only information available through `t-1`
- price features include lagged return, momentum, drawdown, volatility, beta, lagged close, and lagged benchmark return
- fundamental features are shifted one monthly period and include lagged market-cap, valuation, profitability, growth, and balance-sheet metrics
- `numeric_fill` remains `none` so missingness stays visible

Signal-stage rules:

- deterministic rankings are built cross-sectionally by month from configured lagged features
- each feature is converted to a percentile score within the month
- higher-is-better and lower-is-better directions are defined in `config/signals.yaml`
- the composite score is the available-feature weighted mean
- rows must meet the configured minimum non-missing feature count to receive a score
- top `N=10` selection is deterministic and uses tie-breakers `composite_score`, `market_cap_lag1`, then `ticker`

Backtest-stage rules:

- holdings are formed from `signal_rankings.parquet` at month-end decision date `t`
- those holdings earn realized returns over the next monthly period and are booked at month-end `t+1`
- `portfolio_returns.parquet.date` is the realized month-end `t+1`
- transaction costs use a linear one-way turnover model: `turnover * (transaction_cost_bps + slippage_bps) / 10000`
- the current default cash policy is `redistribute`, so if names are selected they are fully invested equally unless a capped-weight configuration says otherwise
- if a selected security is missing a realized return on a valid holding period end, the realized return is filled with `0.0` and logged in QC

Evaluation and reporting rules:

- every generated report is explicitly marked exploratory unless stronger evidence is actually available
- benchmark comparisons are carried through into the report and experiment registry
- bias caveats are written directly into the strategy report
- meaningful evaluation-report runs append one JSONL record to `outputs/reports/experiment_registry.jsonl`

Modeling-stage rules:

- labels are derived from future realized returns only and align month-end decision date `t` to realized label date `t+1`
- the default initial label is `forward_excess_return_top_n_binary`
- under that default, a row is labeled `1` when the ticker finishes inside the top `N=10` next-month benchmark-relative returns across the decision-month cross-section
- chronological splits are explicit and config-driven: train `2024-02-29` through `2024-03-31`, validation `2024-04-30`, test `2024-05-31`
- preprocessing is numeric-only and fit on training rows only using median imputation plus scaling
- the current main runner writes the configured selected model to the canonical model artifact paths, while model-specific CLIs overwrite those same canonical paths for their own run
- modeling runs append a cautious exploratory record to `outputs/reports/experiment_registry.jsonl`

Important caveat:

- Point-in-time-safe fundamentals are still not solved. Lagged fundamentals and fundamentals-derived signals therefore still carry revised-history bias risk.

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

Run signal generation:

```powershell
.\.venv\Scripts\python.exe -m src.run_signal_generation
```

Run backtest:

```powershell
.\.venv\Scripts\python.exe -m src.run_backtest
```

Run evaluation reporting:

```powershell
.\.venv\Scripts\python.exe -m src.run_evaluation_report
```

Run the configured modeling baseline:

```powershell
.\.venv\Scripts\python.exe -m src.run_modeling_baselines
```

Run logistic regression explicitly:

```powershell
.\.venv\Scripts\python.exe -m src.run_logistic_regression
```

Run random forest explicitly:

```powershell
.\.venv\Scripts\python.exe -m src.run_random_forest
```

Full deterministic baseline pipeline:

```powershell
.\.venv\Scripts\python.exe -m src.run_data_ingestion
.\.venv\Scripts\python.exe -m src.run_panel_assembly
.\.venv\Scripts\python.exe -m src.run_feature_generation
.\.venv\Scripts\python.exe -m src.run_signal_generation
.\.venv\Scripts\python.exe -m src.run_backtest
.\.venv\Scripts\python.exe -m src.run_evaluation_report
```

End-to-end through the default modeling runner:

```powershell
.\.venv\Scripts\python.exe -m src.run_data_ingestion
.\.venv\Scripts\python.exe -m src.run_panel_assembly
.\.venv\Scripts\python.exe -m src.run_feature_generation
.\.venv\Scripts\python.exe -m src.run_signal_generation
.\.venv\Scripts\python.exe -m src.run_modeling_baselines
```

Recommended interpreter:

```powershell
.\.venv\Scripts\python.exe -m ...
```

## Verification

Automated verification:

- `.\.venv\Scripts\python.exe -m pytest -q`

Manual verification completed on 2026-03-28:

- `.\.venv\Scripts\python.exe -m src.run_signal_generation`
- `.\.venv\Scripts\python.exe -m src.run_backtest`
- `.\.venv\Scripts\python.exe -m src.run_evaluation_report`

Manual verification completed on 2026-03-29:

- `.\.venv\Scripts\python.exe -m src.run_modeling_baselines`

Current automated status on 2026-03-29:

- `.\.venv\Scripts\python.exe -m pytest -q` passed with `46 passed`

## Best Next Step

Route model scores into model-driven portfolio construction and backtesting under the same benchmark, turnover, and reporting controls already used for the deterministic baseline.
