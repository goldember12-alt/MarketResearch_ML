# 10 Development Roadmap

## Current Milestone

The deterministic baseline workflow, chronology-safe modeling baselines, walk-forward multi-window model evaluation, aggregated out-of-sample model-driven backtesting, and overlap-aware model-aware reporting with structured coverage diagnostics are implemented. The next milestone is longer-history robustness evaluation on broader local raw coverage.

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
