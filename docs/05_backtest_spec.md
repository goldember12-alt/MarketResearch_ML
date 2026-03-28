# 05 Backtest Specification

## Baseline Portfolio Form

The canonical early-stage backtest is:

- deterministic cross-sectional ranking
- top `N=10` stock selection
- equal-weight holdings
- monthly rebalance
- explicit benchmark comparison to `SPY`, `QQQ`, and `equal_weight_universe`

These defaults come from `config/backtest.yaml` and are scaffold assumptions, not validated research findings.

## Decision And Execution Timing

- Decision frequency: monthly
- Decision anchor: month-end
- Trade timing assumption: `next_period_open`
- Information set: only data available through the rebalance decision date

## Current Cost Assumptions

- transaction cost: `10.0` bps per trade
- slippage: `0.0` bps

These values are placeholders for the first deterministic baseline and must be disclosed with every result.

## Required Inputs

- `outputs/data/monthly_panel.parquet`
- `outputs/features/feature_panel.parquet`
- deterministic ranking output from `src.signals`
- `config/backtest.yaml`
- benchmark return series aligned to the monthly rebalance calendar

## Required Outputs

- `outputs/backtests/holdings_history.parquet`
- `outputs/backtests/trade_log.parquet`
- `outputs/backtests/portfolio_returns.parquet`
- `outputs/backtests/benchmark_returns.parquet`
- `outputs/backtests/backtest_summary.json`

## Required Metrics

- cumulative return
- annualized return
- annualized volatility
- Sharpe ratio
- Sortino ratio
- max drawdown
- turnover
- hit rate

## Backtest Rules

- Portfolio construction must use only current-stage signals, not future outcomes.
- Turnover must be explicit and cost-adjusted.
- Benchmarks must be reported alongside the strategy, not omitted when unfavorable.
- Any filter, cap, or universe exclusion must be documented in the experiment record.
- Exploratory runs must not be described as canonical benchmark results.
