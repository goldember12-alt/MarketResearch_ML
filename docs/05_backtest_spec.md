# 05 Backtest Specification

## Baseline Portfolio Form

The implemented deterministic backtest currently uses:

- deterministic cross-sectional ranking inputs from `outputs/signals/signal_rankings.parquet`
- top `N=10` long-only stock selection
- monthly rebalance
- equal-weight holdings by default
- explicit benchmark comparison to `SPY`, `QQQ`, and `equal_weight_universe`

These defaults come from `config/backtest.yaml` and are explicit assumptions, not validated research findings.

The repo now also supports an aggregated out-of-sample model-driven backtest that:

- reads model scores from `outputs/models/test_predictions.parquet`
- uses only the configured out-of-sample prediction splits, currently `test`
- ranks names cross-sectionally by `predicted_probability`
- applies the same top-N, weighting, turnover, cost, and benchmark rules
- writes separate `model_*` backtest artifacts so the deterministic baseline outputs remain intact

Execution-mode note:

- the seeded verification path remains the default
- the optional `research_scale` execution mode is designed for the same backtest logic on longer local raw histories when those files are available upstream
- the implemented Alpha Vantage + SEC remote acquisition layer should only increase upstream raw coverage; it must not change the implemented backtest contract

## Inputs

Required inputs:

- `outputs/signals/signal_rankings.parquet`
- `outputs/data/monthly_panel.parquet`
- `outputs/data/benchmarks_monthly.parquet`
- `config/backtest.yaml`

Model-driven backtest inputs:

- `outputs/models/test_predictions.parquet`
- `outputs/models/model_metadata.json`
- `outputs/data/monthly_panel.parquet`
- `outputs/data/benchmarks_monthly.parquet`
- `config/backtest.yaml`
- `config/model.yaml`

The backtest stage validates duplicate keys on:

- `signal_rankings`: `ticker`, `date`
- `monthly_panel`: `ticker`, `date`
- `benchmarks_monthly`: `benchmark_ticker`, `date`

## Decision, Execution, And Holding Convention

Implemented timing assumptions:

- decision frequency: monthly
- decision anchor: month-end
- trade timing assumption label: `next_period_open`
- information set: only data available through the rebalance decision date

Implemented holding-period convention:

- signal date `t` is the rebalance and portfolio-formation date
- holdings selected using information available at `t` earn realized monthly returns recorded at the next month-end `t+1`
- `holdings_history.parquet.date` is the formation date `t`
- `portfolio_returns.parquet.date` is the realized return date `t+1`
- same-month future information is not used

Model-driven integration note:

- when the ranking input includes an explicit realized period end such as `realized_label_date`, that value overrides next-ranking-date inference
- this allows aggregated out-of-sample prediction months to backtest against the correct realized `t+1` month even when later decision months are not yet available

This convention is the repo's current leakage-safe monthly backtest baseline.

## Holdings Construction

Implemented rules:

- use the `selected_top_n` flag from the signal artifact when present
- validate that `selected_top_n` is consistent with `score_rank <= configured_top_n`
- construct one holdings snapshot per rebalance month
- output one row per selected security per rebalance date
- record the next realized month-end as `holding_period_end`

Current weighting options:

- `equal_weight`
- `capped_weight`

Current cash policies:

- `redistribute`
  Fully invest across the available selected names.
- `hold_cash`
  Keep unallocated residual cash if the configured top-N count is not filled or if a cap prevents full investment.

Current default config:

- `weighting: equal_weight`
- `cash_handling_policy: redistribute`

## Trade Log And Turnover

Trade-log construction:

- compare each rebalance snapshot with the immediately prior rebalance snapshot
- label rows as `entry`, `exit`, `increase`, `decrease`, or `rebalance`
- keep previous and target weights so turnover is auditable

Turnover definition:

- one-way turnover for a rebalance month is `max(total_buy_weight, total_sell_weight)`
- the first investable rebalance is handled explicitly from prior cash
- empty-selection months are allowed and can liquidate the portfolio back to cash

