# 10 Development Roadmap

## Current Milestone

Data foundation and leakage-safe feature layer implemented. The next milestone is deterministic signal generation on top of the feature panel.

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
- focused automated tests for feature formulas, lag behavior, missingness summaries, and CLI execution

Remaining risks inside this phase:

- short histories naturally leave long-lookback features missing
- numeric imputation is intentionally not implemented yet
- fundamentals-derived features still inherit revised-history bias risk

## Phase 4: Deterministic Signal And Backtest Baseline

Next deliverables:

- deterministic ranking logic
- signal artifact schema
- portfolio construction
- monthly backtest outputs
- benchmark-relative summary metrics

## Phase 5: Evaluation And Reporting

Deferred deliverables:

- strategy report generation
- experiment registry appends
- period and risk-metric summary tables

## Phase 6: Modeling Baselines

Deferred deliverables:

- label construction
- walk-forward validation datasets
- logistic regression baseline
- random forest baseline

## Phase 7: Expansion And Forward Evaluation

Deferred deliverables:

- broader universe and regime analysis
- diversification robustness studies
- paper-trading-style forward evaluation in `outputs/paper_trading/`
