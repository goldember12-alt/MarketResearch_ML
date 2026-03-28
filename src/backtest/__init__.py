"""Backtest-stage utilities for the market research system."""

from src.backtest.config import BacktestPipelineConfig, load_backtest_pipeline_config
from src.backtest.holdings import build_holdings_history
from src.backtest.metrics import (
    build_backtest_summary,
    build_performance_by_period,
    build_risk_metrics_summary,
)
from src.backtest.qc import build_backtest_qc_summary
from src.backtest.returns import build_benchmark_returns, build_portfolio_returns
from src.backtest.trades import build_trade_log

__all__ = [
    "BacktestPipelineConfig",
    "build_backtest_qc_summary",
    "build_backtest_summary",
    "build_benchmark_returns",
    "build_holdings_history",
    "build_performance_by_period",
    "build_portfolio_returns",
    "build_risk_metrics_summary",
    "build_trade_log",
    "load_backtest_pipeline_config",
]
