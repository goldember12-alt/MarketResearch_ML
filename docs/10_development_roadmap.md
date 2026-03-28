# 10 Development Roadmap

## Current Milestone

Repository skeleton, config contract, and documentation alignment.

## Phase 1: Scaffold And Contract Alignment

Status:

- complete for the initial scaffold

Delivered:

- stage-specific repo structure
- shared config loader
- canonical output-path config
- runnable CLI scaffolds
- aligned docs and progress files

## Phase 2: Data Foundation

Next required deliverables:

- implement raw market, fundamentals, and benchmark ingestion contracts
- validate schemas and coverage
- assemble `outputs/data/monthly_panel.parquet`
- document any point-in-time limitations

## Phase 3: Deterministic Feature Layer

Deliverables:

- leakage-safe monthly feature generation
- QC and missingness summaries
- documented lookback and lag rules

## Phase 4: Deterministic Signal And Backtest Baseline

Deliverables:

- deterministic ranking logic
- portfolio construction
- monthly backtest outputs
- benchmark-relative summary metrics

## Phase 5: Evaluation And Reporting

Deliverables:

- strategy report generation
- experiment registry appends
- period and risk-metric summary tables

## Phase 6: Modeling Baselines

Deliverables:

- label construction
- walk-forward validation datasets
- logistic regression baseline
- random forest baseline

## Phase 7: Expansion And Forward Evaluation

Deliverables:

- broader universe and regime analysis
- diversification robustness studies
- paper-trading-style forward evaluation in `outputs/paper_trading/`
