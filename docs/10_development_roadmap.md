# 10 Development Roadmap

## Current Milestone

Data foundation, leakage-safe feature layer, deterministic signal layer, and deterministic backtest baseline are implemented. The next milestone is evaluation and reporting on top of the backtest artifacts.

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
- standardized monthly price, benchmark, and fundamentals artifacts
- deterministic equal-weight benchmark construction
- canonical `outputs/data/monthly_panel.parquet`
- data QC JSON outputs and coverage CSV outputs

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
- focused automated tests for scoring direction, minimum-feature gating, tie-break behavior, and CLI execution

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
- focused automated tests for holdings, turnover, alignment, costs, benchmarks, drawdown, duplicate keys, and empty-month handling

Remaining risks inside this phase:

- current sample data are deterministic fixtures, not benchmark-quality research data
- very short histories make annualized metrics unstable
- fundamentals-derived signals still inherit revised-history bias risk

## Phase 6: Evaluation And Reporting

Next deliverables:

- strategy report generation
- experiment registry appends
- formal benchmark-relative diagnostics and interpretation rules

## Phase 7: Modeling Baselines

Deferred deliverables:

- label construction
- walk-forward validation datasets
- logistic regression baseline
- random forest baseline

## Phase 8: Expansion And Forward Evaluation

Deferred deliverables:

- broader universe and regime analysis
- diversification robustness studies
- paper-trading-style forward evaluation in `outputs/paper_trading/`
