# MarketResearch_ML

This repository is a reproducible market research and portfolio simulation framework for rules-based and later ML-assisted equity selection. The canonical analytic unit is one row per ticker per month.

## Current Status

The deterministic baseline workflow is implemented through evaluation reporting, and the modeling path extends through multi-window out-of-sample evaluation, an aggregated model-driven backtest, and a mode-aware longer-history research execution path. The first remote raw-data acquisition layer is now also implemented upstream of the existing ingestion contract:

- `src.data` ingests local raw market, benchmark, and fundamentals files and assembles the canonical monthly panel
- `src.features` generates leakage-safe monthly features from that panel
- `src.signals` converts the feature panel into deterministic cross-sectional rankings
- `src.backtest` converts those rankings into monthly holdings, turnover, portfolio returns, and benchmark comparisons
- `src.evaluation` builds a benchmark-aware summary from the backtest artifacts
- `src.reporting` writes human-readable strategy reports, a top-level run coverage summary artifact, a model comparison summary artifact, and experiment-registry records
- `src.models` builds leakage-safe labels, fixed or expanding chronological folds, fold-local train-only preprocessing, baseline classifiers, model metadata artifacts, aggregated out-of-sample model score rankings, and model-driven backtest outputs
- `src.run_model_evaluation_report` now writes a model-aware exploratory report from the current canonical model artifacts
- `src.run_fetch_remote_raw` now fetches Alpha Vantage monthly adjusted price history plus overview metadata and SEC Company Facts inputs into immutable local raw snapshots and machine-readable manifests without changing downstream live-API behavior

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

Execution modes:

- default `seeded` mode reads only the packaged sample raw files and preserves the current verification path
- optional `research_scale` mode prefers broader non-sample local raw files under the same raw-data directories and falls back to the packaged sample files when broader coverage is absent

## Implemented Remote Acquisition Layer

The codebase now includes a first upstream remote fetch layer that preserves the local-file-first downstream contract.

Implemented source split:

- Alpha Vantage for security and benchmark price history
- Alpha Vantage `OVERVIEW`-style metadata for sector and industry classification when needed
- SEC EDGAR / Company Facts for filing-based fundamentals

Implemented architectural rule:

- remote fetchers write latest non-sample raw `csv` or `parquet` files plus immutable snapshot copies and dataset manifests under the existing `data/raw/...` directories
- the current `src.run_data_ingestion` and downstream stages continue to read only from local raw files
- no downstream stage should depend directly on live API calls

Implemented first-scope behavior as of 2026-03-30:

- Alpha Vantage supports free API keys, but the free tier is best treated as a bootstrap path for a small universe and low-frequency refreshes
- SEC EDGAR data are publicly accessible, but fetchers must identify themselves properly and respect SEC fair-access expectations
- the implemented fetchers prefer Alpha Vantage monthly adjusted series over premium-only daily-adjusted full-history endpoints because the repo ultimately standardizes to monthly decision frequency
- the implemented SEC mapping is intentionally conservative and leaves many canonical valuation fields unmapped rather than faking completeness
- sector and industry enrichment may come from Alpha Vantage overview snapshots when SEC Company Facts do not provide those classifications directly

Implemented remote raw-data artifacts:

- `data/raw/market/prices_monthly_alphavantage.csv`
- `data/raw/market/snapshots/`
- `data/raw/market/manifests/prices_monthly_alphavantage_manifest.json`
- `data/raw/benchmarks/benchmarks_monthly_alphavantage.csv`
- `data/raw/benchmarks/snapshots/`
- `data/raw/benchmarks/manifests/benchmarks_monthly_alphavantage_manifest.json`
- `data/raw/fundamentals/fundamentals_quarterly_sec_companyfacts.parquet`
- `data/raw/fundamentals/snapshots/`
- `data/raw/fundamentals/manifests/fundamentals_quarterly_sec_companyfacts_manifest.json`
- `data/raw/fundamentals/metadata/security_metadata_alphavantage_overview.csv`
- `data/raw/fundamentals/metadata/snapshots/`
- `data/raw/fundamentals/sec_companyfacts/raw/`
- `data/raw/fundamentals/sec_companyfacts/manifests/sec_companyfacts_raw_manifest.json`
- `data/raw/manifests/remote_fetch_alphavantage_sec_<timestamp>.json`

