"""Trade-log construction and turnover summaries for monthly rebalances."""

from __future__ import annotations

import pandas as pd

from src.data.standardize import assert_unique_keys


def build_trade_log(
    holdings_history: pd.DataFrame, rebalance_summary: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare consecutive holdings snapshots and produce trade-level changes."""
    if not rebalance_summary.empty:
        assert_unique_keys(rebalance_summary, ["rebalance_date"], "rebalance_summary")

    if holdings_history.empty:
        turnover_summary = rebalance_summary[["rebalance_date"]].copy()
        turnover_summary["gross_buy_weight"] = 0.0
        turnover_summary["gross_sell_weight"] = 0.0
        turnover_summary["gross_trade_weight"] = 0.0
        turnover_summary["turnover"] = 0.0
        return pd.DataFrame(), turnover_summary

    assert_unique_keys(holdings_history, ["date", "ticker"], "holdings_history")

    rebalance_dates = rebalance_summary["rebalance_date"].sort_values().tolist()
    trade_frames: list[pd.DataFrame] = []
    previous_snapshot = pd.DataFrame(columns=["ticker", "portfolio_weight"])
    previous_date = pd.NaT

    for rebalance_date in rebalance_dates:
        current_snapshot = holdings_history.loc[
            holdings_history["date"] == rebalance_date, ["ticker", "portfolio_weight"]
        ].copy()

        merged = previous_snapshot.merge(
            current_snapshot,
            on="ticker",
            how="outer",
            suffixes=("_previous", "_target"),
        )
        merged["portfolio_weight_previous"] = (
            merged["portfolio_weight_previous"].fillna(0.0).astype(float)
        )
        merged["portfolio_weight_target"] = (
            merged["portfolio_weight_target"].fillna(0.0).astype(float)
        )
        merged["weight_change"] = (
            merged["portfolio_weight_target"] - merged["portfolio_weight_previous"]
        )
        merged = merged.loc[merged["weight_change"] != 0.0].copy()
        if merged.empty:
            previous_snapshot = current_snapshot
            previous_date = rebalance_date
            continue

        merged["rebalance_date"] = rebalance_date
        merged["previous_rebalance_date"] = previous_date
        merged["buy_weight"] = merged["weight_change"].clip(lower=0.0)
        merged["sell_weight"] = (-merged["weight_change"]).clip(lower=0.0)
        merged["abs_weight_change"] = merged["weight_change"].abs()
        merged["trade_type"] = "rebalance"
        merged.loc[
            (merged["portfolio_weight_previous"] > 0.0)
            & (merged["portfolio_weight_target"] > merged["portfolio_weight_previous"]),
            "trade_type",
        ] = "increase"
        merged.loc[
            (merged["portfolio_weight_previous"] > 0.0)
            & (merged["portfolio_weight_target"] < merged["portfolio_weight_previous"])
            & (merged["portfolio_weight_target"] > 0.0),
            "trade_type",
        ] = "decrease"
        merged.loc[
            (merged["portfolio_weight_previous"] == 0.0)
            & (merged["portfolio_weight_target"] > 0.0),
            "trade_type",
        ] = "entry"
        merged.loc[
            (merged["portfolio_weight_previous"] > 0.0)
            & (merged["portfolio_weight_target"] == 0.0),
            "trade_type",
        ] = "exit"

        trade_frames.append(
            merged[
                [
                    "rebalance_date",
                    "previous_rebalance_date",
                    "ticker",
                    "trade_type",
                    "portfolio_weight_previous",
                    "portfolio_weight_target",
                    "weight_change",
                    "abs_weight_change",
                    "buy_weight",
                    "sell_weight",
                ]
            ].sort_values(["rebalance_date", "ticker"])
        )
        previous_snapshot = current_snapshot
        previous_date = rebalance_date

    trade_log = (
        pd.concat(trade_frames, ignore_index=True)
        if trade_frames
        else pd.DataFrame(
            columns=[
                "rebalance_date",
                "previous_rebalance_date",
                "ticker",
                "trade_type",
                "portfolio_weight_previous",
                "portfolio_weight_target",
                "weight_change",
                "abs_weight_change",
                "buy_weight",
                "sell_weight",
            ]
        )
    )
    if not trade_log.empty:
        assert_unique_keys(trade_log, ["rebalance_date", "ticker"], "trade_log")

    turnover_summary = rebalance_summary[["rebalance_date"]].copy()
    if trade_log.empty:
        turnover_summary["gross_buy_weight"] = 0.0
        turnover_summary["gross_sell_weight"] = 0.0
        turnover_summary["gross_trade_weight"] = 0.0
        turnover_summary["turnover"] = 0.0
        return trade_log, turnover_summary

    aggregated = (
        trade_log.groupby("rebalance_date", as_index=False)
        .agg(
            gross_buy_weight=("buy_weight", "sum"),
            gross_sell_weight=("sell_weight", "sum"),
            gross_trade_weight=("abs_weight_change", "sum"),
        )
        .sort_values("rebalance_date")
    )
    turnover_summary = turnover_summary.merge(aggregated, on="rebalance_date", how="left")
    for column in ("gross_buy_weight", "gross_sell_weight", "gross_trade_weight"):
        turnover_summary[column] = turnover_summary[column].fillna(0.0)
    turnover_summary["turnover"] = turnover_summary[
        ["gross_buy_weight", "gross_sell_weight"]
    ].max(axis=1)
    return trade_log, turnover_summary