## Return Calculation

Portfolio gross return:

- weighted average of selected security `monthly_return` values aligned to `holding_period_end`
- residual cash earns `0.0` in the current baseline

Portfolio net return:

- `portfolio_gross_return - transaction_cost`

Current transaction cost model:

- linear turnover-based one-way cost
- `transaction_cost = turnover * (transaction_cost_bps + slippage_bps) / 10000`

Current default costs from config:

- transaction cost: `10.0` bps
- slippage: `0.0` bps

Missing realized return policy:

- if a selected security has a valid `holding_period_end` but no realized `monthly_return`, fill the missing realized return with `0.0`
- log the count and examples in `backtest_summary.json`

## Benchmark Comparison

Benchmark rules:

- benchmarks are read directly from `outputs/data/benchmarks_monthly.parquet`
- only configured identifiers are aligned into the backtest outputs
- benchmark returns must exist for every realized portfolio date
- benchmark comparisons are explicit and not inferred from `monthly_panel.benchmark_return`

Implemented benchmark outputs:

- long-form aligned benchmark series in `outputs/backtests/benchmark_returns.parquet`
- wide aligned benchmark columns in `outputs/backtests/performance_by_period.csv`

## Outputs

Required outputs written by the implemented stage:

- `outputs/backtests/holdings_history.parquet`
- `outputs/backtests/trade_log.parquet`
- `outputs/backtests/portfolio_returns.parquet`
- `outputs/backtests/benchmark_returns.parquet`
- `outputs/backtests/backtest_summary.json`
- `outputs/backtests/performance_by_period.csv`
- `outputs/backtests/risk_metrics_summary.csv`

Additional outputs written by the model-driven backtest stage:

- `outputs/models/model_signal_rankings.parquet`
- `outputs/backtests/model_holdings_history.parquet`
- `outputs/backtests/model_trade_log.parquet`
- `outputs/backtests/model_portfolio_returns.parquet`
- `outputs/backtests/model_benchmark_returns.parquet`
- `outputs/backtests/model_backtest_summary.json`
- `outputs/backtests/model_performance_by_period.csv`
- `outputs/backtests/model_risk_metrics_summary.csv`

Coverage-aware reporting outputs fed by backtest summaries:

- `outputs/reports/run_summary.json`

## Metrics

Implemented metrics:

- cumulative return
- annualized return
- annualized volatility
- Sharpe ratio
- Sortino ratio
- max drawdown
- turnover
- hit rate

Current implementation notes:

- annualization assumes monthly periodicity and uses `12` periods per year
- volatility uses monthly standard deviation annualized by `sqrt(12)`
- Sortino is zero-rate and can be `NaN` when there are no downside observations
- short samples can produce unstable annualized values; the metrics are still reported but should not be overinterpreted

## Validation And QC

Implemented validation checks:

- duplicate-key checks on all required inputs
- one holdings row per ticker-date
- holdings-plus-cash weight sum consistency
- benchmark coverage on every realized portfolio date
- missing realized return logging

Current compact QC output:

- embedded in `outputs/backtests/backtest_summary.json`
- includes coverage counts such as formation months, realized months, average selected tickers, and unique held tickers

## Research Guardrails

- Portfolio construction must use only current-stage signals, not future outcomes.
- Benchmarks must be reported alongside the strategy, not omitted when unfavorable.
- Any filter, cap, or universe exclusion must be documented in the experiment record once experiment logging is implemented.
- Exploratory runs must not be described as canonical benchmark results.
- Fundamentals-derived inputs still inherit revised-history bias risk until true point-in-time data are introduced.
- Aggregated out-of-sample model-driven backtests remain exploratory until they are extended over longer history and evaluated under the same reporting discipline as the deterministic baseline.
- When the `research_scale` path falls back to sample-tagged raw files, downstream interpretation must still be treated as seeded-sample verification rather than longer-history evidence.