Required environment variables for live remote fetches:

- `ALPHAVANTAGE_API_KEY`
- `SEC_USER_AGENT` or `SEC_CONTACT_EMAIL`

Persistent repo-local credential file for the PowerShell refresh wrapper:

- Edit `config/remote_provider_env.local.ps1`
- Reference template: `config/remote_provider_env.local.example.ps1`
- Import helper: `scripts/import_remote_provider_env.ps1`

That local file is gitignored. Fill in:

```powershell
$env:ALPHAVANTAGE_API_KEY = "your_alpha_vantage_key"
$env:SEC_CONTACT_EMAIL = "your_email@example.com"
```

Optional:

```powershell
$env:SEC_USER_AGENT = "MarketResearch_ML (your_email@example.com)"
```

Remote fetch config file:

- `config/remote_data.yaml`

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
- `outputs/reports/model_strategy_report.md`
- `outputs/reports/run_summary.json`
- `outputs/reports/model_comparison_summary.json`
- `outputs/reports/model_subperiod_comparison.csv`
- `outputs/reports/experiment_registry.jsonl`

Modeling artifacts:

- `outputs/models/train_predictions.parquet`
- `outputs/models/test_predictions.parquet`
- `outputs/models/model_metadata.json`
- `outputs/models/feature_importance.csv`
- `outputs/models/model_signal_rankings.parquet`

Model-driven backtest artifacts:

- `outputs/backtests/model_holdings_history.parquet`
- `outputs/backtests/model_trade_log.parquet`
- `outputs/backtests/model_portfolio_returns.parquet`
- `outputs/backtests/model_benchmark_returns.parquet`
- `outputs/backtests/model_backtest_summary.json`
- `outputs/backtests/model_performance_by_period.csv`
- `outputs/backtests/model_risk_metrics_summary.csv`

## Config Foundation

Implemented stage config files:

- `config/universe.yaml`
- `config/data.yaml`
- `config/remote_data.yaml`
- `config/features.yaml`
- `config/signals.yaml`
- `config/backtest.yaml`
- `config/execution.yaml`
- `config/evaluation.yaml`
- `config/paths.yaml`
- `config/logging.yaml`
- `config/model.yaml`

## Logic Summary

Data-stage rules:

- monthly dates use calendar month-end
- monthly security and benchmark returns use `adjusted_close_t / adjusted_close_t-1 - 1`
- the equal-weight benchmark is the simple average of available constituent monthly returns, chained from `100.0`
- fundamentals are mapped with a conservative `2`-month effective lag and `12`-month staleness cap
- `config/execution.yaml` controls whether raw-file discovery stays on the seeded verification files or prefers broader local non-sample files
- ingestion QC now records the selected raw-file set, per-file filesystem metadata, observed raw row and date coverage, whether broader local raw files were available, and whether research-scale mode had to fall back to the sample files

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
- model-aware reporting now compares model-driven backtest returns against the deterministic baseline only on overlapping realized dates
- model-aware reporting now writes configurable regime and subperiod diagnostics from the overlap window by fold, calendar quarter, calendar half-year, calendar year, benchmark direction, benchmark drawdown state, and benchmark volatility state
- reports now write `outputs/reports/run_summary.json` with raw-data selection context, compact per-dataset raw provenance overviews, stage-level coverage counts, eligible modeling decision-month counts, and deterministic-vs-model overlap-month counts
- segment evidence is now classified deterministically as `insufficient_segment_history`, `descriptive_segment_evidence`, or `broader_coverage_exploratory_evidence` using thresholds from `config/evaluation.yaml`
- bias caveats are written directly into the strategy report
- meaningful evaluation-report runs append one JSONL record to `outputs/reports/experiment_registry.jsonl`
- once remote acquisition is implemented, reporting should distinguish seeded local fixtures from Alpha Vantage / SEC sourced research runs through raw-data provenance manifests rather than narrative guesswork

