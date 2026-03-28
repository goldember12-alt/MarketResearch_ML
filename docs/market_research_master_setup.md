# Master Setup Document

## Project Title
Market Research System for Rules-Based and ML-Assisted Equity Selection

## Purpose
Build a reproducible research and portfolio simulation system for evaluating stock-selection strategies against benchmarks, starting with deterministic ranking models and expanding into machine learning only after a strong backtesting and data foundation exists.

This project is not intended to begin as a live-trading system. The first priority is research quality, experiment discipline, and avoidance of false confidence caused by data leakage, overfitting, survivorship bias, and uncontrolled backtest assumptions.

---

# 1. Core Objective

Create a modular system that can:
1. Ingest and standardize market and fundamental data.
2. Build a clean historical panel dataset.
3. Generate rules-based features and signals.
4. Simulate portfolios under configurable rebalancing and risk rules.
5. Evaluate strategies against benchmarks.
6. Add ML-based ranking or classification models later.
7. Support paper-trading-style forward evaluation in a later phase.

## First Milestone
Produce a valid, reproducible monthly backtest pipeline for a limited equity universe using deterministic ranking rules.

## Second Milestone
Add ML models such as logistic regression and random forest and compare them against deterministic baselines using walk-forward evaluation.

## Third Milestone
Expand the universe, improve risk controls, and test robustness across market regimes.

---

# 2. Research Principles

## Primary Research Principle
Do not optimize for maximum historical return before proving the pipeline is trustworthy.

## Required Principles
- All features must be based only on data available at the decision date.
- All time splits must respect chronological order.
- All backtests must include configurable transaction cost assumptions.
- All experiments must be reproducible from config files and versioned inputs.
- All benchmark comparisons must be explicit.
- Deterministic baselines must be implemented before ML models.
- Each module must expose clear inputs, outputs, and validation checks.

## Disallowed Early-Stage Behaviors
- No live trading automation.
- No deep learning in the initial implementation.
- No daily-frequency modeling in phase 1 unless explicitly approved later.
- No undocumented manual edits to generated datasets.
- No strategy claims based only on in-sample performance.

---

# 3. Initial Scope

## Initial Universe
Start with a manageable universe, such as:
- Large-cap US tech names.
- A comparison group of large-cap non-tech names.
- Benchmarks such as SPY, QQQ, and an equal-weight universe portfolio.

The universe must be defined in configuration, not hardcoded.

## Initial Frequency
Monthly.

## Initial Strategy Form
Cross-sectional ranking of stocks using deterministic factor-like signals.

## Initial Benchmark Set
- SPY
- QQQ
- Equal-weight universe portfolio

## Initial Target Questions
- Can a simple rules-based stock ranking model outperform benchmarks on a risk-adjusted basis?
- Does diversification beyond tech improve outcomes enough to justify reduced domain familiarity?
- Do ML models outperform deterministic scorecards after realistic controls?
- Which features remain useful across multiple market environments?

---

# 4. System Architecture

The repository should be organized around explicit modules.

## Data Flow
1. Raw data ingestion
2. Standardization and schema validation
3. Historical panel assembly
4. Feature generation
5. Signal generation
6. Portfolio construction
7. Backtesting
8. Evaluation and reporting
9. Experiment logging

## Core Design Rules
- Each stage should write a defined artifact.
- Artifacts should be inspectable and versionable.
- Config files should drive universe, feature set, and backtest settings.
- Each major stage should have tests.
- Each major stage should log summary diagnostics.

---

# 5. Repository Structure

