# 03 Data Schema

## Canonical Frequency And Grain

- Frequency: monthly
- Decision grain: one row per ticker per month
- Date convention: normalized month-end date for the observation period
- Join keys: deterministic keys only

The monthly panel is the canonical research table for both deterministic and later ML workflows.

## Canonical Artifacts

### `outputs/data/prices_monthly.parquet`

Required columns:

| Column | Type | Notes |
| --- | --- | --- |
| `ticker` | string | security identifier used across the repo |
| `date` | date/timestamp | month-end observation date |
| `adjusted_close` | float | split/dividend adjusted close |
| `monthly_return` | float | total return for the month |
| `volume` | float or int | optional if reliably available |

Primary key:

- `ticker`, `date`

### `outputs/data/fundamentals_monthly.parquet`

Required columns:

| Column | Type | Notes |
| --- | --- | --- |
| `ticker` | string | join key |
| `date` | date/timestamp | aligned monthly observation date |
| `sector` | string | sector classification used in analysis |
| `industry` | string | industry classification |
| `market_cap` | float | market capitalization at or lagged to the decision date |
| valuation metrics | float columns | for example `pe_ratio`, `price_to_sales`, `ev_to_ebitda` |
| profitability metrics | float columns | for example `gross_margin`, `operating_margin`, `roe`, `roa` |
| growth metrics | float columns | for example `revenue_growth`, `eps_growth` |
| balance-sheet metrics | float columns | for example `debt_to_equity`, `current_ratio` |
| revision metrics | float columns | optional and only if leakage-safe |

Primary key:

- `ticker`, `date`

Point-in-time note:

- If point-in-time fundamentals are unavailable, this table must carry a documented revised-history caveat in reports and progress files.

### `outputs/data/benchmarks_monthly.parquet`

Required columns:

| Column | Type | Notes |
| --- | --- | --- |
| `benchmark_ticker` | string | `SPY`, `QQQ`, or a derived benchmark id |
| `date` | date/timestamp | month-end observation date |
| `adjusted_close` | float | benchmark close series |
| `monthly_return` | float | benchmark total return |

Primary key:

- `benchmark_ticker`, `date`

### `outputs/data/monthly_panel.parquet`

Required minimum columns:

| Column | Type | Notes |
| --- | --- | --- |
| `ticker` | string | analytic unit key |
| `date` | date/timestamp | monthly observation key |
| `adjusted_close` | float | inherited from prices table |
| `monthly_return` | float | security total return |
| `benchmark_return` | float | benchmark return used for relative evaluation |
| `sector` | string | classification for evaluation and optional constraints |
| `industry` | string | classification for analysis |
| `market_cap` | float | current or lagged market cap |
| valuation metrics | float columns | lagged if needed to avoid leakage |
| profitability metrics | float columns | lagged if needed to avoid leakage |
| growth metrics | float columns | lagged if needed to avoid leakage |

Primary key:

- `ticker`, `date`

## Downstream Artifact Contract

The monthly panel feeds:

- `outputs/features/feature_panel.parquet`
- model label construction
- deterministic ranking signals
- benchmark-relative evaluation

The scaffold also reserves these later-stage artifacts:

- `outputs/backtests/holdings_history.parquet`
- `outputs/backtests/trade_log.parquet`
- `outputs/models/train_predictions.parquet`
- `outputs/reports/strategy_report.md`

## Assembly Rules

- All joins must be explicit on date-aligned keys.
- Missingness must be logged consistently, not handled ad hoc in notebooks.
- Benchmark alignment must be preserved at the monthly decision frequency.
- Schema changes require simultaneous doc, test, and progress updates.