Modeling-stage rules:

- labels are derived from future realized returns only and align month-end decision date `t` to realized label date `t+1`
- the default initial label is `forward_excess_return_top_n_binary`
- under that default, a row is labeled `1` when the ticker finishes inside the top `N=10` next-month benchmark-relative returns across the decision-month cross-section
- chronological evaluation is config-driven and now defaults to `expanding_walk_forward`
- the current default walk-forward settings are `min_train_periods=2`, `validation_window_periods=0`, `test_window_periods=1`, and `step_periods=1`
- on the seeded sample this produces two folds with held-out decision months `2024-04-30` and `2024-05-31`
- preprocessing is numeric-only and fit on training rows only using median imputation plus scaling, refit separately inside each fold
- the current main runner writes the configured selected model to the canonical model artifact paths, while model-specific CLIs overwrite those same canonical paths for their own run
- modeling runs append a cautious exploratory record to `outputs/reports/experiment_registry.jsonl`

Model-driven backtest rules:

- `src.run_model_backtest` reads aggregated out-of-sample model predictions from `outputs/models/test_predictions.parquet`
- only the configured out-of-sample splits are eligible for portfolio formation, currently `test`
- model scores are ranked cross-sectionally within each decision month using `predicted_probability`
- the model backtest reuses the same holdings, turnover, cost, benchmark, and metric logic as the deterministic baseline
- when explicit realized label dates are available, they override next-ranking-date inference so sparse held-out prediction months still map correctly to realized `t+1` returns
- model-driven backtest outputs are written to separate `model_*` artifacts under `outputs/backtests/`

Model-aware reporting rules:

- `src.run_model_evaluation_report` reads `model_metadata.json`, `test_predictions.parquet`, deterministic `performance_by_period.csv`, and the `model_*` backtest artifacts
- it combines out-of-sample classification diagnostics with model-driven portfolio and benchmark metrics, fold coverage, an overlap-aware deterministic-vs-model comparison, exploratory regime/subperiod diagnostics, and a cross-stage coverage audit
- it writes `outputs/reports/model_strategy_report.md`
- it writes `outputs/reports/run_summary.json`
- it writes `outputs/reports/model_comparison_summary.json`
- it writes `outputs/reports/model_subperiod_comparison.csv`
- it appends a `model_evaluation_report` record to `outputs/reports/experiment_registry.jsonl`

Important caveat:

- Point-in-time-safe fundamentals are still not solved. Lagged fundamentals and fundamentals-derived signals therefore still carry revised-history bias risk.

Planned remote-acquisition caveat:

- SEC Company Facts can materially improve auditability relative to opaque revised vendor snapshots, but the first remote implementation will still require careful mapping from filing facts into the repo's canonical fundamentals schema and should not be treated as fully point-in-time safe without explicit filing-date logic and release-timing controls.

## CLI Entrypoints

Run ingestion:

```powershell
.\.venv\Scripts\python.exe -m src.run_data_ingestion
```

Run ingestion in research-scale mode:

