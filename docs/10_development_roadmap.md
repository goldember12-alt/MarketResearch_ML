# 10 Development Roadmap

## Current Milestone

The deterministic baseline workflow, chronology-safe modeling baselines, walk-forward multi-window model evaluation, aggregated out-of-sample model-driven backtesting, overlap-aware model-aware reporting, the Stage 2 reporting/provenance consistency hardening pass, and the first upstream Alpha Vantage + SEC remote raw-data acquisition layer are implemented. The next milestone is Stage 3: a first credentialed longer-history refresh and downstream rerun on remote-sourced broader local raw coverage.

## Near-Term Implementation Plan

The repo now needs a stabilization-to-research sequence rather than another broad feature burst. The near-term plan is to move from an exploratory seeded verification framework to a stable longer-history research workflow in clearly staged milestones.

### Stage 1: Restore A Fully Green Baseline

Purpose:

- make the currently documented workflow pass cleanly again before adding more scope

Primary work items:

- fix the current `research_scale` ingestion regression in the fundamentals monthly alignment path
- verify datetime coercion and null-handling behavior in the fundamentals staleness logic
- rerun the full automated suite under the repo-local `.venv`
- confirm the seeded and `research_scale` data-stage CLIs both complete successfully

Expected code areas:

- `src/data/fundamentals_data.py`
- `src/data/standardize.py`
- `tests/data/test_data_pipeline.py`
- `tests/test_repo_skeleton.py`

Required verification:

- `.\.venv\Scripts\python.exe -m pytest -q`
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion`
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion --execution-mode research_scale`

Exit criteria:

- no failing automated tests
- no `research_scale` ingestion failure in the current workspace state
- progress files updated with the exact verification result

### Stage 2: Reporting And Provenance Consistency Hardening

Purpose:

- make the repo's self-description trustworthy before using it for broader research runs

Primary work items:

- reconcile machine-readable and markdown reporting for raw-data provenance and broader-history availability
- ensure seeded runs clearly distinguish:
  - broader local raw files exist somewhere in the raw directories
  - the current run actually selected seeded sample files
- add focused tests for the coverage-summary and report-rendering behavior

Expected code areas:

- `src/evaluation/coverage.py`
- `src/reporting/markdown.py`
- `tests/reporting/test_evaluation_reporting.py`
- `tests/evaluation/test_model_comparison.py`

Required verification:

- `.\.venv\Scripts\python.exe -m pytest -q tests/reporting/test_evaluation_reporting.py tests/evaluation/test_model_comparison.py`
- `.\.venv\Scripts\python.exe -m src.run_evaluation_report`
- `.\.venv\Scripts\python.exe -m src.run_model_evaluation_report`

Exit criteria:

- markdown reports and machine-readable run summaries agree on raw-data selection context
- seeded runs do not imply benchmark-quality broader-history evidence

### Stage 3: Make `research_scale` Produce Genuine Longer-History Inputs

Purpose:

- move from sample fallback to actual broader local raw coverage

Primary work items:

- run the credentialed remote refresh path against Alpha Vantage and SEC inputs
- inspect provider manifests for quota, partial-failure, and coverage conditions
- confirm usable non-sample local files exist for:
  - market prices
  - benchmark prices
  - fundamentals
- rerun the downstream `research_scale` path using those local non-sample files

Expected code areas:

- `src/run_fetch_remote_raw.py`
- `src/data/alphavantage.py`
- `src/data/sec_companyfacts.py`
- `scripts/run_remote_refresh_and_research_scale.ps1`
- `config/remote_data.yaml`

Required verification:

- `.\.venv\Scripts\python.exe -m src.run_fetch_remote_raw --provider alphavantage_sec --execution-mode research_scale`
- full downstream `research_scale` pipeline through reporting

Exit criteria:

- `research_scale` no longer depends on seeded fallback for the main datasets in the run being evaluated
- manifests are written and reviewed for partial-failure conditions
- the resulting run is logged in `outputs/reports/experiment_registry.jsonl`

### Stage 4: Establish The First Meaningful Deterministic Research Baseline

Purpose:

- create the first longer-history benchmark-aware baseline before expanding ML claims

Primary work items:

- rerun deterministic ingestion, panel assembly, feature generation, signal generation, backtesting, and reporting on broader local raw history
- inspect coverage counts, turnover, benchmark gaps, and missingness on the longer run
- document the run as exploratory unless and until point-in-time and data-quality caveats materially improve

Expected code areas:

- deterministic stage CLIs and existing output/reporting paths
- `docs/05_backtest_spec.md`
- `docs/07_evaluation_spec.md`
- `progress/current_status.md`

Required verification:

- full deterministic pipeline under `research_scale`
- manual review of `outputs/reports/strategy_report.md`, `outputs/reports/run_summary.json`, and the experiment registry append

Exit criteria:

- a longer-history deterministic report exists
- benchmark comparisons are based on materially more than the seeded 5 realized months
- docs and progress notes reflect the actual evidence level

