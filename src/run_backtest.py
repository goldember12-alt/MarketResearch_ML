"""CLI entrypoint for deterministic monthly portfolio backtesting."""

from __future__ import annotations

import logging

from src.backtest.config import configure_backtest_logging, load_backtest_pipeline_config
from src.backtest.holdings import build_holdings_history
from src.backtest.metrics import (
    build_backtest_summary,
    build_performance_by_period,
    build_risk_metrics_summary,
)
from src.backtest.qc import build_backtest_qc_summary
from src.backtest.returns import build_benchmark_returns, build_portfolio_returns
from src.backtest.trades import build_trade_log
from src.data.io import read_parquet_required, write_csv, write_json, write_parquet
from src.utils.config import ensure_output_directories


def main() -> int:
    """Run the deterministic monthly backtest stage."""
    config = load_backtest_pipeline_config()
    configure_backtest_logging(config)
    ensure_output_directories(config.project)

    logger = logging.getLogger(__name__)
    logger.info("Starting deterministic backtest stage.")

    signal_rankings = read_parquet_required(config.outputs.signal_rankings, "signal_rankings")
    monthly_panel = read_parquet_required(config.outputs.monthly_panel, "monthly_panel")
    benchmarks_monthly = read_parquet_required(
        config.outputs.benchmarks_monthly, "benchmarks_monthly"
    )

    holdings_history, rebalance_summary = build_holdings_history(signal_rankings, config)
    trade_log, turnover_summary = build_trade_log(holdings_history, rebalance_summary)
    portfolio_returns, holding_return_details = build_portfolio_returns(
        holdings_history,
        rebalance_summary,
        monthly_panel,
        turnover_summary,
        config,
    )
    benchmark_returns = build_benchmark_returns(
        benchmarks_monthly,
        portfolio_returns,
        config,
    )
    performance_by_period = build_performance_by_period(portfolio_returns, benchmark_returns)
    risk_metrics_summary = build_risk_metrics_summary(portfolio_returns, benchmark_returns)
    qc_summary = build_backtest_qc_summary(
        config=config,
        holdings_history=holdings_history,
        rebalance_summary=rebalance_summary,
        holding_return_details=holding_return_details,
        portfolio_returns=portfolio_returns,
        benchmark_returns=benchmark_returns,
    )
    backtest_summary = build_backtest_summary(
        config,
        portfolio_returns,
        benchmark_returns,
        risk_metrics_summary,
        qc_summary,
    )

    write_parquet(holdings_history, config.outputs.holdings_history)
    write_parquet(trade_log, config.outputs.trade_log)
    write_parquet(portfolio_returns, config.outputs.portfolio_returns)
    write_parquet(benchmark_returns, config.outputs.benchmark_returns)
    write_csv(performance_by_period, config.outputs.performance_by_period)
    write_csv(risk_metrics_summary, config.outputs.risk_metrics_summary)
    write_json(backtest_summary, config.outputs.backtest_summary)

    logger.info("Wrote %s", config.outputs.backtest_summary)
    print("Backtest completed.")
    print(config.outputs.holdings_history)
    print(config.outputs.trade_log)
    print(config.outputs.portfolio_returns)
    print(config.outputs.benchmark_returns)
    print(config.outputs.performance_by_period)
    print(config.outputs.risk_metrics_summary)
    print(config.outputs.backtest_summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
