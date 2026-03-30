"""Holdings construction for deterministic monthly backtests."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.backtest.config import BacktestPipelineConfig
from src.data.standardize import assert_unique_keys


@dataclass(frozen=True)
class RebalanceSnapshot:
    """Summary of a single rebalance month's target allocation."""

    date: pd.Timestamp
    holding_period_end: pd.Timestamp | pd.NaT
    selected_count: int
    invested_weight: float
    cash_weight: float


def _resolve_selected_rows(
    signal_rankings: pd.DataFrame, *, selected_top_n: int
) -> pd.Series:
    """Resolve the selected-name mask from the ranking artifact."""
    if "selected_top_n" in signal_rankings.columns:
        selected_mask = signal_rankings["selected_top_n"].fillna(False).astype(bool)
        if "score_rank" in signal_rankings.columns:
            derived_mask = signal_rankings["score_rank"].notna() & (
                signal_rankings["score_rank"] <= selected_top_n
            )
            if bool((selected_mask != derived_mask).any()):
                raise ValueError(
                    "signal_rankings selected_top_n does not match the configured backtest top_n. "
                    "Regenerate signals or align config/backtest.yaml."
                )
        return selected_mask

    if "score_rank" not in signal_rankings.columns:
        raise ValueError(
            "signal_rankings must contain either 'selected_top_n' or 'score_rank'."
        )
    return signal_rankings["score_rank"].notna() & (
        signal_rankings["score_rank"] <= selected_top_n
    )


def _allocate_weights(
    selected_count: int,
    *,
    selected_top_n: int,
    weighting_scheme: str,
    max_weight: float,
    cash_handling_policy: str,
) -> tuple[float, float]:
    """Return the per-name target weight and residual cash weight."""
    if selected_count == 0:
        return 0.0, 1.0

    if cash_handling_policy == "redistribute":
        base_weight = 1.0 / selected_count
    elif cash_handling_policy == "hold_cash":
        base_weight = 1.0 / selected_top_n
    else:
        raise ValueError(f"Unsupported cash handling policy: {cash_handling_policy!r}")

    if weighting_scheme == "equal_weight":
        per_name_weight = base_weight
    elif weighting_scheme == "capped_weight":
        per_name_weight = min(base_weight, max_weight)
    else:
        raise ValueError(f"Unsupported weighting scheme: {weighting_scheme!r}")

    invested_weight = per_name_weight * selected_count
    if cash_handling_policy == "redistribute" and invested_weight < 1.0 - 1e-12:
        raise ValueError(
            "Configured capped weights cannot fully invest the selected portfolio under "
            "cash_handling_policy='redistribute'. Increase max_position_weight, reduce top_n, "
            "or switch to cash_handling_policy='hold_cash'."
        )

    return per_name_weight, max(0.0, 1.0 - invested_weight)


def _resolve_holding_period_end(
    month_frame: pd.DataFrame,
    *,
    rebalance_date: pd.Timestamp,
    next_dates: pd.Series,
) -> pd.Timestamp | pd.NaT:
    """Resolve the realized period end for one rebalance date."""
    explicit_column = None
    for candidate in ("holding_period_end", "realized_label_date"):
        if candidate in month_frame.columns:
            explicit_column = candidate
            break

    if explicit_column is None:
        return next_dates.loc[rebalance_date]

    explicit_values = pd.to_datetime(month_frame[explicit_column]).dropna().drop_duplicates()
    if explicit_values.empty:
        return pd.NaT
    if len(explicit_values) != 1:
        raise ValueError(
            "signal_rankings contains multiple realized period end values within a rebalance date. "
            f"Date={rebalance_date.strftime('%Y-%m-%d')}, values={explicit_values.dt.strftime('%Y-%m-%d').tolist()}"
        )
    return pd.Timestamp(explicit_values.iloc[0])


