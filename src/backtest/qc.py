"""Validation helpers and QC summaries for monthly backtests."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.backtest.config import BacktestPipelineConfig
from src.data.standardize import assert_unique_keys


def _weight_sum_checks(
    holdings_history: pd.DataFrame, rebalance_summary: pd.DataFrame
) -> dict[str, float]:
    """Validate holdings weights against the rebalance summary."""
    if rebalance_summary.empty:
        return {
            "max_weight_sum_deviation": 0.0,
            "max_cash_weight": 0.0,
            "min_cash_weight": 0.0,
        }

    assert_unique_keys(rebalance_summary, ["rebalance_date"], "rebalance_summary")
    invested_weights = (
        holdings_history.groupby("date", as_index=False)["portfolio_weight"].sum()
        if not holdings_history.empty
        else pd.DataFrame(columns=["date", "portfolio_weight"])
    )
    checks = rebalance_summary.merge(
        invested_weights,
        left_on="rebalance_date",
        right_on="date",
        how="left",
    )
    checks["portfolio_weight"] = checks["portfolio_weight"].fillna(0.0)
    checks["weight_sum_total"] = checks["portfolio_weight"] + checks["cash_weight"]
    checks["weight_sum_deviation"] = (checks["weight_sum_total"] - 1.0).abs()
    return {
        "max_weight_sum_deviation": float(checks["weight_sum_deviation"].max()),
        "max_cash_weight": float(checks["cash_weight"].max()),
        "min_cash_weight": float(checks["cash_weight"].min()),
    }


def build_backtest_qc_summary(
    *,
    config: BacktestPipelineConfig,
    holdings_history: pd.DataFrame,
    rebalance_summary: pd.DataFrame,
    holding_return_details: pd.DataFrame,
    portfolio_returns: pd.DataFrame,
    benchmark_returns: pd.DataFrame,
) -> dict[str, Any]:
    """Build a compact QC summary for the completed backtest stage."""
    if not holdings_history.empty:
        assert_unique_keys(holdings_history, ["date", "ticker"], "holdings_history")
    if not portfolio_returns.empty:
        assert_unique_keys(portfolio_returns, ["date"], "portfolio_returns")
    if not benchmark_returns.empty:
        assert_unique_keys(
            benchmark_returns, ["benchmark_ticker", "date"], "benchmark_returns"
        )

    expected_benchmark_rows = len(portfolio_returns) * len(config.benchmarks.identifiers)
    benchmark_alignment_ok = len(benchmark_returns) == expected_benchmark_rows
    holdings_by_rebalance = (
        holdings_history.groupby("date")["ticker"].nunique() if not holdings_history.empty else pd.Series(dtype="int64")
    )

    missing_realized_return_count = int(
        holding_return_details["missing_realized_return"].sum()
        if "missing_realized_return" in holding_return_details.columns
        else 0
    )
    missing_realized_return_examples: list[dict[str, Any]] = []
    if missing_realized_return_count:
        examples = holding_return_details.loc[
            holding_return_details["missing_realized_return"],
            ["date", "ticker", "holding_period_end"],
        ].head(5)
        missing_realized_return_examples = [
            {
                "formation_date": row["date"].strftime("%Y-%m-%d"),
                "ticker": row["ticker"],
                "realized_date": row["holding_period_end"].strftime("%Y-%m-%d"),
            }
            for row in examples.to_dict("records")
        ]

    return {
        "holdings_row_count": int(len(holdings_history)),
        "rebalance_count": int(len(rebalance_summary)),
        "portfolio_period_count": int(len(portfolio_returns)),
        "benchmark_row_count": int(len(benchmark_returns)),
        "unique_held_ticker_count": int(holdings_history["ticker"].nunique()) if not holdings_history.empty else 0,
        "average_selected_ticker_count": (
            float(holdings_by_rebalance.mean()) if not holdings_by_rebalance.empty else 0.0
        ),
        "max_selected_ticker_count": (
            int(holdings_by_rebalance.max()) if not holdings_by_rebalance.empty else 0
        ),
        "benchmark_alignment_ok": benchmark_alignment_ok,
        "missing_realized_return_policy": "fill_with_zero_and_log",
        "missing_realized_return_count": missing_realized_return_count,
        "missing_realized_return_examples": missing_realized_return_examples,
        **_weight_sum_checks(holdings_history, rebalance_summary),
    }
