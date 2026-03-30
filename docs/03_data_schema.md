# 03 Data Schema

## Canonical Frequency And Grain

- Frequency: monthly
- Decision grain: one row per ticker per month
- Date convention: normalized calendar month-end
- Deterministic keys only

The canonical monthly panel is the shared upstream table for feature generation, deterministic signals, and later chronology-safe modeling workflows.

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
| `market_cap` | float | mapped market cap |
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
| `sector` | string | metadata only |
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

### `outputs/signals/signal_rankings.parquet`

Primary key:

- `ticker`, `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| metadata columns | mixed | inherited from `feature_panel.parquet` |
| raw feature columns | float | inherited lagged predictive inputs |
| `score__*` columns | float | cross-sectional percentile scores by month |
| `non_missing_feature_count` | int | count of configured raw feature values available for scoring |
| `composite_score` | float | available-feature weighted mean of score columns |
| `score_rank` | float | deterministic within-month composite rank, 1 is best |
| `score_rank_pct` | float | `score_rank / scored_row_count` within the month |
| `selected_top_n` | bool | whether the name falls inside configured top-N selection |

### `outputs/backtests/holdings_history.parquet`

Primary key:

- `date`, `ticker`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| `date` | timestamp | rebalance decision month-end `t` |
| `ticker` | string | selected security identifier |
| `portfolio_weight` | float | target security weight used for the next period |
| `signal_rank` | float | selected deterministic rank from the signal artifact |
| `composite_score` | float | selected deterministic composite score |
| `holding_period_start` | timestamp | same as rebalance decision date `t` |
| `holding_period_end` | timestamp | next realized month-end `t+1` |
| `selected_name_count` | int | number of selected securities at rebalance date `t` |
| `configured_top_n` | int | configured target top-N count |
| `target_weight_sum` | float | total invested weight across selected securities |
| `cash_weight` | float | residual cash weight implied by config and selection availability |
| `sector` | string | classification metadata for auditability |
| `industry` | string | classification metadata for auditability |

### `outputs/backtests/trade_log.parquet`

Primary key:

- `rebalance_date`, `ticker`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| `rebalance_date` | timestamp | current rebalance month-end `t` |
| `previous_rebalance_date` | timestamp | prior rebalance month-end |
| `ticker` | string | security identifier affected by the rebalance |
| `trade_type` | string | `entry`, `exit`, `increase`, `decrease`, or `rebalance` |
| `portfolio_weight_previous` | float | prior target weight before the rebalance |
| `portfolio_weight_target` | float | new target weight after the rebalance |
| `weight_change` | float | signed target-weight change |
| `abs_weight_change` | float | absolute target-weight change |
| `buy_weight` | float | positive traded notional fraction |
| `sell_weight` | float | negative traded notional fraction expressed positively |

### `outputs/backtests/portfolio_returns.parquet`

Primary key:

- `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| `date` | timestamp | realized month-end return date `t+1` |
| `formation_date` | timestamp | rebalance decision date `t` that formed the holdings |
| `holding_count` | int | count of securities with active holdings in the realized period |
| `selected_name_count` | int | selected security count at formation date |
| `invested_weight` | float | total invested security weight |
| `cash_weight` | float | residual cash weight for the period |
| `gross_buy_weight` | float | aggregate buy notional at formation date |
| `gross_sell_weight` | float | aggregate sell notional at formation date |
| `gross_trade_weight` | float | sum of absolute target-weight changes |
| `turnover` | float | one-way traded notional fraction, defined as `max(buys, sells)` |
| `missing_security_return_count` | int | count of selected names whose realized return was missing and filled with `0.0` |
| `portfolio_gross_return` | float | weighted gross portfolio return before costs |
| `transaction_cost_rate` | float | decimal one-way cost rate applied to turnover |
| `transaction_cost` | float | turnover times configured cost rate |
| `portfolio_net_return` | float | gross return minus transaction cost |
| `cumulative_gross_return` | float | chained gross cumulative return |
| `cumulative_net_return` | float | chained net cumulative return |

### `outputs/backtests/benchmark_returns.parquet`

Primary key:

