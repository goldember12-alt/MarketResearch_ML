# 02 System Architecture

## Architectural Goal

The system is organized as a stage-based research pipeline with explicit inputs, outputs, and artifact contracts. The implemented boundary in this milestone is the raw-to-processed data layer plus canonical monthly panel assembly.

## Canonical Stage Flow

1. `src.data`
   Ingest local raw market, benchmark, and fundamentals files.
2. `src.data`
   Standardize those inputs to monthly processed artifacts.
3. `src.data`
   Assemble the canonical one-row-per-ticker-per-month panel.
4. `src.features`
   Build leakage-safe features with documented lookbacks and lag rules.
5. `src.signals`
   Convert features into deterministic rankings or model-ready scores.
6. `src.portfolio`
   Map scores to constrained holdings weights.
7. `src.backtest`
   Simulate monthly rebalances and benchmark-relative performance.
8. `src.evaluation`
   Compute metrics, diagnostics, and period analysis.
9. `src.reporting`
   Write human-readable reports and append experiment logs.
10. `src.models`
    Add later-stage chronology-safe baselines after deterministic baselines exist.

## Implemented Raw-To-Processed Flow

### Raw Input Contract

The current pipeline is local-file-first and reads raw tabular files from:

- `data/raw/market/`
- `data/raw/benchmarks/`
- `data/raw/fundamentals/`

Supported formats:

- CSV
- Parquet

Raw files are treated as immutable inputs. The repo currently includes deterministic local sample raw files so the implemented runners can be executed without live vendor connectors.

### Ingestion Runner

`src.run_data_ingestion` performs:

1. load shared project config from `config/universe.yaml`, `config/data.yaml`, `config/paths.yaml`, and `config/logging.yaml`
2. standardize market data to monthly `ticker`-`date` rows with month-end adjusted closes and month-over-month returns
3. standardize explicit benchmarks `SPY` and `QQQ`
4. derive `equal_weight_universe` from the cross-sectional average of constituent monthly returns
5. standardize fundamentals observations, apply the configured effective lag, and map them onto the monthly calendar
6. write processed Parquet artifacts and dataset QC JSON summaries

### Panel Runner

`src.run_panel_assembly` performs:

1. read `prices_monthly`, `fundamentals_monthly`, and `benchmarks_monthly`
2. build the canonical monthly calendar from security-price and primary-benchmark dates
3. create the full ticker-month grid for the configured universe
4. left join prices and lagged fundamentals by `ticker` and `date`
5. align the configured primary benchmark return by `date`
6. validate one row per ticker per month
7. write the panel plus panel-level QC and coverage summaries

## Implemented `src.data` Module Responsibilities

| Module | Responsibility |
| --- | --- |
| `src.data.config` | data-stage config loading and logging setup |
| `src.data.universe` | universe and benchmark validation helpers |
| `src.data.io` | raw file discovery plus Parquet/JSON/CSV persistence |
| `src.data.standardize` | column normalization, date normalization, return computation, duplicate-key checks |
| `src.data.market_data` | raw market-price ingestion and monthly standardization |
| `src.data.benchmarks` | explicit benchmark ingestion and equal-weight benchmark construction |
| `src.data.fundamentals_data` | fundamentals standardization and lagged monthly mapping |
| `src.data.panel_assembly` | deterministic monthly panel joins and grid validation |
| `src.data.qc` | QC summaries and ticker/date coverage tables |

## Config And Artifact Control

Implemented data-stage config files:

- `config/universe.yaml`
- `config/data.yaml`
- `config/paths.yaml`
- `config/logging.yaml`

The processed data artifact contract lives in `config/paths.yaml` and is described in `docs/03_data_schema.md`.

## Design Rules In Force

- Every implemented stage reads from documented upstream artifacts instead of notebook state.
- All joins are deterministic and keyed explicitly.
- Monthly dates use a documented calendar month-end convention.
- The panel is built on a full ticker-month grid so missingness is visible rather than silently dropped.
- Point-in-time-safe fundamentals are not claimed; the current conservative lag rule is documented as a bias control, not a complete solution.
- Feature engineering, signal generation, backtesting, and modeling remain downstream work and were not implemented in this milestone.

## Immediate Next Boundary

The next critical path is `src.features`:

- derive leakage-safe features from `outputs/data/monthly_panel.parquet`
- document lookback windows and lag rules
- write feature QC and missingness artifacts