```powershell
.\.venv\Scripts\python.exe -m src.run_data_ingestion --execution-mode research_scale
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

Run the aggregated out-of-sample model-driven backtest:

```powershell
.\.venv\Scripts\python.exe -m src.run_model_backtest
```

Run the model-aware report:

```powershell
.\.venv\Scripts\python.exe -m src.run_model_evaluation_report
```

Research-scale end-to-end path:

```powershell
.\.venv\Scripts\python.exe -m src.run_data_ingestion --execution-mode research_scale
.\.venv\Scripts\python.exe -m src.run_panel_assembly --execution-mode research_scale
.\.venv\Scripts\python.exe -m src.run_feature_generation --execution-mode research_scale
.\.venv\Scripts\python.exe -m src.run_signal_generation --execution-mode research_scale
.\.venv\Scripts\python.exe -m src.run_backtest --execution-mode research_scale
.\.venv\Scripts\python.exe -m src.run_evaluation_report --execution-mode research_scale
.\.venv\Scripts\python.exe -m src.run_modeling_baselines --execution-mode research_scale
.\.venv\Scripts\python.exe -m src.run_model_backtest --execution-mode research_scale
.\.venv\Scripts\python.exe -m src.run_model_evaluation_report --execution-mode research_scale
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

End-to-end through the default multi-window modeling runner:

```powershell
.\.venv\Scripts\python.exe -m src.run_data_ingestion
.\.venv\Scripts\python.exe -m src.run_panel_assembly
.\.venv\Scripts\python.exe -m src.run_feature_generation
.\.venv\Scripts\python.exe -m src.run_signal_generation
.\.venv\Scripts\python.exe -m src.run_modeling_baselines
.\.venv\Scripts\python.exe -m src.run_model_backtest
.\.venv\Scripts\python.exe -m src.run_model_evaluation_report
```

Recommended interpreter:

```powershell
.\.venv\Scripts\python.exe -m ...
```

One-shot remote refresh helper:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_remote_refresh_and_research_scale.ps1
```

That helper writes a timestamped run log under `.cache/logs/`, dot-sources `scripts/import_remote_provider_env.ps1`, and expects your persistent local credentials in `config/remote_provider_env.local.ps1`. It also sets `PYTHONDONTWRITEBYTECODE=1` for the duration of the run so it does not create fresh repo-local `__pycache__` folders while executing the fetch-plus-pipeline sequence.
For these CLI runs, console `INFO` logging now goes to stdout instead of stderr, so long-running PowerShell fetches no longer surface normal progress as `NativeCommandError` noise. The wrapper also records explicit child exit codes and writes a clear error block into the timestamped `.cache/logs/...` file before exiting on failure.

Remote raw-data fetch entrypoint:

```powershell
. .\scripts\import_remote_provider_env.ps1
.\.venv\Scripts\python.exe -m src.run_fetch_remote_raw --provider alphavantage_sec --execution-mode research_scale
```

The command is implemented. It now logs a deterministic fetch run id, dataset-stage start/end markers, requested symbol lists, per-symbol start/completion/failure events, Alpha Vantage and SEC pacing sleeps, throttle detection, row/date summaries before writes, written file paths, and a final completed-versus-failed symbol summary. It also skips later Alpha Vantage stages once a daily quota condition is detected, avoids overwriting latest/snapshot raw CSVs with zero-row outputs, and now decodes gzip-compressed SEC responses correctly. Live provider verification still depends on supplying the required environment variables.
The local-file-first reader also ignores headerless empty non-sample CSVs, so `research_scale` can still fall back to the seeded sample files when an upstream fetch wrote an unusable empty CSV.

## Verification

Automated verification:

- `.\.venv\Scripts\python.exe -m pytest -q`

Manual verification completed on 2026-03-28:

- `.\.venv\Scripts\python.exe -m src.run_signal_generation`
- `.\.venv\Scripts\python.exe -m src.run_backtest`
- `.\.venv\Scripts\python.exe -m src.run_evaluation_report`

Manual verification completed on 2026-03-29:

- `.\.venv\Scripts\python.exe -m src.run_modeling_baselines`
- `.\.venv\Scripts\python.exe -m src.run_model_backtest`

Current automated status on 2026-03-29:

- `.\.venv\Scripts\python.exe -m pytest -q` passed with `49 passed`

Manual verification completed on 2026-03-30:

- `.\.venv\Scripts\python.exe -m src.run_modeling_baselines`
- `.\.venv\Scripts\python.exe -m src.run_logistic_regression`
- `.\.venv\Scripts\python.exe -m src.run_model_backtest`
- `.\.venv\Scripts\python.exe -m src.run_model_evaluation_report`
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion --execution-mode research_scale`
- `.\.venv\Scripts\python.exe -m src.run_panel_assembly --execution-mode research_scale`
- `.\.venv\Scripts\python.exe -m src.run_feature_generation --execution-mode research_scale`
- `.\.venv\Scripts\python.exe -m src.run_signal_generation --execution-mode research_scale`
- `.\.venv\Scripts\python.exe -m src.run_backtest --execution-mode research_scale`
- `.\.venv\Scripts\python.exe -m src.run_evaluation_report --execution-mode research_scale`
- `.\.venv\Scripts\python.exe -m src.run_modeling_baselines --execution-mode research_scale`
- `.\.venv\Scripts\python.exe -m src.run_model_backtest --execution-mode research_scale`
- `.\.venv\Scripts\python.exe -m src.run_model_evaluation_report --execution-mode research_scale`

