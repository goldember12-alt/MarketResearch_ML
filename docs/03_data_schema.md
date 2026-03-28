# 03 Data Schema

## Canonical Frequency And Grain

- Frequency: monthly
- Decision grain: one row per ticker per month
- Date convention: normalized calendar month-end
- Deterministic keys only

The canonical monthly panel is the shared upstream table for feature generation, later deterministic signals, and later chronology-safe modeling workflows.

## Raw Data Contract

Local raw inputs are read from:

- `data/raw/market/`
- `data/raw/benchmarks/`
- `data/raw/fundamentals/`

Supported raw formats:

- CSV
- Parquet

Raw files are immutable inputs. The current repo includes deterministic local sample raw files for pipeline verification.

## Standardization Rules

### Monthly Date Convention

- All processed monthly dates are normalized to calendar month-end.
- If raw market or benchmark data are daily, the last available observation within the month is used.

### `adjusted_close`

- The selection priority lives in `config/data.yaml`.
- Current priority: `adjusted_close`, `adj_close`, `adjclose`, then `close`.

### `monthly_return`

- Formula: `adjusted_close_t / adjusted_close_t-1 - 1`
- Computed separately within each identifier.
- The first available month per identifier is `NaN`.

### `benchmark_return`

- Benchmarks use the same month-over-month formula.
- `benchmarks_monthly.parquet` stores `SPY`, `QQQ`, and `equal_weight_universe`.
- `monthly_panel.parquet` currently aligns the configured primary benchmark `SPY` by `date` and stores it as `benchmark_return`.

### Equal-Weight Universe Benchmark

- Identifier: `equal_weight_universe`
- Monthly return: simple arithmetic average of available universe constituent `monthly_return` values
- Adjusted close: chained synthetic series starting from `100.0`

### Fundamentals Mapping Rule

- Raw fundamentals are normalized to `fundamentals_source_date`
- A conservative `2`-month effective lag is applied
- Monthly fundamentals are mapped by ticker using backward as-of logic from `fundamentals_effective_date`
- Configured max staleness is `12` months; older mapped observations are nulled out

Important caveat:

- This lag rule reduces obvious look-ahead risk, but it is not a true point-in-time solution. Revised-history bias remains possible.

## Canonical Artifacts

### `outputs/data/prices_monthly.parquet`

Primary key:

- `ticker`, `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| `ticker` | string | canonical security identifier |
| `date` | timestamp | calendar month-end |
| `adjusted_close` | float | standardized adjusted close |
| `volume` | float or int | last observed volume in the month when available |
| `monthly_return` | float | month-over-month return |

### `outputs/data/benchmarks_monthly.parquet`

Primary key:

- `benchmark_ticker`, `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| `benchmark_ticker` | string | `SPY`, `QQQ`, or `equal_weight_universe` |
| `date` | timestamp | calendar month-end |
| `adjusted_close` | float | explicit or derived benchmark close series |
| `volume` | float or int | available for explicit benchmarks |
| `monthly_return` | float | month-over-month benchmark return |

### `outputs/data/fundamentals_monthly.parquet`

Primary key:

