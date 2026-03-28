# 02 System Architecture

## Architectural Goal

The system is organized as a stage-based research pipeline with explicit inputs, outputs, and artifact contracts. The implemented boundary now covers raw-to-processed data ingestion, canonical monthly panel assembly, leakage-safe monthly feature generation, deterministic cross-sectional signal generation, deterministic monthly backtesting, and baseline evaluation reporting.

## Canonical Stage Flow

1. `src.data`
   Ingest local raw market, benchmark, and fundamentals files.
2. `src.data`
   Standardize those inputs to processed monthly datasets.
3. `src.data`
   Assemble the canonical one-row-per-ticker-per-month panel.
4. `src.features`
   Generate documented leakage-safe monthly features from the panel.
5. `src.signals`
   Convert the feature panel into deterministic cross-sectional rankings.
6. `src.backtest`
   Map signal selections to holdings, trades, realized returns, and benchmark-relative metrics.
7. `src.evaluation`
   Build a benchmark-aware, caveat-aware summary from the backtest outputs.
8. `src.reporting`
   Write the human-readable report and append the experiment registry.
9. `src.models`
   Add chronology-safe baselines only after deterministic baselines exist.

## Implemented Raw-To-Report Flow

### Raw Input Contract

The current workflow is local-file-first and reads immutable raw tabular files from:

- `data/raw/market/`
- `data/raw/benchmarks/`
- `data/raw/fundamentals/`

Supported formats:

- CSV
- Parquet

Deterministic sample raw files are included in the repo so the implemented stages are runnable without external connectors.

### Data Stage

`src.run_data_ingestion` performs:

1. load shared project config
2. standardize market prices to monthly month-end `ticker`-`date` rows
3. compute `monthly_return` from standardized `adjusted_close`
4. standardize explicit benchmarks `SPY` and `QQQ`
5. derive `equal_weight_universe`
6. standardize fundamentals, apply a conservative effective lag, and map them onto the monthly calendar
7. write processed Parquet artifacts and dataset QC summaries

### Panel Stage

`src.run_panel_assembly` performs:

1. read the processed data artifacts
2. build the canonical monthly calendar
3. create the full ticker-month grid for the configured universe
4. left join prices and lagged fundamentals by `ticker` and `date`
5. align the configured primary benchmark return by `date`
6. validate one row per ticker per month
7. write the monthly panel plus panel QC and coverage summaries

### Feature Stage

`src.run_feature_generation` performs:

1. read `outputs/data/monthly_panel.parquet`
2. validate one row per ticker per month
3. generate lagged price-based features using only information available through `t-1`
4. shift fundamentals-derived metrics by one additional month before exposing them as predictive features
5. preserve missingness instead of numeric imputation
6. write the feature panel, feature QC summary, and feature missingness summary

### Signal Stage

`src.run_signal_generation` performs:

1. read `outputs/features/feature_panel.parquet`
2. validate one row per ticker per month
3. convert configured features into within-month percentile scores with explicit directionality
4. average available feature scores using configured weights
5. require a minimum number of non-missing feature values before a row receives a composite score
6. rank names deterministically within each month using documented tie-breakers
7. write the ranking table plus signal QC and selection summary artifacts

### Backtest Stage

`src.run_backtest` performs:

1. read `signal_rankings`, `monthly_panel`, and `benchmarks_monthly`
2. validate duplicate keys and deterministic monthly joins
3. construct top-N holdings snapshots by rebalance month
4. map month-end decision date `t` to realized return date `t+1`
5. compare consecutive snapshots to generate trade and turnover records
6. apply next-period realized security returns, then subtract configured turnover-based costs
7. align explicit benchmark returns to the same realized months
8. write holdings, trades, return series, period comparisons, risk metrics, and a JSON summary

### Evaluation And Reporting Stage

`src.run_evaluation_report` performs:

1. read the backtest summary, return series, per-period table, and risk metrics table
2. combine them with current signal and backtest config context
3. build a benchmark-aware exploratory evaluation summary with required caveats
4. render `outputs/reports/strategy_report.md`
5. append one record to `outputs/reports/experiment_registry.jsonl`

## Implemented Module Responsibilities

| Module | Responsibility |
| --- | --- |
| `src.data.*` | ingestion, standardization, panel assembly, QC |
| `src.features.config` | feature-stage config loading and logging setup |
| `src.features.engineering` | lagged and rolling feature calculations |
| `src.features.qc` | feature QC and missingness outputs |
| `src.signals.config` | signal-stage config loading and logging setup |
| `src.signals.scoring` | cross-sectional feature scoring, composite score construction, deterministic ranking |
| `src.signals.qc` | signal QC and selection summaries |
| `src.backtest.config` | backtest-stage config loading and logging setup |
| `src.backtest.holdings` | holdings construction and rebalance summaries |
| `src.backtest.trades` | trade logs and turnover summaries |
| `src.backtest.returns` | next-period return alignment and benchmark joins |
| `src.backtest.metrics` | cumulative returns and risk metric calculations |
| `src.backtest.qc` | backtest validation and QC summaries |
| `src.evaluation.summary` | structured benchmark-aware evaluation summaries |
| `src.reporting.markdown` | strategy report rendering |
| `src.reporting.registry` | experiment-record creation and JSONL append |

## Design Rules In Force

- Every implemented stage reads from documented upstream artifacts, not notebook state.
- All joins and rank-order operations are deterministic and keyed explicitly.
- The panel, feature panel, and signal rankings preserve the full ticker-month grid so missingness remains visible.
- Predictive features and downstream signals use only information available through the prior month.
- Backtest holdings formed at month-end `t` only earn returns recorded at month-end `t+1`.
- Transaction costs are explicit and config-driven.
- Reports must include benchmark context and bias caveats.
- Numeric feature imputation is intentionally not implemented.
- Point-in-time-safe fundamentals are not claimed; the current lag rule is a bias control, not a complete solution.

## Immediate Next Boundary

The next critical path is `src.models`:

- add chronology-safe deterministic and ML baseline runners
- compare models against the documented deterministic signal baseline
- preserve walk-forward, leakage-safe evaluation