```text
market-research-system/
|-- README.md
|-- AGENTS.md
|-- docs/
|   |-- 00_project_scope.md
|   |-- 01_research_questions.md
|   |-- 02_system_architecture.md
|   |-- 03_data_schema.md
|   |-- 04_feature_spec.md
|   |-- 05_backtest_spec.md
|   |-- 06_modeling_spec.md
|   |-- 07_evaluation_spec.md
|   |-- 08_experiment_tracking.md
|   |-- 09_risk_and_bias_controls.md
|   |-- 10_development_roadmap.md
|   `-- templates/
|       |-- experiment_template.md
|       |-- module_progress_template.md
|       `-- dataset_qc_template.md
|-- progress/
|   |-- current_status.md
|   |-- module_data_pipeline.md
|   |-- module_features.md
|   |-- module_backtesting.md
|   |-- module_modeling.md
|   `-- module_reporting.md
|-- config/
|   |-- universe.yaml
|   |-- features.yaml
|   |-- backtest.yaml
|   |-- model.yaml
|   `-- logging.yaml
|-- src/
|   |-- data/
|   |-- features/
|   |-- signals/
|   |-- portfolio/
|   |-- backtest/
|   |-- models/
|   |-- evaluation/
|   |-- reporting/
|   `-- utils/
|-- tests/
|   |-- data/
|   |-- features/
|   |-- portfolio/
|   |-- backtest/
|   |-- models/
|   `-- evaluation/
|-- notebooks/
|-- outputs/
|   |-- data/
|   |-- features/
|   |-- backtests/
|   |-- models/
|   `-- reports/
`-- scripts/
```

---

# 6. Module Responsibilities

## `src/data/`
Responsible for raw ingestion, standardization, cleaning, schema validation, and historical panel creation.

### Deliverables
- Price history table
- Fundamental data table
- Benchmark table
- Merged monthly panel
- QC summaries

## `src/features/`
Responsible for computing lagged, leakage-safe features.

### Example Features
- trailing returns
- momentum
- drawdown from rolling high
- valuation ratios
- profitability metrics
- growth metrics
- revision metrics if available
- volatility and beta estimates

## `src/signals/`
Responsible for turning features into rankings, composite scores, or model inputs.

## `src/portfolio/`
Responsible for mapping ranked signals into portfolio weights under risk and concentration constraints.

## `src/backtest/`
Responsible for portfolio simulation under realistic rebalancing, transaction cost, and benchmark comparison rules.

## `src/models/`
Responsible for supervised learning models that are added after deterministic baselines are working.

Initial model candidates:
- logistic regression
- random forest
- gradient boosting later if justified

## `src/evaluation/`
Responsible for metrics, diagnostics, benchmark comparison, feature importance summaries, and robustness checks.

## `src/reporting/`
Responsible for generating output tables, charts, experiment summaries, and human-readable reports.

---

# 7. Data Requirements

## Required Initial Datasets
- Historical prices
- Historical returns
- Benchmark prices and returns
- Fundamental metrics by ticker and date
- Sector and industry classifications
- Optional analyst estimate or revision data if available through Morningstar

## Initial Panel Unit
One row per ticker per month.

## Minimum Required Fields
- ticker
- date
- adjusted close
- monthly return
- benchmark return
- sector
- industry
- market cap
- valuation metrics
- profitability metrics
- growth metrics
- optional revisions

## Data Integrity Rules
- No future information may appear in any row's features.
- All derived fields must document the source window and lag rule.
- Missingness must be logged and handled consistently.

---

# 8. Feature Engineering Requirements

Every feature in the system must be documented with:
- feature name
- business intuition
- formula
- data source
- lookback window
- lag rule
- missing-value rule
- expected direction if relevant

## Suggested Initial Feature Groups
### Price-Based
- 1-month return lagged
- 3-month momentum
- 6-month momentum
- 12-month momentum
- drawdown from 52-week high
- rolling volatility
- rolling beta to benchmark

### Valuation-Based
- P/E
- forward P/E if available
- EV/EBITDA
- price/sales
- free-cash-flow yield if available

### Quality / Profitability
- gross margin
- operating margin
- return on equity
- return on assets
- free cash flow margin

### Growth
- revenue growth
- EPS growth
- operating income growth

### Balance Sheet
- debt/equity
- current ratio
- net cash indicator if available

### Estimate / Revision Signals
- earnings estimate revision trend
- target-price revision trend if available

---

# 9. Backtesting Requirements

Backtests must be realistic enough to be informative.

## Required Controls
- Monthly rebalance for phase 1
- Explicit trade date convention
- Transaction cost parameter
- Turnover tracking
- Position caps
- Benchmark comparison
- Cash handling rules
- Optional sector caps

## Minimum Portfolio Simulation Outputs
- portfolio return series
- benchmark return series
- cumulative return
- annualized return
- volatility
- Sharpe ratio
- Sortino ratio
- max drawdown
- turnover
- hit rate
- holdings history

## Initial Portfolio Rules
Start simple:
- rank universe
- hold top N names
- equal-weight or capped-weight portfolio
- rebalance monthly