### Stage 5: Deepen Modeling Only After The Deterministic Baseline Is Useful

Purpose:

- expand ML evaluation on top of a research-quality deterministic baseline rather than on top of fixtures

Primary work items:

- rerun walk-forward modeling on broader history
- preserve run identity so later model runs do not silently erase comparison context
- compare `logistic_regression` and `random_forest` systematically on the same longer-history windows
- extend overlap-aware deterministic-vs-model reporting once the overlap window is materially longer

Expected code areas:

- `src/models/*`
- `src/run_modeling_baselines.py`
- `src/run_logistic_regression.py`
- `src/run_random_forest.py`
- `src/run_model_backtest.py`
- `src/run_model_evaluation_report.py`

Required verification:

- full modeling path under `research_scale`
- manual review of model metadata, model backtest outputs, and model-aware reports

Exit criteria:

- model evaluation is based on materially longer realized history
- model-versus-deterministic comparisons are not dominated by tiny overlap windows
- output/versioning caveats are documented honestly

### Stage 6: Clean Up Structural Debt Before Forward Evaluation

Purpose:

- reduce confusion and workflow fragility before adding new execution stages

Primary work items:

- decide whether `src/portfolio` should own portfolio construction logic or remain a documented placeholder
- reduce canonical artifact overwrite ambiguity for model runs where practical
- keep provenance, run identity, and experiment logging aligned

Expected code areas:

- `src/portfolio/`
- `src/backtest/`
- `src/models/`
- `src/reporting/registry.py`

Exit criteria:

- the repo structure matches the documented ownership boundaries
- future agents can identify the latest meaningful run without guessing

### Stage 7: Defer Paper Trading Until The Research Core Is Credible

Purpose:

- avoid starting forward evaluation on top of unstable or sample-only evidence

Prerequisites:

- stable green automated suite
- genuine longer-history `research_scale` path
- meaningful deterministic benchmark baseline
- materially longer model overlap windows if model-driven forward evaluation is considered

Deferred deliverables:

- `outputs/paper_trading/` population
- later paper-trading-style orchestration and reporting

## Immediate Priority Order

1. Stage 3: obtain usable broader local raw coverage
2. Stage 4: establish the first meaningful deterministic research run
3. Stage 5: deepen modeling on longer history
4. Stage 6: clean up architectural debt
5. Stage 7: forward evaluation only after the core is credible

## Review Checklist For Future Agents

When picking up this roadmap, verify these facts before claiming progress:

- whether `.\.venv\Scripts\python.exe -m pytest -q` is currently green
- whether `research_scale` still falls back to seeded sample files
- whether markdown reports and `run_summary.json` agree on raw-data selection context, especially when broader local raw files exist on disk but the run still selected seeded sample inputs
- whether the latest canonical model artifacts reflect the configured selected model or a later overwrite
- whether longer-history runs are truly based on non-sample local raw files

## Phase 1: Scaffold And Contract Alignment

Status:

- complete

Delivered:

- repo stage structure
- shared config loader
- canonical output-path config
- runnable downstream scaffolds
- aligned baseline docs and progress files

## Phase 2: Data Foundation

Status:

- implemented for the local-file-first workflow

Delivered:

- config-driven `src.data` ingestion modules
- local raw file contract under `data/raw/market`, `data/raw/benchmarks`, and `data/raw/fundamentals`
- config-driven seeded versus `research_scale` raw-file selection
- standardized monthly price, benchmark, and fundamentals artifacts
- deterministic equal-weight benchmark construction
- canonical `outputs/data/monthly_panel.parquet`
- data QC JSON outputs and coverage CSV outputs
- raw-file selection manifests embedded inside the data QC summaries

## Phase 3: Deterministic Feature Layer

Status:

- implemented

Delivered:

- `src.features` config loader and feature engineering modules
- leakage-safe lagged price features
- lagged market-cap, valuation, profitability, growth, and balance-sheet features
- `outputs/features/feature_panel.parquet`
- `outputs/features/feature_qc_summary.json`
- `outputs/features/feature_missingness_summary.csv`

## Phase 4: Deterministic Signal Layer

Status:

- implemented

Delivered:

- `config/signals.yaml`
- `src.signals` config, scoring, and QC modules
- deterministic cross-sectional percentile scoring with explicit directionality
- composite-score construction with available-feature weighted means
- deterministic tie-breaking and top-N selection flags
- `outputs/signals/signal_rankings.parquet`
- `outputs/signals/signal_qc_summary.json`
- `outputs/signals/signal_selection_summary.csv`

Remaining risks inside this phase:

- short histories naturally leave some long-lookback features missing
- fundamentals-derived signals still inherit revised-history bias risk

## Phase 5: Deterministic Backtest Baseline

Status:

- implemented

Delivered:

