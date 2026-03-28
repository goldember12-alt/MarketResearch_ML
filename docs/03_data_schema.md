# 03 Data Schema

## Canonical Frequency And Grain

- Frequency: monthly
- Decision grain: one row per ticker per month
- Date convention: normalized calendar month-end
- Deterministic keys only

The canonical monthly panel is the research table that later feeds feature generation, deterministic baselines, and chronology-safe modeling workflows.

## Raw Data Contract

Local raw inputs are read from:

- `data/raw/market/`
- `data/raw/benchmarks/`
- `data/raw/fundamentals/`

Supported raw formats:

- CSV
- Parquet

Raw files are immutable inputs. The current repo includes deterministic local sample raw files for pipeline verification. These are implementation fixtures, not a claim of production vendor coverage.

## Standardization Rules

### Monthly Date Convention

- All processed monthly dates are normalized to calendar month-end.
- If raw market or benchmark data are daily, the pipeline keeps the last available observation within each month for each identifier.
- If raw data are already monthly, the same month-end normalization is still applied.

### `adjusted_close`

- The configured selection priority lives in `config/data.yaml`.
- Current priority: `adjusted_close`, `adj_close`, `adjclose`, then `close`.
- The selected column is standardized to the canonical processed field `adjusted_close`.

### `monthly_return`

- Formula: `adjusted_close_t / adjusted_close_t-1 - 1`
- Computed separately within each `ticker`.
- The first available month per identifier is `NaN` because no prior monthly close exists.

### `benchmark_return`

- Benchmarks use the same month-over-month return formula as securities.
- `benchmarks_monthly.parquet` stores monthly returns for `SPY`, `QQQ`, and `equal_weight_universe`.
- `monthly_panel.parquet` currently aligns the configured primary benchmark `SPY` by `date` and stores that aligned value as `benchmark_return`.

### Equal-Weight Universe Benchmark

- Identifier: `equal_weight_universe`
- Monthly return: simple arithmetic average of available universe constituent `monthly_return` values on each month-end
- Adjusted close: chained synthetic series starting from `100.0`

Current caution:

- This is a convenient baseline benchmark, not a fully investable implementation with turnover, costs, or constituent-entry rules.

### Fundamentals Mapping Rule

- Raw fundamentals observations are normalized to a monthly `fundamentals_source_date`.
- A conservative `2`-month effective lag is applied:
  `fundamentals_effective_date = month_end(fundamentals_source_date) + 2 month-ends`
- The monthly fundamentals table is built by ticker with backward as-of mapping from the effective date onto the monthly panel calendar.
- Configured max staleness is `12` months. If the latest available fundamentals observation is older than that threshold, the mapped fundamentals fields are nulled out.

Important caveat:

- This lag rule reduces obvious look-ahead risk, but it is not a true point-in-time solution. Revised-history bias remains possible until a point-in-time fundamentals source is added.

## Canonical Artifacts

### `outputs/data/prices_monthly.parquet`

Primary key:

- `ticker`, `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| `ticker` | string | canonical security identifier |
| `date` | timestamp | calendar month-end observation date |
| `adjusted_close` | float | standardized adjusted close |
| `volume` | float or int | last observed volume in the month when available |
| `monthly_return` | float | month-over-month total return from `adjusted_close` |

### `outputs/data/benchmarks_monthly.parquet`

Primary key:

- `benchmark_ticker`, `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| `benchmark_ticker` | string | `SPY`, `QQQ`, or `equal_weight_universe` |
| `date` | timestamp | calendar month-end observation date |
| `adjusted_close` | float | explicit or derived benchmark close series |
| `volume` | float or int | available for explicit benchmarks, null for derived benchmark |
| `monthly_return` | float | benchmark month-over-month return |

### `outputs/data/fundamentals_monthly.parquet`

Primary key:

- `ticker`, `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| `ticker` | string | canonical security identifier |
| `date` | timestamp | monthly mapped observation date |
| `fundamentals_source_date` | timestamp | normalized source observation month |
| `fundamentals_effective_date` | timestamp | source date plus configured lag |
| `sector` | string | classification field |
| `industry` | string | classification field |
| `market_cap` | float | mapped market capitalization |
| `pe_ratio` | float | valuation metric when available |
| `price_to_sales` | float | valuation metric when available |
| `price_to_book` | float | valuation metric when available |
| `ev_to_ebitda` | float | valuation metric when available |
| `gross_margin` | float | profitability metric when available |
| `operating_margin` | float | profitability metric when available |
| `roe` | float | profitability metric when available |
| `roa` | float | profitability metric when available |
| `revenue_growth` | float | growth metric when available |
| `eps_growth` | float | growth metric when available |
| `debt_to_equity` | float | balance-sheet metric when available |
| `current_ratio` | float | balance-sheet metric when available |

### `outputs/data/monthly_panel.parquet`

Primary key:

- `ticker`, `date`

Required implemented columns:

| Column | Type | Notes |
| --- | --- | --- |
| `ticker` | string | analytic unit key |
| `date` | timestamp | calendar month-end observation key |
| `adjusted_close` | float | inherited from prices table |
| `monthly_return` | float | security month-over-month return |
| `benchmark_ticker` | string | current configured primary benchmark id |
| `benchmark_return` | float | aligned primary benchmark return |
| `sector` | string | classification field |
| `industry` | string | classification field |
| `market_cap` | float | lagged mapped market capitalization |
| valuation metrics | float columns | currently `pe_ratio`, `price_to_sales`, `price_to_book`, `ev_to_ebitda` |
| profitability metrics | float columns | currently `gross_margin`, `operating_margin`, `roe`, `roa` |
| growth metrics | float columns | currently `revenue_growth`, `eps_growth` |
| balance-sheet metrics | float columns | currently `debt_to_equity`, `current_ratio` |
| `fundamentals_source_date` | timestamp | documented monthly fundamentals source mapping |
| `fundamentals_effective_date` | timestamp | documented effective date used in the merge |
| `volume` | float or int | inherited monthly volume when available |

Panel construction rule:

- The panel is built on the full universe-by-month grid derived from the union of processed price dates and primary benchmark dates. Missingness remains visible in the panel rather than being silently dropped.

## QC And Coverage Artifacts

### Dataset QC JSON

- `outputs/data/prices_qc_summary.json`
- `outputs/data/fundamentals_qc_summary.json`
- `outputs/data/benchmarks_qc_summary.json`
- `outputs/data/panel_qc_summary.json`

Current summary content includes:

- row count
- column count
- column list
- unique identifier count
- min and max date
- duplicate key count
- missing count by column

### Coverage CSV

- `outputs/data/ticker_coverage_summary.csv`
- `outputs/data/date_coverage_summary.csv`

These make per-ticker and per-date coverage, missingness, and panel completeness easy to inspect outside of code.

## Downstream Contract

The implemented monthly panel is the required upstream input for:

- `outputs/features/feature_panel.parquet`
- later signal generation
- later benchmark-relative backtesting
- later chronology-safe modeling datasets

## Change Control

- All joins must remain explicit on documented keys.
- Schema changes require synchronized updates to code, tests, docs, and progress files.
- Do not treat the current lagged fundamentals mapping as proof of point-in-time safety.
