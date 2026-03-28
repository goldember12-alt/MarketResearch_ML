# AGENTS.md

## Project

Build and maintain a reproducible end-to-end market research and portfolio simulation workflow for rules-based and ML-assisted equity selection that covers:

1. study design and research-question definition
2. market and fundamentals data ingestion
3. historical panel assembly
4. feature engineering
5. signal generation
6. portfolio construction
7. backtesting and benchmark comparison
8. ML evaluation with leakage-safe time splits
9. later paper-trading-style forward evaluation

This repo is not only a modeling sandbox. It is a research, simulation, and evaluation framework for testing stock-selection strategies under realistic controls.

## Core Objective

Produce a canonical monthly panel dataset and use it to evaluate whether deterministic and later ML-assisted ranking or classification strategies can outperform explicit benchmarks on a risk-adjusted basis.

Analytic unit:

- one row per ticker per month

Canonical early-stage portfolio task:

- rank stocks cross-sectionally and hold the top N names under explicit portfolio constraints

Grouping structure for evaluation:

- chronological train/validation/test windows
- optional regime segments for robustness analysis

## Canonical Outputs

Primary data artifacts:

- `outputs/data/prices_monthly.parquet`
- `outputs/data/fundamentals_monthly.parquet`
- `outputs/data/benchmarks_monthly.parquet`
- `outputs/data/monthly_panel.parquet`

Feature artifacts:

- `outputs/features/feature_panel.parquet`
- `outputs/features/feature_qc_summary.json`
- `outputs/features/feature_missingness_summary.csv`

Signal and portfolio artifacts:

- `outputs/backtests/holdings_history.parquet`
- `outputs/backtests/trade_log.parquet`
- `outputs/backtests/portfolio_returns.parquet`
- `outputs/backtests/benchmark_returns.parquet`
- `outputs/backtests/backtest_summary.json`

Modeling artifacts:

- `outputs/models/train_predictions.parquet`
- `outputs/models/test_predictions.parquet`
- `outputs/models/model_metadata.json`
- `outputs/models/feature_importance.csv`

Reporting artifacts:

- `outputs/reports/strategy_report.md`
- `outputs/reports/experiment_registry.jsonl`
- `outputs/reports/performance_by_period.csv`
- `outputs/reports/risk_metrics_summary.csv`

Reserved later-stage forward-evaluation artifacts:

- `outputs/paper_trading/`

## Canonical Monthly Panel Columns

Minimum required columns:

- `ticker`
- `date`
- `adjusted_close`
- `monthly_return`
- `benchmark_return`
- `sector`
- `industry`
- `market_cap`
- valuation metrics
- profitability metrics
- growth metrics
- optional revision metrics

Optional later-stage columns may be added only through documented schema updates.

## Workflow Contract

The repo should be treated as an end-to-end lifecycle with these stages:

1. define project scope and research questions
2. define the universe and benchmark set
3. ingest and standardize raw market and fundamental data
4. assemble the historical monthly panel
5. compute leakage-safe features
6. generate deterministic signals and rankings
7. construct portfolios under explicit constraints
8. run realistic backtests against benchmarks
9. evaluate results and document bias controls
10. add ML models only after deterministic baselines are working
11. expand to regime analysis, diversification testing, and forward evaluation

## Data Logic

Study and panel logic:

- The initial canonical frequency is monthly
- The universe must be config-driven, not hardcoded
- The initial universe should begin with large-cap US tech plus a comparison group of large-cap non-tech names
- Benchmarks should explicitly include `SPY`, `QQQ`, and an equal-weight universe portfolio unless documentation changes
- The system must preserve date-aligned benchmark and security data at the decision frequency
- Features must reflect only information available at the decision date

Final assembly rules:

- all panel joins must be keyed deterministically
- all derived features must document the lookback window and lag rule
- missingness must be logged and handled consistently
- revised historical fundamentals must be treated carefully and documented as a possible bias source if point-in-time data are unavailable

## Backtesting Contract

Treat backtesting as a first-class pipeline stage.

Canonical backtesting inputs:

- `outputs/data/monthly_panel.parquet`
- `outputs/features/feature_panel.parquet`
- config-driven universe, feature, and backtest settings

Leakage-safe backtest rules:

- all decisions must use only information available at the rebalance date
- all train/test splits must respect chronological order
- no random shuffling across time for model evaluation
- portfolio construction must use only signals available at the decision date
- transaction cost assumptions must be explicit
- benchmark comparisons must be explicit