- `ticker`, `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| `ticker` | string | canonical security identifier |
| `date` | timestamp | monthly mapped observation date |
| `fundamentals_source_date` | timestamp | normalized source month |
| `fundamentals_effective_date` | timestamp | source month plus configured lag |
| `sector` | string | classification field |
| `industry` | string | classification field |
| `market_cap` | float | mapped market capitalization |
| `pe_ratio` | float | valuation metric |
| `price_to_sales` | float | valuation metric |
| `price_to_book` | float | valuation metric |
| `ev_to_ebitda` | float | valuation metric |
| `gross_margin` | float | profitability metric |
| `operating_margin` | float | profitability metric |
| `roe` | float | profitability metric |
| `roa` | float | profitability metric |
| `revenue_growth` | float | growth metric |
| `eps_growth` | float | growth metric |
| `debt_to_equity` | float | balance-sheet metric |
| `current_ratio` | float | balance-sheet metric |

### `outputs/data/monthly_panel.parquet`

Primary key:

- `ticker`, `date`

Implemented columns:

| Column | Type | Notes |
| --- | --- | --- |
| `ticker` | string | analytic unit key |
| `date` | timestamp | monthly observation key |
| `adjusted_close` | float | inherited from prices table |
| `monthly_return` | float | security month-over-month return |
| `benchmark_ticker` | string | current primary benchmark id |
| `benchmark_return` | float | aligned primary benchmark return |
| `sector` | string | classification field |
| `industry` | string | classification field |
| `market_cap` | float | lagged mapped market cap |
| `pe_ratio` | float | valuation metric |
| `price_to_sales` | float | valuation metric |
| `price_to_book` | float | valuation metric |
| `ev_to_ebitda` | float | valuation metric |
| `gross_margin` | float | profitability metric |
| `operating_margin` | float | profitability metric |
| `roe` | float | profitability metric |
| `roa` | float | profitability metric |
| `revenue_growth` | float | growth metric |
| `eps_growth` | float | growth metric |
| `debt_to_equity` | float | balance-sheet metric |
| `current_ratio` | float | balance-sheet metric |
| `fundamentals_source_date` | timestamp | source mapping metadata |
| `fundamentals_effective_date` | timestamp | effective-date mapping metadata |
| `volume` | float or int | inherited monthly volume |

### `outputs/features/feature_panel.parquet`

Primary key:

- `ticker`, `date`

Metadata columns:

| Column | Type | Notes |
| --- | --- | --- |
| `ticker` | string | analytic unit key |
| `date` | timestamp | feature observation month |
| `benchmark_ticker` | string | benchmark id used for benchmark-relative features |
| `sector` | string | metadata only, not a predictive return target |
| `industry` | string | metadata only |
| `fundamentals_source_date` | timestamp | mapped fundamentals source month |
| `fundamentals_effective_date` | timestamp | mapped fundamentals effective month |

Implemented feature columns:

| Column | Type | Notes |
| --- | --- | --- |
| `ret_1m_lag1` | float | prior month return |
| `mom_3m` | float | compounded return over prior 3 months excluding current month |
| `mom_6m` | float | compounded return over prior 6 months excluding current month |
| `mom_12m` | float | compounded return over prior 12 months excluding current month |
| `drawdown_12m` | float | prior close divided by trailing 12-month high minus 1 |
| `vol_12m` | float | rolling 12-month standard deviation of lagged monthly returns |
| `beta_12m_spy` | float | rolling 12-month beta versus lagged `SPY` returns |
| `adjusted_close_lag1` | float | prior month adjusted close |
| `benchmark_return_lag1` | float | prior month primary benchmark return |
| `market_cap_lag1` | float | prior month mapped market cap |
| `pe_ratio_lag1` | float | prior month valuation ratio |
| `price_to_sales_lag1` | float | prior month valuation ratio |
| `price_to_book_lag1` | float | prior month valuation ratio |
| `ev_to_ebitda_lag1` | float | prior month valuation ratio |
| `gross_margin_lag1` | float | prior month profitability metric |
| `operating_margin_lag1` | float | prior month profitability metric |
| `roe_lag1` | float | prior month profitability metric |
| `roa_lag1` | float | prior month profitability metric |
| `revenue_growth_lag1` | float | prior month growth metric |
| `eps_growth_lag1` | float | prior month growth metric |
| `debt_to_equity_lag1` | float | prior month balance-sheet metric |
| `current_ratio_lag1` | float | prior month balance-sheet metric |

Feature rules:

- Predictive features use only information available through `t-1`
- Fundamental metrics are shifted one additional month before inclusion in the feature panel
- Numeric missingness is preserved rather than imputed

## QC And Coverage Artifacts

### Data-Stage QC

- `outputs/data/prices_qc_summary.json`
- `outputs/data/fundamentals_qc_summary.json`
- `outputs/data/benchmarks_qc_summary.json`
- `outputs/data/panel_qc_summary.json`
- `outputs/data/ticker_coverage_summary.csv`
- `outputs/data/date_coverage_summary.csv`

### Feature-Stage QC

- `outputs/features/feature_qc_summary.json`
- `outputs/features/feature_missingness_summary.csv`

Feature QC currently includes:

- row count
- feature column count
- feature group membership
- duplicate key count
- min and max date
- total missing feature-cell count
- missing feature cells by date

Feature missingness CSV currently includes:

- feature name
- feature group
- missing count
- non-missing count
- missing ratio
- first valid date

## Change Control

- All schema changes require synchronized updates to code, tests, docs, and progress files.
- Do not treat lagged fundamentals in the feature panel as proof of point-in-time safety.
