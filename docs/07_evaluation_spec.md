# 07 Evaluation Specification

## Evaluation Objective

Evaluation must show whether a strategy meaningfully outperforms explicit benchmarks after realistic controls, not just whether it produced a high raw return in one period.

## Required Metrics

The implemented deterministic baseline now writes these metrics:

- cumulative return
- annualized return
- annualized volatility
- Sharpe ratio
- Sortino ratio
- max drawdown
- turnover
- hit rate

Current metric definitions:

- annualized return: compounded monthly return annualized by `12 / period_count`
- annualized volatility: monthly return standard deviation annualized by `sqrt(12)`
- Sharpe ratio: zero-rate Sharpe using monthly mean and sample volatility
- Sortino ratio: zero-rate Sortino using downside deviation from monthly returns
- max drawdown: minimum wealth-relative drawdown from the cumulative return path
- turnover: one-way traded notional fraction, defined per period as `max(total_buys, total_sells)`
- hit rate: fraction of realized months with positive return

## Required Benchmark Context

Every benchmark-quality evaluation must state:

- universe preset
- date range
- benchmark set
- rebalance frequency
- transaction cost assumptions
- any filtering constraints or sample caps
- whether the result is deterministic baseline or ML-based
- the exact holding-period convention

## Implemented Output Tables

Current deterministic backtest evaluation tables:

- `outputs/backtests/performance_by_period.csv`
- `outputs/backtests/risk_metrics_summary.csv`
- `outputs/backtests/backtest_summary.json`

Current reporting outputs:

- `outputs/reports/strategy_report.md`
- `outputs/reports/experiment_registry.jsonl`

Current modeling-diagnostic outputs:

- `outputs/models/train_predictions.parquet`
- `outputs/models/test_predictions.parquet`
- `outputs/models/model_metadata.json`
- `outputs/models/feature_importance.csv`

## Period And Robustness Breakdowns

The current implementation provides:

- full-period portfolio and benchmark summary metrics
- per-period aligned portfolio and benchmark return tables
- a benchmark-aware exploratory strategy report
- experiment-registry append logic for meaningful evaluation-report runs

The following remain deferred:

- subperiod summary by major market regime
- information ratio and benchmark-relative attribution tables
- concentration-aware interpretation for the seeded tech-heavy universe
- automated regime-aware report sections
- model-driven portfolio evaluation under the same transaction cost controls as the deterministic baseline

## Interpretation Standard

- Deterministic baselines come first.
- No model or strategy should be evaluated only in-sample.
- Current model-stage metrics are prediction diagnostics, not model-driven portfolio performance results.
- Any result using revised historical fundamentals must include that caveat.
- Lack of benchmark comparison makes a result incomplete.
- Small-sample annualized metrics are descriptive, not conclusive.
- Current reporting outputs must explicitly remain exploratory unless stronger evidence is actually available.