Implemented early-stage deterministic portfolio form:

- cross-sectional ranking
- top-N portfolio selection
- equal-weight or capped-weight holdings
- monthly rebalance

Required backtest outputs:

- portfolio return series
- benchmark return series
- cumulative returns
- annualized return
- annualized volatility
- Sharpe ratio
- Sortino ratio
- max drawdown
- turnover
- hit rate
- holdings history

## Modeling Contract

Treat modeling as a later but still first-class pipeline stage.

Canonical modeling inputs:

- `outputs/features/feature_panel.parquet`
- benchmark-relative labels or forward-return labels derived from the monthly panel

Leakage-safe modeling rules:

- split by time, never by random row shuffle
- all preprocessing, imputation, scaling, encoding, and feature selection must be fit on training periods only
- walk-forward or expanding-window validation is preferred
- all ML models must be compared against deterministic score baselines
- no ML claim is valid if it relies only on in-sample performance

Initial model runners to support:

- deterministic score baseline
- logistic regression or regularized linear baseline
- random forest

Deferred model families:

- gradient boosting only if justified
- no deep learning in the initial implementation

Feature-contract guidance for early stock-selection models:

Safe initial predictive feature groups:

- valuation metrics
- profitability metrics
- growth metrics
- lagged returns and momentum
- drawdown from rolling highs
- rolling volatility and beta
- balance-sheet indicators
- estimate and revision signals if available and leakage-safe

Do not use these as predictive features unless explicitly justified and documented:

- forward returns
- benchmark-relative future outcomes
- any target-derived label
- identifiers that leak future grouping or hand-curated outcomes
- any feature that depends on data published after the decision date

## Preset And Benchmarking Rules

`README.md` is the canonical definition of available presets and their meanings.

Use that document as the source of truth for:

- what the initial research preset means
- what a full backtest means
- how to describe benchmarks and universes in methods/results language
- the current feature set and rebalance defaults if they are exposed there

Do not describe exploratory or smoke-style runs as final benchmark-quality results.
Always report:

- the date range
- the universe
- the benchmark set
- the rebalance frequency
- the transaction cost assumptions
- any sample caps or filtering constraints

Meaningful experiment runs should append to:

- `outputs/reports/experiment_registry.jsonl`

Do not claim a canonical benchmark result has been completed unless it is actually logged in the relevant docs and registry.

## Python Environment Rules

Use the repo-local virtual environment as the standard interpreter when available:

```powershell
.\\.venv\\Scripts\\python.exe -m ...
```

Environment rules:

- prefer the repo-local `.venv` for normal repo work
- create a fresh `.venv` for this repo; do not copy `.venv` folders from other projects
- use `.tmp/` as the single repo-local temporary directory when a repo-local temp path is needed
- use `.cache/` as the single repo-local cache directory when a repo-local cache path is needed
- treat parquet as the canonical artifact format where practical
- keep CSV support as a compatibility path, not the primary research artifact format
- do not hardcode API keys or credentials
- read secrets from environment variables only
- data-source credentials and proprietary access tokens must never be committed

## Engineering Rules

- Use Python only unless docs explicitly authorize otherwise
- Prefer production modules and CLI entrypoints over notebook-only logic
- Keep raw data immutable
- Preserve deterministic output paths
- Save intermediate artifacts where the pipeline expects them
- Add logging
- Add type hints where practical
- Add or update tests for modified logic
- Prefer modular, column-selective, memory-aware implementations
- Keep data ingestion, feature engineering, portfolio logic, and modeling clearly separated
- Do not silently change canonical output schemas or directory contracts
- Do not silently change benchmark definitions, rebalance rules, or trade-execution assumptions
- Do not silently change the universe definition

Preferred libraries include:

- `pandas`
- `numpy`
- `pyarrow`
- `scikit-learn`
- `statsmodels`
- `matplotlib`
- `pyyaml`
- `pathlib`

Additional libraries may be added only when justified by the module requirements.

## Main Entrypoints To Respect

Data and orchestration:

- `src.data.*`
- `src.features.*`
- `src.signals.*`
- `src.portfolio.*`
- `src.backtest.*`
- `src.models.*`
- `src.evaluation.*`
- `src.reporting.*`

Suggested CLI entrypoints to create and preserve:

