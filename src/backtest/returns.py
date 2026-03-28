"""Return alignment and benchmark comparison logic for monthly backtests."""

from __future__ import annotations

import pandas as pd

from src.backtest.config import BacktestPipelineConfig
from src.data.standardize import assert_unique_keys


def build_portfolio_returns(
    holdings_history: pd.DataFrame,
    rebalance_summary: pd.DataFrame,
    monthly_panel: pd.DataFrame,
    turnover_summary: pd.DataFrame,
    config: BacktestPipelineConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute portfolio returns using holdings formed at t and returns realized at t+1."""
    assert_unique_keys(monthly_panel, ["ticker", "date"], "monthly_panel")
    assert_unique_keys(rebalance_summary, ["rebalance_date"], "rebalance_summary")
    assert_unique_keys(turnover_summary, ["rebalance_date"], "turnover_summary")

    returns_source = monthly_panel[["ticker", "date", "monthly_return"]].copy()
    returns_source["date"] = pd.to_datetime(returns_source["date"])

    aligned_holdings = holdings_history.copy()
    if aligned_holdings.empty:
        aligned_holdings = pd.DataFrame(
            columns=[
                "date",
                "ticker",
                "portfolio_weight",
                "holding_period_end",
                "selected_name_count",
                "target_weight_sum",
                "cash_weight",
            ]
        )
    else:
        aligned_holdings["holding_period_end"] = pd.to_datetime(
            aligned_holdings["holding_period_end"]
        )

    holding_return_details = aligned_holdings.merge(
        returns_source.rename(
            columns={
                "date": "realized_date",
                "monthly_return": "security_monthly_return",
            }
        ),
        left_on=["ticker", "holding_period_end"],
        right_on=["ticker", "realized_date"],
        how="left",
    )
    holding_return_details["missing_realized_return"] = (
        holding_return_details["holding_period_end"].notna()
        & holding_return_details["security_monthly_return"].isna()
    )
    holding_return_details["security_monthly_return_filled"] = holding_return_details[
        "security_monthly_return"
    ].fillna(0.0)
    holding_return_details["gross_return_contribution"] = (
        holding_return_details["portfolio_weight"]
        * holding_return_details["security_monthly_return_filled"]
    )

    period_frame = rebalance_summary.copy()
    period_frame["rebalance_date"] = pd.to_datetime(period_frame["rebalance_date"])
    period_frame["realized_date"] = pd.to_datetime(period_frame["realized_date"])
    period_frame = period_frame.loc[period_frame["realized_date"].notna()].copy()
    if period_frame.empty:
        return pd.DataFrame(), holding_return_details

    contributions = (
        holding_return_details.loc[holding_return_details["holding_period_end"].notna()]
        .groupby("date", as_index=False)
        .agg(
            holding_count=("ticker", "count"),
            missing_security_return_count=("missing_realized_return", "sum"),
            portfolio_gross_return=("gross_return_contribution", "sum"),
        )
        .rename(columns={"date": "rebalance_date"})
    )
    portfolio_returns = period_frame.merge(contributions, on="rebalance_date", how="left")
    portfolio_returns = portfolio_returns.merge(turnover_summary, on="rebalance_date", how="left")

    fill_defaults = {
        "holding_count": 0,
        "missing_security_return_count": 0,
        "portfolio_gross_return": 0.0,
        "gross_buy_weight": 0.0,
        "gross_sell_weight": 0.0,
        "gross_trade_weight": 0.0,
        "turnover": 0.0,
    }
    for column, default in fill_defaults.items():
        portfolio_returns[column] = portfolio_returns[column].fillna(default)

    portfolio_returns["transaction_cost_rate"] = config.costs.total_cost_rate
    portfolio_returns["transaction_cost"] = (
        portfolio_returns["turnover"] * portfolio_returns["transaction_cost_rate"]
    )
    portfolio_returns["portfolio_net_return"] = (
        portfolio_returns["portfolio_gross_return"] - portfolio_returns["transaction_cost"]
    )
    portfolio_returns = portfolio_returns.rename(
        columns={"rebalance_date": "formation_date", "realized_date": "date"}
    ).sort_values("date")
    portfolio_returns["cumulative_gross_return"] = (
        1.0 + portfolio_returns["portfolio_gross_return"]
    ).cumprod() - 1.0
    portfolio_returns["cumulative_net_return"] = (
        1.0 + portfolio_returns["portfolio_net_return"]
    ).cumprod() - 1.0
    portfolio_returns = portfolio_returns[
        [
            "date",
            "formation_date",
            "holding_count",
            "selected_count",
            "invested_weight",
            "cash_weight",
            "gross_buy_weight",
            "gross_sell_weight",
            "gross_trade_weight",
            "turnover",
            "missing_security_return_count",
            "portfolio_gross_return",
            "transaction_cost_rate",
            "transaction_cost",
            "portfolio_net_return",
            "cumulative_gross_return",
            "cumulative_net_return",
        ]
    ].rename(columns={"selected_count": "selected_name_count"})
    return portfolio_returns.reset_index(drop=True), holding_return_details.reset_index(drop=True)


def build_benchmark_returns(
    benchmarks_monthly: pd.DataFrame,
    portfolio_returns: pd.DataFrame,
    config: BacktestPipelineConfig,
) -> pd.DataFrame:
    """Align configured benchmarks to the realized portfolio return dates."""
    assert_unique_keys(benchmarks_monthly, ["benchmark_ticker", "date"], "benchmarks_monthly")
    if portfolio_returns.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "formation_date",
                "benchmark_ticker",
                "benchmark_return",
                "cumulative_return",
            ]
        )

    portfolio_dates = portfolio_returns[["date", "formation_date"]].copy()
    benchmark_frames: list[pd.DataFrame] = []
    for benchmark_id in config.benchmarks.identifiers:
        benchmark_series = benchmarks_monthly.loc[
            benchmarks_monthly["benchmark_ticker"] == benchmark_id,
            ["date", "monthly_return"],
        ].copy()
        aligned = portfolio_dates.merge(benchmark_series, on="date", how="left")
        if aligned["monthly_return"].isna().any():
            missing_dates = aligned.loc[aligned["monthly_return"].isna(), "date"].dt.strftime(
                "%Y-%m-%d"
            )
            raise ValueError(
                f"benchmarks_monthly is missing {benchmark_id!r} for dates: {missing_dates.tolist()}"
            )
        aligned["benchmark_ticker"] = benchmark_id
        aligned = aligned.rename(columns={"monthly_return": "benchmark_return"})
        aligned["cumulative_return"] = (1.0 + aligned["benchmark_return"]).cumprod() - 1.0
        benchmark_frames.append(aligned)

    benchmark_returns = pd.concat(benchmark_frames, ignore_index=True)
    benchmark_returns = benchmark_returns[
        ["date", "formation_date", "benchmark_ticker", "benchmark_return", "cumulative_return"]
    ].sort_values(["benchmark_ticker", "date"])
    assert_unique_keys(benchmark_returns, ["benchmark_ticker", "date"], "benchmark_returns")
    return benchmark_returns.reset_index(drop=True)
