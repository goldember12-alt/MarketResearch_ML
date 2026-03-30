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
- `outputs/reports/model_strategy_report.md`
- `outputs/reports/run_summary.json`
- `outputs/reports/model_comparison_summary.json`
- `outputs/reports/model_subperiod_comparison.csv`
- `outputs/reports/experiment_registry.jsonl`

Current modeling-diagnostic outputs:

- `outputs/models/train_predictions.parquet`
- `outputs/models/test_predictions.parquet`
- `outputs/models/model_metadata.json`
- `outputs/models/feature_importance.csv`

Current model-driven backtest outputs:

- `outputs/backtests/model_portfolio_returns.parquet`
- `outputs/backtests/model_benchmark_returns.parquet`
- `outputs/backtests/model_performance_by_period.csv`
- `outputs/backtests/model_risk_metrics_summary.csv`
- `outputs/backtests/model_backtest_summary.json`

Current multi-window modeling metadata also records:

- fold count
- fold window boundaries
- aggregated out-of-sample decision and realized date coverage
- aggregated out-of-sample classification metrics

## Period And Robustness Breakdowns

The current implementation provides:

- full-period portfolio and benchmark summary metrics
- per-period aligned portfolio and benchmark return tables
- a benchmark-aware exploratory strategy report
- a model-aware exploratory strategy report for the current canonical model run
- a top-level run summary with raw-data selection context and stage-level coverage counts
- overlap-aware deterministic-vs-model comparison metrics computed only on shared realized dates
- overlap-window regime and subperiod diagnostics broken out by fold, calendar quarter, calendar half-year, calendar year, benchmark direction, benchmark drawdown state, and benchmark volatility state
- held-out fold coverage and fold-level diagnostics derived from aggregated out-of-sample predictions
- a machine-readable comparison summary for the model-aware reporting stage
- a machine-readable subperiod comparison table for the model-aware reporting stage
- experiment-registry append logic for meaningful evaluation-report runs

The following remain deferred:

- information ratio and benchmark-relative attribution tables
- concentration-aware interpretation for the seeded tech-heavy universe
- stronger regime evidence from materially longer realized overlap history

## Interpretation Standard

- Deterministic baselines come first.
- No model or strategy should be evaluated only in-sample.
- Current model-stage metrics include both multi-window prediction diagnostics and a short aggregated out-of-sample model-driven backtest, but they remain exploratory.
- Deterministic-vs-model comparisons must be computed only on overlapping realized dates when the model backtest covers fewer months than the deterministic baseline.
- Segment evidence must be labeled explicitly as `insufficient_segment_history`, `descriptive_segment_evidence`, or `broader_coverage_exploratory_evidence` using the thresholds configured in `config/evaluation.yaml`.
- The run summary must disclose whether a `research_scale` execution actually used broader local raw files or only sample fallback.
- Any result using revised historical fundamentals must include that caveat.
- Lack of benchmark comparison makes a result incomplete.
- Small-sample annualized metrics are descriptive, not conclusive.
- Current reporting outputs must explicitly remain exploratory unless stronger evidence is actually available.
