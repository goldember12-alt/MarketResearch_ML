# 02 System Architecture

## Architectural Goal

The system is organized as a stage-based research pipeline with explicit inputs, outputs, and artifact contracts. The implemented boundary now covers raw-to-processed data ingestion, canonical monthly panel assembly, and leakage-safe monthly feature generation.

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
   Convert features into deterministic cross-sectional rankings.
6. `src.portfolio`
   Map rankings to constrained holdings weights.
7. `src.backtest`
   Simulate rebalances and benchmark-relative performance.
8. `src.evaluation`
   Compute metrics, diagnostics, and period analysis.
9. `src.reporting`
   Write reports and experiment logs.
10. `src.models`
    Add chronology-safe baselines only after deterministic baselines exist.

## Implemented Raw-To-Feature Flow

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

1. load shared project config from `config/universe.yaml`, `config/data.yaml`, `config/paths.yaml`, and `config/logging.yaml`
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

## Implemented Module Responsibilities

| Module | Responsibility |
| --- | --- |
| `src.data.config` | data-stage config loading and logging setup |
| `src.data.market_data` | monthly security-price standardization |
| `src.data.benchmarks` | explicit benchmark ingestion and equal-weight benchmark construction |
| `src.data.fundamentals_data` | fundamentals standardization and lagged monthly mapping |
| `src.data.panel_assembly` | canonical monthly panel joins and validation |
| `src.data.qc` | data-stage QC and coverage outputs |
| `src.features.config` | feature-stage config loading and logging setup |
| `src.features.engineering` | lagged and rolling feature calculations |
| `src.features.qc` | feature QC and missingness outputs |

## Design Rules In Force

- Every implemented stage reads from documented upstream artifacts, not notebook state.
- All joins are deterministic and keyed explicitly.
- The panel and feature panel preserve the full ticker-month grid so missingness is visible.
- Predictive features use only information available through the prior month.
- Numeric feature imputation is intentionally not implemented yet because the current contract prefers visible missingness over silent masking.
- Point-in-time-safe fundamentals are not claimed; the current lag rule is a bias control, not a complete solution.

## Immediate Next Boundary

The next critical path is `src.signals`:

- convert the feature panel into deterministic cross-sectional ranking signals
- document ranking logic and tie-breaking rules
- keep portfolio and backtest logic out of that stage