- `src.run_data_ingestion`
- `src.run_panel_assembly`
- `src.run_feature_generation`
- `src.run_signal_generation`
- `src.run_backtest`
- `src.run_modeling_baselines`
- `src.run_logistic_regression`
- `src.run_random_forest`
- `src.run_evaluation_report`

If actual entrypoint names change, update docs and progress files together.

## Documentation Rules

Keep these documents aligned:

- `README.md` = landing page and canonical high-level repo definition
- `docs/00_project_scope.md` = scope, goals, initial universe, success criteria, and non-goals
- `docs/01_research_questions.md` = research questions and hypotheses
- `docs/02_system_architecture.md` = module boundaries, data flow, and artifact flow
- `docs/03_data_schema.md` = canonical tables, fields, keys, and artifact contracts
- `docs/04_feature_spec.md` = feature definitions, formulas, lag rules, and dependencies
- `docs/05_backtest_spec.md` = rebalance rules, ranking rules, costs, benchmark logic, and outputs
- `docs/06_modeling_spec.md` = labels, candidate models, and validation rules
- `docs/07_evaluation_spec.md` = evaluation metrics, regime splits, and report structure
- `docs/08_experiment_tracking.md` = experiment logging conventions
- `docs/09_risk_and_bias_controls.md` = methodological safeguards and warnings
- `docs/10_development_roadmap.md` = milestone order and implementation phases
- `progress/current_status.md` = canonical rolling handoff and current state summary

Documentation expectations:

- update `README.md` when repo architecture or canonical usage changes
- update the relevant `docs/` file when module behavior, assumptions, or outputs change
- update `progress/current_status.md` and the relevant module progress file after meaningful work
- add docstrings to public functions and CLI entrypoints where practical

## State And Handoff Maintenance

Treat `progress/current_status.md` as the canonical rolling handoff file.

Rules:

- prefer updating existing docs over creating redundant status files
- do not create extra tracking docs if the existing progress files can carry the state
- after any meaningful code, test, documentation, output, or workflow change, update the relevant progress file before ending the task unless explicitly told not to
- keep handoff notes concise, factual, and honest
- distinguish clearly between:
  - implemented
  - test-verified
  - manually verified
- do not invent benchmark status, manual verification, or out-of-sample claims

When relevant, refresh these handoff sections:

- Current Milestone
- What Is Completed
- Testing Status
- Manual Verification Status
- Immediate Next Step
- Known Risks / Open Issues
- Current Output Structure

For any new module, CLI, artifact, or workflow stage, record:

- what was added
- where it lives
- how to run it
- what was verified manually
- what was verified only by tests

## Task Completion Rule

A task is not complete until the relevant combination of:

- code
- tests
- docs
- progress files

has been updated consistently.

## Git Operations

Before any push, run:

- `git remote -v`
- `git branch --show-current`
- `git status`

Git rules:

- default branch is `main`
- do not force-push `main` unless explicitly requested
- if push fails, capture and report the exact error text
- do not guess auth or permission causes; verify by rerunning and reporting the actual message

## Market-Data And Research Rules

Market and fundamentals ingestion is a required pipeline stage.

Rules:

- preserve raw downloads or extracts as immutable inputs
- standardize all downstream artifacts through documented schemas
- log date coverage, ticker coverage, and field coverage for each major dataset
- support resumable data builds where practical
- document whether each field is point-in-time safe or potentially revised historically
- do not bypass the documented raw-to-panel contract without updating docs and progress notes

Research-method rules:

- deterministic baselines must be implemented before ML models
- no strategy claim may be presented without a note on likely bias sources and current controls
- no feature may use future information relative to the rebalance date
- no random train/test split is allowed for time-dependent modeling
- no portfolio comparison is complete without explicit benchmark and turnover context

## Output-Structure Rules

Respect the stage-specific output structure:

- `outputs/data/` = canonical machine-readable processed datasets
- `outputs/features/` = feature panels and QC summaries
- `outputs/backtests/` = holdings, trades, return series, and summary metrics
- `outputs/models/` = model predictions, metadata, and interpretability outputs
- `outputs/reports/` = human-readable reports, registries, and summary tables
- `outputs/paper_trading/` = reserved later-stage forward-evaluation artifacts

Do not collapse these stage-specific roots into a single mixed output directory without a deliberate repo-wide documentation update.
