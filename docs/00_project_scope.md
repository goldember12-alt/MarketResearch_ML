# 00 Project Scope

## Project Definition

Build and maintain a reproducible end-to-end market research and portfolio simulation framework for rules-based and later ML-assisted equity selection. This repo is a research and evaluation system, not a notebook-only sandbox.

The canonical analytic unit is:

- one row per ticker per month

The canonical early-stage task is:

- rank stocks cross-sectionally each month
- hold the top `N` names subject to explicit portfolio constraints
- compare performance against explicit benchmarks

## Initial Research Preset

The initial preset is the operating default for the scaffold and all documentation unless a later doc update changes it.

- Universe name: `initial_large_cap_tech_plus_comparison`
- Frequency: monthly
- Start date target: `2015-01-01`
- Tech cohort: `AAPL`, `MSFT`, `NVDA`, `AMZN`, `META`, `GOOGL`, `AVGO`, `ORCL`, `CRM`, `ADBE`
- Comparison cohort: `JPM`, `JNJ`, `PG`, `UNH`, `HD`, `WMT`, `XOM`, `CVX`, `COST`, `KO`
- Explicit benchmarks: `SPY`, `QQQ`
- Derived benchmark: `equal_weight_universe`
- Portfolio baseline: top `10`, equal weight, monthly rebalance, `10` bps transaction costs

## Phase-1 Objective

The first implementation objective is not full ML modeling. It is a deterministic, documented, and reproducible monthly research pipeline that can:

- ingest and standardize market and fundamentals inputs
- assemble `outputs/data/monthly_panel.parquet`
- generate leakage-safe features
- create deterministic ranking signals
- run a benchmark-aware monthly backtest
- write evaluation-ready output artifacts

The next adjacent objective after the currently implemented baseline is:

- maintain the implemented remote raw-data acquisition layer that populates the local raw-data contract from Alpha Vantage and SEC sources without changing downstream stage boundaries

## Success Criteria For The Current Build Phase

The scaffold phase is successful when:

- the repo structure matches the documented pipeline stages
- config files define the initial universe, benchmarks, outputs, and backtest defaults
- docs state the same contracts as the code scaffold
- CLI entrypoints are runnable and point to the next concrete implementation step
- progress files distinguish scaffolded work from implemented logic

## Explicit Non-Goals For This Phase

- no claim of completed benchmark-quality results
- no claim of out-of-sample performance
- no live trading or paper-trading execution engine
- no deep learning models
- no undocumented manual data patches
- no silent schema or methodology drift
- no direct dependency of downstream research stages on live vendor calls at runtime

## Known Scope Boundaries

- Fundamentals may not be point-in-time safe initially; that risk must be documented until a point-in-time source is available.
- The initial universe is a seeded research preset, not a final production universe definition.
- The first implementation milestone prioritizes data contracts and deterministic baselines before any ML comparison.
- The implemented remote acquisition layer preserves the existing raw-file-first contract by writing immutable raw extracts locally before ingestion begins.
