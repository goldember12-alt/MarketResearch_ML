# 07 Evaluation Specification

## Evaluation Objective

Evaluation must show whether a strategy meaningfully outperforms explicit benchmarks after realistic controls, not just whether it produced a high raw return in one period.

## Required Metrics

- annualized return
- annualized volatility
- Sharpe ratio
- Sortino ratio
- max drawdown
- information ratio versus benchmark where applicable
- turnover
- hit rate

## Required Benchmark Context

Every benchmark-quality evaluation must state:

- universe preset
- date range
- benchmark set
- rebalance frequency
- transaction cost assumptions
- any filtering constraints or sample caps
- whether the result is deterministic baseline or ML-based

## Expected Report Outputs

- `outputs/reports/strategy_report.md`
- `outputs/reports/performance_by_period.csv`
- `outputs/reports/risk_metrics_summary.csv`

## Period And Robustness Breakdowns

The initial scaffold reserves these breakdowns for later implementation:

- full-period summary
- subperiod summary by major market regime
- benchmark-relative return comparison
- concentration-aware interpretation for the seeded tech-heavy universe

## Interpretation Standard

- Deterministic baselines come first.
- No model or strategy should be evaluated only in-sample.
- Any result using revised historical fundamentals must include that caveat.
- Lack of benchmark comparison makes a result incomplete.