Do not add complexity before the baseline is working.

---

# 10. Modeling Requirements

ML follows the deterministic-baseline and backtest-hardening phases; it is not part of phase 1.

## Initial Modeling Use Cases
- Predict whether a stock outperforms the benchmark over the next 3 or 6 months.
- Predict cross-sectional rank of forward excess returns.

## Initial Model Candidates
- logistic regression
- linear regression or regularized variants
- random forest

## Validation Rules
- Use chronological train/validation/test splits only.
- Prefer walk-forward or expanding-window validation.
- Never use random shuffling across time.
- Compare every ML model to a deterministic baseline.

## ML Success Standard
An ML model is useful only if it adds value out of sample after realistic backtest assumptions.

---

# 11. Evaluation Requirements

Evaluation must compare performance on both return and risk.

## Required Metrics
- CAGR
- annualized volatility
- Sharpe ratio
- Sortino ratio
- max drawdown
- information ratio vs benchmark
- alpha/beta style comparison if desired
- turnover
- hit rate
- average holding period

## Required Breakdowns
- full period
- subperiods by market regime
- tech-only subset if applicable
- diversified subset if applicable
- benchmark-relative comparisons

## Interpretability Outputs
- feature importance summaries
- coefficient summaries for linear models
- confusion matrix or rank-quality diagnostics where appropriate

---

# 12. Risk and Bias Controls

This project must explicitly guard against the following:
- look-ahead bias
- survivorship bias
- data snooping
- overfitting
- benchmark cherry-picking
- leakage from revised historical fundamentals if applicable
- unrealistic trade execution assumptions

## Mandatory Rule
No strategy result may be presented without a note on potential bias sources and current controls.

---

# 13. Experiment Tracking Rules

Every experiment must log:
- experiment ID
- purpose
- date range
- universe
- features used
- portfolio rules
- model type
- benchmark set
- transaction cost assumptions
- result summary
- interpretation
- next step

Progress documents should be updated whenever a module changes materially.

---

# 14. Development Workflow Rules for Codex / Agentic Development

## General Rules
- Implement one module or submodule at a time.
- Read the relevant docs before editing code.
- Update progress files after meaningful work.
- Do not silently change schemas.
- Do not silently change backtest assumptions.
- Prefer explicit configuration over hardcoding.
- Write tests with each major module.
- Surface assumptions in documentation.

## Required Development Order
1. repository scaffolding
2. config definitions
3. data schema and ingestion
4. panel assembly and QC
5. deterministic features
6. baseline signals
7. portfolio construction
8. backtesting
9. evaluation reporting
10. ML layer

## Code Quality Rules
- modular functions
- type hints where practical
- docstrings for public functions
- no hidden global state
- clear logging
- deterministic outputs where possible

---

# 15. Initial Documentation Tree

## `docs/00_project_scope.md`
Defines scope, goals, initial universe, frequency, success criteria, and non-goals.

## `docs/01_research_questions.md`
Defines the exact research questions and hypothesis list.

## `docs/02_system_architecture.md`
Defines modules, data flow, artifact flow, and implementation boundaries.

## `docs/03_data_schema.md`
Defines tables, fields, keys, data types, and artifact expectations.

## `docs/04_feature_spec.md`
Defines each feature, formula, lag rule, intuition, and dependencies.

## `docs/05_backtest_spec.md`
Defines rebalance rules, ranking rules, costs, turnover logic, benchmarks, and output metrics.

## `docs/06_modeling_spec.md`
Defines target labels, candidate models, validation logic, and ML comparison requirements.

## `docs/07_evaluation_spec.md`
Defines evaluation metrics, regime splits, and output report structure.

## `docs/08_experiment_tracking.md`
Defines experiment logging conventions and result recording templates.

## `docs/09_risk_and_bias_controls.md`
Defines methodological safeguards and required warnings.

## `docs/10_development_roadmap.md`
Defines milestone ordering, implementation phases, and deliverables.

---

# 16. Progress File Expectations

## `progress/current_status.md`
High-level summary of overall project status, active milestone, blockers, and next actions.

## Module Progress Files
Each module progress file should contain:
- current implementation state
- files touched
- known issues
- completed tasks
- next development target
- notes for the next coding session

These should function as handoff documents for Codex or any agent.

---
