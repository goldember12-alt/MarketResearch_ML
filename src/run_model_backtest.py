"""CLI entrypoint for model-driven monthly backtesting."""

from __future__ import annotations

import json
import logging
import sys

from src.backtest.config import configure_backtest_logging, load_backtest_pipeline_config
from src.backtest.holdings import build_holdings_history
from src.backtest.metrics import (
    build_performance_by_period,
    build_risk_metrics_summary,
)
from src.backtest.qc import build_backtest_qc_summary
from src.backtest.returns import build_benchmark_returns, build_portfolio_returns
from src.backtest.trades import build_trade_log
from src.data.io import read_parquet_required, write_csv, write_json, write_parquet
from src.models.backtest import (
    build_model_backtest_registry_record,
    build_model_backtest_summary,
    build_model_signal_rankings,
)
from src.models.config import load_model_pipeline_config
from src.reporting.registry import append_experiment_record
from src.utils.cli import parse_execution_mode_args
from src.utils.config import ensure_output_directories


def main(argv: list[str] | None = None) -> int:
    """Run a held-out model-driven backtest using the current model predictions."""
    args = parse_execution_mode_args(argv)
    model_config = load_model_pipeline_config(execution_mode=args.execution_mode)
    backtest_config = load_backtest_pipeline_config(
        model_config.root_dir,
        execution_mode=args.execution_mode,
    )
    configure_backtest_logging(backtest_config)
    ensure_output_directories(model_config.project)

    logger = logging.getLogger(__name__)
    logger.info("Starting model-driven backtest stage.")

    predictions = read_parquet_required(model_config.outputs.test_predictions, "test_predictions")
    monthly_panel = read_parquet_required(model_config.outputs.monthly_panel, "monthly_panel")
    benchmarks_monthly = read_parquet_required(
        model_config.outputs.benchmarks_monthly, "benchmarks_monthly"
    )
    model_metadata = json.loads(model_config.outputs.model_metadata.read_text(encoding="utf-8"))

    model_signal_rankings, signal_metadata = build_model_signal_rankings(
        predictions,
        model_config=model_config,
        backtest_config=backtest_config,
    )
    holdings_history, rebalance_summary = build_holdings_history(
        model_signal_rankings,
        backtest_config,
    )
    trade_log, turnover_summary = build_trade_log(holdings_history, rebalance_summary)
    portfolio_returns, holding_return_details = build_portfolio_returns(
        holdings_history,
        rebalance_summary,
        monthly_panel,
        turnover_summary,
        backtest_config,
    )
    benchmark_returns = build_benchmark_returns(
        benchmarks_monthly,
        portfolio_returns,
        backtest_config,
    )
    performance_by_period = build_performance_by_period(portfolio_returns, benchmark_returns)
    risk_metrics_summary = build_risk_metrics_summary(portfolio_returns, benchmark_returns)
    qc_summary = build_backtest_qc_summary(
        config=backtest_config,
        holdings_history=holdings_history,
        rebalance_summary=rebalance_summary,
        holding_return_details=holding_return_details,
        portfolio_returns=portfolio_returns,
        benchmark_returns=benchmark_returns,
    )
    backtest_summary = build_model_backtest_summary(
        model_config=model_config,
        backtest_config=backtest_config,
        model_metadata=model_metadata,
        portfolio_returns=portfolio_returns,
        benchmark_returns=benchmark_returns,
        risk_metrics_summary=risk_metrics_summary,
        qc_summary=qc_summary,
        signal_metadata=signal_metadata,
    )

    write_parquet(model_signal_rankings, model_config.outputs.model_signal_rankings)
    write_parquet(holdings_history, model_config.outputs.model_holdings_history)
    write_parquet(trade_log, model_config.outputs.model_trade_log)
    write_parquet(portfolio_returns, model_config.outputs.model_portfolio_returns)
    write_parquet(benchmark_returns, model_config.outputs.model_benchmark_returns)
    write_csv(performance_by_period, model_config.outputs.model_performance_by_period)
    write_csv(risk_metrics_summary, model_config.outputs.model_risk_metrics_summary)
    write_json(backtest_summary, model_config.outputs.model_backtest_summary)

    record = build_model_backtest_registry_record(
        model_config=model_config,
        backtest_summary=backtest_summary,
        artifacts_written=[
            str(model_config.outputs.model_signal_rankings),
            str(model_config.outputs.model_holdings_history),
            str(model_config.outputs.model_trade_log),
            str(model_config.outputs.model_portfolio_returns),
            str(model_config.outputs.model_benchmark_returns),
            str(model_config.outputs.model_performance_by_period),
            str(model_config.outputs.model_risk_metrics_summary),
            str(model_config.outputs.model_backtest_summary),
            str(model_config.outputs.experiment_registry),
        ],
    )
    append_experiment_record(record, model_config.outputs.experiment_registry)

    logger.info("Wrote %s", model_config.outputs.model_backtest_summary)
    print("Model backtest completed.")
    print(model_config.outputs.model_signal_rankings)
    print(model_config.outputs.model_holdings_history)
    print(model_config.outputs.model_trade_log)
    print(model_config.outputs.model_portfolio_returns)
    print(model_config.outputs.model_benchmark_returns)
    print(model_config.outputs.model_performance_by_period)
    print(model_config.outputs.model_risk_metrics_summary)
    print(model_config.outputs.model_backtest_summary)
    print(model_config.outputs.experiment_registry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