- `src.backtest` config, holdings, trades, returns, metrics, and QC modules
- leakage-safe `t` to `t+1` holding convention
- deterministic holdings construction from signal selections
- trade-log and turnover tracking
- turnover-based transaction cost application
- explicit benchmark alignment to `SPY`, `QQQ`, and `equal_weight_universe`
- `outputs/backtests/holdings_history.parquet`
- `outputs/backtests/trade_log.parquet`
- `outputs/backtests/portfolio_returns.parquet`
- `outputs/backtests/benchmark_returns.parquet`
- `outputs/backtests/backtest_summary.json`
- `outputs/backtests/performance_by_period.csv`
- `outputs/backtests/risk_metrics_summary.csv`

Remaining risks inside this phase:

- current sample data are deterministic fixtures, not benchmark-quality research data
- very short histories make annualized metrics unstable
- fundamentals-derived signals still inherit revised-history bias risk

## Phase 6: Evaluation And Reporting

Status:

- implemented with overlap-aware model comparison reporting

Delivered:

- `src.evaluation.summary` for structured benchmark-aware summaries
- `src.reporting.markdown` for strategy report rendering
- `src.reporting.registry` for experiment-registry appends
- runnable `src.run_evaluation_report`
- runnable `src.run_model_evaluation_report`
- `outputs/reports/strategy_report.md`
- `outputs/reports/model_strategy_report.md`
- `outputs/reports/run_summary.json`
- `outputs/reports/model_comparison_summary.json`
- `outputs/reports/model_subperiod_comparison.csv`
- `outputs/reports/experiment_registry.jsonl`
- overlap-aware deterministic-vs-model comparison on shared realized dates only
- held-out fold coverage diagnostics in the model-aware report
- overlap-window regime and subperiod diagnostics by fold, calendar quarter, calendar half-year, calendar year, benchmark direction, benchmark drawdown state, and benchmark volatility state
- structured evidence-tier labeling for insufficient-history versus broader-coverage exploratory segment comparisons

Remaining work inside this phase:

- richer benchmark-relative attribution
- materially longer-history overlap comparison once broader local raw coverage is added

## Phase 6A: Remote Raw-Data Acquisition

Status:

- implemented initial milestone

Target deliverables:

- `config/remote_data.yaml` for provider credentials, fetch settings, overwrite policy, and output naming driven by environment variables
- Alpha Vantage market and benchmark fetchers that write latest non-sample raw files plus immutable snapshots under `data/raw/market` and `data/raw/benchmarks`
- SEC EDGAR / Company Facts fetcher that writes latest non-sample mapped fundamentals plus immutable raw JSON payload snapshots under `data/raw/fundamentals`
- Alpha Vantage overview-style metadata fetch for sector and industry classification support under `data/raw/fundamentals/metadata`
- provider/fetch manifests capturing request scope, fetch timestamps, rate-limit behavior, written raw files, and partial-failure conditions
- runnable `src.run_fetch_remote_raw`

Guardrails for this phase:

- preserve the existing local-file-first downstream architecture
- do not let downstream ingestion, feature, backtest, modeling, or reporting stages call live providers directly
- keep seeded verification files and seeded execution mode intact
- document all provider limitations and point-in-time caveats explicitly

Remaining work inside this phase:

- run the fetch layer with real credentials and inspect the resulting manifests for throttle or partial-failure conditions
- rerun the full `research_scale` downstream path on broader fetched local coverage
- extend the SEC mapping coverage where canonical fields remain intentionally unmapped

## Phase 7: Modeling Baselines

Status:

- implemented baseline

Delivered:

- `src.models` config, label, dataset, preprocessing, evaluation, QC, and baseline-model modules
- explicit forward-return label construction aligned to the month-end `t` to `t+1` convention
- config-driven fixed windows plus expanding walk-forward folds
- train-only preprocessing with median imputation and scaling, refit independently per fold
- deterministic signal comparison context inside prediction artifacts and metadata
- runnable `src.run_modeling_baselines`
- runnable `src.run_logistic_regression`
- runnable `src.run_random_forest`
- `outputs/models/train_predictions.parquet`
- `outputs/models/test_predictions.parquet`
- `outputs/models/model_metadata.json`
- `outputs/models/feature_importance.csv`

Remaining work inside this phase:

- longer-history walk-forward evaluation on richer research data
- richer multi-model comparison without overwriting the same canonical model artifacts

## Phase 7A: Held-Out Model-Driven Backtest

Status:

- implemented with aggregated out-of-sample prediction input

Delivered:

- `src.models.backtest` for converting aggregated out-of-sample model scores into backtestable rankings
- runnable `src.run_model_backtest`
- separate `model_*` backtest artifacts under `outputs/backtests/`
- held-out model-backtest experiment-registry appends

Remaining work inside this phase:

- compare multiple model runs systematically without overwriting the same canonical model artifacts
- extend the realized out-of-sample history with richer research data

## Phase 8: Expansion And Forward Evaluation

Deferred deliverables:

- broader universe and regime analysis
- diversification robustness studies
- paper-trading-style forward evaluation in `outputs/paper_trading/`
