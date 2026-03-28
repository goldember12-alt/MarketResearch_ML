# 10 Development Roadmap

## Current Milestone

Data foundation implemented. The next milestone is leakage-safe feature generation on top of the canonical monthly panel.

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

- `src.data` config-driven ingestion modules
- raw local file contract under `data/raw/market`, `data/raw/benchmarks`, and `data/raw/fundamentals`
- standardized monthly price, benchmark, and fundamentals artifacts
- deterministic equal-weight universe benchmark construction
- canonical `outputs/data/monthly_panel.parquet`
- dataset QC JSON outputs
- ticker and date coverage CSV outputs
- focused automated tests for resampling, returns, duplicate keys, benchmark alignment, panel-grid validation, and fundamentals lag mapping

Remaining risks inside this phase:

- production-grade vendor adapters are not implemented yet
- point-in-time-safe fundamentals are still unresolved
- equal-weight benchmark construction is a research baseline, not an investable execution model

## Phase 3: Deterministic Feature Layer

Next deliverables:

- leakage-safe monthly feature generation from `outputs/data/monthly_panel.parquet`
- documented lookback windows and lag rules
- feature QC and missingness summaries
- updated schema and progress documentation

## Phase 4: Deterministic Signal And Backtest Baseline

Deferred deliverables:

- deterministic ranking logic
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