- `benchmark_ticker`, `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| `date` | timestamp | realized benchmark month-end return date `t+1` |
| `formation_date` | timestamp | portfolio formation date `t` aligned to the same realized period |
| `benchmark_ticker` | string | configured benchmark identifier |
| `benchmark_return` | float | realized monthly benchmark return aligned to the portfolio date |
| `cumulative_return` | float | chained cumulative benchmark return |

### `outputs/backtests/performance_by_period.csv`

Primary key:

- `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| portfolio return columns | mixed | copied from `portfolio_returns.parquet` |
| `benchmark_return__*` | float | wide benchmark monthly returns aligned to each realized period |
| `benchmark_cumulative_return__*` | float | wide benchmark cumulative returns aligned to each realized period |

### `outputs/backtests/risk_metrics_summary.csv`

Primary key:

- `series_id`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| `series_id` | string | `portfolio_gross`, `portfolio_net`, or benchmark identifier |
| `series_type` | string | `portfolio` or `benchmark` |
| `period_count` | int | realized monthly period count in the summary |
| `cumulative_return` | float | chained total return |
| `annualized_return` | float | monthly compounded return annualized by `12 / periods` |
| `annualized_volatility` | float | monthly return standard deviation annualized by `sqrt(12)` |
| `sharpe_ratio` | float | zero-rate Sharpe ratio |
| `sortino_ratio` | float | zero-rate Sortino ratio |
| `max_drawdown` | float | worst peak-to-trough decline |
| `hit_rate` | float | share of realized months with positive return |
| `average_turnover` | float | mean one-way turnover for applicable series |
| `total_turnover` | float | total one-way turnover for applicable series |

### `outputs/backtests/backtest_summary.json`

Structure:

- stage config snapshot
- holding-period convention
- realized date range
- benchmark list
- metrics by series
- compact QC summary

### `outputs/reports/strategy_report.md`

Current contents:

- run status and timestamp
- universe, benchmarks, rebalance, and cost assumptions
- portfolio summary metrics
- explicit benchmark comparison
- risk controls
- bias caveats
- cautious interpretation
- next recommended implementation step

### `outputs/reports/experiment_registry.jsonl`

One JSON object per line with at minimum:

- `experiment_id`
- `run_timestamp`
- `stage`
- `purpose`
- `date_range`
- `universe_preset`
- `benchmark_set`
- `feature_set`
- `signal_or_model`
- `portfolio_rules`
- `rebalance_frequency`
- `transaction_cost_bps`
- `artifacts_written`
- `result_summary`
- `interpretation`
- `status`
- `next_step`

Modeling-stage runs now also append exploratory records here, using the same high-level fields but with `stage = "modeling_baselines"`.

### `outputs/models/train_predictions.parquet`

Primary key:

- `ticker`, `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| `ticker` | string | analytic unit key |
| `date` | timestamp | decision month-end `t` used for prediction |
| `realized_label_date` | timestamp | future realized label month-end `t+1` under the current default label |
| `benchmark_ticker` | string | benchmark identifier used for the benchmark-relative label |
| `sector` | string | metadata only |
| `industry` | string | metadata only |
| `true_label` | int | realized binary label |
| `forward_raw_return` | float | realized next-period raw return used in label construction |
| `forward_benchmark_return` | float | realized next-period benchmark return used in label construction |
| `forward_excess_return` | float | realized next-period raw return minus benchmark return |
| `split` | string | currently `train` only in this artifact |
| `model_feature_non_missing_count` | int | count of configured model features available before preprocessing |
| `model_type` | string | current fitted model identifier |
| `predicted_probability` | float | model-estimated probability for class `1` |
| `predicted_class` | int | thresholded class prediction |
| `deterministic_composite_score` | float | aligned deterministic signal score when available |
| `deterministic_selected_top_n` | bool | aligned deterministic top-N class proxy when available |
| `deterministic_score_rank` | float | aligned deterministic within-month rank when available |
| `deterministic_score_rank_pct` | float | aligned deterministic rank percentile when available |

### `outputs/models/test_predictions.parquet`

Primary key:

- `ticker`, `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| all columns from `train_predictions.parquet` | mixed | same schema for held-out scoring |
| `split` | string | currently `validation` or `test` |