def build_holdings_history(
    signal_rankings: pd.DataFrame, config: BacktestPipelineConfig
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build holdings history from deterministic monthly signal selections."""
    assert_unique_keys(signal_rankings, ["ticker", "date"], "signal_rankings")
    rankings = signal_rankings.copy()
    rankings["date"] = pd.to_datetime(rankings["date"])
    rankings = rankings.sort_values(["date", "ticker"]).reset_index(drop=True)

    rankings["selected_for_backtest"] = _resolve_selected_rows(
        rankings, selected_top_n=config.portfolio.selected_top_n
    )

    rebalance_dates = pd.Index(rankings["date"]).drop_duplicates().sort_values()
    next_dates = pd.Series(rebalance_dates[1:].tolist() + [pd.NaT], index=rebalance_dates)

    holdings_frames: list[pd.DataFrame] = []
    summary_rows: list[RebalanceSnapshot] = []

    for rebalance_date in rebalance_dates:
        month_frame = rankings.loc[rankings["date"] == rebalance_date].copy()
        month_selected = rankings.loc[
            (rankings["date"] == rebalance_date) & rankings["selected_for_backtest"]
        ].copy()
        selected_count = int(len(month_selected))
        per_name_weight, cash_weight = _allocate_weights(
            selected_count,
            selected_top_n=config.portfolio.selected_top_n,
            weighting_scheme=config.portfolio.weighting_scheme,
            max_weight=config.portfolio.max_weight,
            cash_handling_policy=config.portfolio.cash_handling_policy,
        )
        invested_weight = float(per_name_weight * selected_count)
        holding_period_end = _resolve_holding_period_end(
            month_frame,
            rebalance_date=pd.Timestamp(rebalance_date),
            next_dates=next_dates,
        )
        summary_rows.append(
            RebalanceSnapshot(
                date=pd.Timestamp(rebalance_date),
                holding_period_end=holding_period_end,
                selected_count=selected_count,
                invested_weight=invested_weight,
                cash_weight=float(cash_weight),
            )
        )

        if month_selected.empty:
            continue

        month_selected["portfolio_weight"] = float(per_name_weight)
        month_selected["holding_period_start"] = pd.Timestamp(rebalance_date)
        month_selected["holding_period_end"] = holding_period_end
        month_selected["signal_rank"] = month_selected["score_rank"]
        month_selected["selected_name_count"] = selected_count
        month_selected["configured_top_n"] = config.portfolio.selected_top_n
        month_selected["target_weight_sum"] = invested_weight
        month_selected["cash_weight"] = float(cash_weight)

        holdings_frames.append(
            month_selected[
                [
                    "date",
                    "ticker",
                    "portfolio_weight",
                    "signal_rank",
                    "composite_score",
                    "holding_period_start",
                    "holding_period_end",
                    "selected_name_count",
                    "configured_top_n",
                    "target_weight_sum",
                    "cash_weight",
                    "sector",
                    "industry",
                ]
            ].sort_values(["date", "signal_rank", "ticker"])
        )

    holdings_history = (
        pd.concat(holdings_frames, ignore_index=True)
        if holdings_frames
        else pd.DataFrame(
            columns=[
                "date",
                "ticker",
                "portfolio_weight",
                "signal_rank",
                "composite_score",
                "holding_period_start",
                "holding_period_end",
                "selected_name_count",
                "configured_top_n",
                "target_weight_sum",
                "cash_weight",
                "sector",
                "industry",
            ]
        )
    )
    rebalance_summary = pd.DataFrame(summary_rows).rename(
        columns={"date": "rebalance_date", "holding_period_end": "realized_date"}
    )

    if not holdings_history.empty:
        holdings_history["date"] = pd.to_datetime(holdings_history["date"])
        holdings_history["holding_period_start"] = pd.to_datetime(
            holdings_history["holding_period_start"]
        )
        holdings_history["holding_period_end"] = pd.to_datetime(
            holdings_history["holding_period_end"]
        )
        assert_unique_keys(holdings_history, ["date", "ticker"], "holdings_history")

    return holdings_history, rebalance_summary
