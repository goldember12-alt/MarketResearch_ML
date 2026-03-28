# 02 System Architecture

## Architectural Goal

The system is organized as a stage-based research pipeline with explicit inputs, outputs, and artifact contracts. The repo should support repeatable runs that can be re-executed from config and inspected stage by stage.

## Canonical Stage Flow

1. `src.data`
   Standardize raw prices, fundamentals, and benchmark inputs.
2. `src.data`
   Assemble the monthly panel keyed by `ticker` and `date`.
3. `src.features`
   Build leakage-safe features with documented lookbacks and lag rules.
4. `src.signals`
   Convert features into deterministic rankings or model-ready scores.
5. `src.portfolio`
   Map scores to constrained holdings weights.
6. `src.backtest`
   Simulate monthly rebalances, turnover, and benchmark-relative returns.
7. `src.evaluation`
   Compute metrics, period splits, and diagnostics.
8. `src.reporting`
   Write human-readable reports and append the experiment registry.
9. `src.models`
   Later-stage modeling baselines using chronology-safe data splits.

## Current Code Scaffold

- `src/utils/config.py`
  Loads the shared project contract from YAML and resolves canonical paths.
- `src/utils/stage_runner.py`
  Gives the CLI entrypoints one shared scaffold behavior.
- `src/run_*.py`
  Minimal executable runners for each stage. They do not implement research logic yet.

## Module Responsibilities

| Module | Responsibility | Canonical Outputs |
| --- | --- | --- |
| `src.data` | ingestion, standardization, panel assembly, QC | `outputs/data/*.parquet` |
| `src.features` | lagged and fundamentals-based feature generation, missingness summaries | `outputs/features/*` |
| `src.signals` | deterministic score construction and ranking tables | intermediate ranking artifacts to be formalized |
| `src.portfolio` | top-N selection, weights, turnover inputs | holdings tables |
| `src.backtest` | return series, trade log, summary metrics | `outputs/backtests/*` |
| `src.models` | labels, walk-forward data prep, deterministic and ML baselines | `outputs/models/*` |
| `src.evaluation` | metric computation and period diagnostics | report-ready tables |
| `src.reporting` | markdown reports and experiment registry writes | `outputs/reports/*` |

## Config And Artifact Control

The current scaffold treats these config files as canonical:

- `config/universe.yaml`
- `config/backtest.yaml`
- `config/features.yaml`
- `config/model.yaml`
- `config/paths.yaml`
- `config/logging.yaml`

The artifact contract lives in `config/paths.yaml` and is described for humans in `docs/03_data_schema.md`.

## Design Rules

- Every stage must read from documented upstream artifacts rather than implicit notebook state.
- All joins must be deterministic and keyed explicitly.
- Features and labels must reflect only information available at the decision date.
- Output directories must remain stage-specific and not be collapsed into a mixed artifact root.
- Docs, tests, and progress files must be updated when contracts change.

## Immediate Implementation Boundary

The scaffold is complete enough to support the next coding task:

- build `src.data` ingestion contracts
- validate monthly schemas
- assemble `outputs/data/monthly_panel.parquet`

That is the critical path before meaningful feature engineering or backtesting work.