### `outputs/models/feature_importance.csv`

Primary key:

- `feature`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| `feature` | string | configured model feature name |
| `importance` | float | absolute coefficient magnitude or impurity importance |
| `signed_importance` | float | signed coefficient for logistic regression, same as `importance` for random forest |
| `importance_type` | string | `standardized_logistic_coefficient` or `impurity_importance` |
| `model_type` | string | fitted model identifier that produced the export |

### `outputs/models/model_metadata.json`

Structure:

- run timestamp and stage status
- label definition and label settings
- configured chronological split windows
- configured feature list and minimum non-missing rule
- preprocessing fit settings and fit window
- model type and core hyperparameters
- row counts by split
- dropped-row summary
- split-level model metrics
- deterministic baseline comparison context
- compact QC summary
- artifact paths, caveats, and next recommended implementation step

### `outputs/models/model_signal_rankings.parquet`

Primary key:

- `ticker`, `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| held-out prediction columns | mixed | inherited from `outputs/models/test_predictions.parquet` |
| `composite_score` | float | model score reused as the portfolio ranking score |
| `score_rank` | float | within-month model-score rank, 1 is best |
| `score_rank_pct` | float | `score_rank / row_count` within the month |
| `selected_top_n` | bool | whether the name falls inside configured top-N selection for the model-driven backtest |

### `outputs/backtests/model_holdings_history.parquet`

Primary key:

- `date`, `ticker`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| same schema as `outputs/backtests/holdings_history.parquet` | mixed | model-driven holdings formed from held-out model rankings |

### `outputs/backtests/model_trade_log.parquet`

Primary key:

- `rebalance_date`, `ticker`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| same schema as `outputs/backtests/trade_log.parquet` | mixed | trade log for the model-driven backtest |

### `outputs/backtests/model_portfolio_returns.parquet`

Primary key:

- `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| same schema as `outputs/backtests/portfolio_returns.parquet` | mixed | realized model-driven portfolio returns |

### `outputs/backtests/model_benchmark_returns.parquet`

Primary key:

- `benchmark_ticker`, `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| same schema as `outputs/backtests/benchmark_returns.parquet` | mixed | benchmark returns aligned to the model-driven portfolio dates |

### `outputs/backtests/model_performance_by_period.csv`

Primary key:

- `date`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| same schema as `outputs/backtests/performance_by_period.csv` | mixed | model-driven per-period portfolio and benchmark comparison table |

### `outputs/backtests/model_risk_metrics_summary.csv`

Primary key:

- `series_id`

Columns:

| Column | Type | Notes |
| --- | --- | --- |
| same schema as `outputs/backtests/risk_metrics_summary.csv` | mixed | risk metrics for the model-driven portfolio and aligned benchmarks |

### `outputs/backtests/model_backtest_summary.json`

Structure:

- shared backtest summary fields from the deterministic backtest
- model type
- model label definition
- prediction score column used for ranking
- held-out prediction splits used for portfolio formation
- compact QC summary
- caveats and next recommended implementation step

## QC Artifacts

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

### Signal-Stage QC

- `outputs/signals/signal_qc_summary.json`
- `outputs/signals/signal_selection_summary.csv`

### Backtest-Stage QC

Backtest QC currently lives inside `outputs/backtests/backtest_summary.json` and includes:

- benchmark alignment status
- holdings and rebalance row counts
- realized missing-return policy and count
- max holdings-plus-cash weight deviation from `1.0`
- min and max cash weight across rebalances

The model-driven backtest writes the same QC structure inside:

- `outputs/backtests/model_backtest_summary.json`

### Reporting-Stage Outputs

The evaluation-report stage currently writes:

- `outputs/reports/strategy_report.md`
- `outputs/reports/experiment_registry.jsonl`

### Modeling-Stage QC

Model QC currently lives inside `outputs/models/model_metadata.json` and includes:

- row counts by split
- decision and realized date ranges by split
- dropped-row counts for missing labels, insufficient features, and out-of-window rows
- whether deterministic baseline context was available

## Change Control

- All schema changes require synchronized updates to code, tests, docs, and progress files.
- Do not treat lagged fundamentals or fundamentals-derived signals as proof of point-in-time safety.