Current automated status on 2026-03-30:

- `.\.venv\Scripts\python.exe -m pytest -q` passed with `74 passed`

Additional manual verification completed on 2026-03-30:

- `.\.venv\Scripts\python.exe -m src.run_fetch_remote_raw --help`
- `.\.venv\Scripts\python.exe -m pytest tests/data/test_remote_fetch.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests/data/test_data_pipeline.py tests/data/test_remote_fetch.py -q`
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion`
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion --execution-mode research_scale`
- `powershell -NoProfile -Command "[scriptblock]::Create((Get-Content 'scripts\run_remote_refresh_and_research_scale.ps1' -Raw)) | Out-Null; Write-Output 'parsed'"`
- `.\.venv\Scripts\python.exe -m src.run_evaluation_report --execution-mode research_scale`
- `.\.venv\Scripts\python.exe -m src.run_modeling_baselines --execution-mode research_scale`
- `.\.venv\Scripts\python.exe -m src.run_model_backtest --execution-mode research_scale`
- `.\.venv\Scripts\python.exe -m src.run_model_evaluation_report --execution-mode research_scale`

Those reruns confirmed that the new remote-fetch code did not break the seeded or `research_scale` ingestion paths, refreshed the QC and reporting artifacts with the existing raw-file provenance fields, and preserved the canonical model/report outputs in the default `logistic_regression` state after the automated suite.

Additional wrapper failure-path verification completed on 2026-03-31 UTC:

- Running `scripts/run_remote_refresh_and_research_scale.ps1` with `ALPHAVANTAGE_API_KEY`, `SEC_USER_AGENT`, and `SEC_CONTACT_EMAIL` intentionally unset produced `wrapper_exit_code=1` and wrote an explicit error block to `.cache/logs/remote_refresh_research_scale_20260331T035813Z.log` without attempting live provider calls.

Additional automated verification completed on 2026-03-31:

- `.\.venv\Scripts\python.exe -m pytest -q tests/data/test_remote_fetch.py`
- `.\.venv\Scripts\python.exe -m pytest -q`

Those checks covered the SEC gzip decode fix, Alpha Vantage daily-quota detection helper, and the zero-row write-skip behavior after the live `2026-03-31` quota failure revealed both issues.

Live remote provider calls were not manually exercised on 2026-03-30 because this workspace verification pass did not use credentials.

## Best Next Step

Run the first credentialed `src.run_fetch_remote_raw --provider alphavantage_sec --execution-mode research_scale` fetch, inspect the written raw manifests for throttle or partial-failure conditions, and then rerun the full `research_scale` downstream path on the fetched broader local coverage.
