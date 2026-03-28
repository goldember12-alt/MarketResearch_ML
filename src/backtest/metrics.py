"""Performance and risk metric helpers for deterministic monthly backtests."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.backtest.config import BacktestPipelineConfig


PERIODS_PER_YEAR = 12.0


def compute_max_drawdown(returns: pd.Series) -> float:
    """Compute the maximum drawdown from a monthly return series."""
    if returns.empty:
        return float("nan")
    wealth = (1.0 + returns.fillna(0.0)).cumprod()
    drawdown = wealth / wealth.cummax() - 1.0
    return float(drawdown.min())


def _json_safe_value(value: Any) -> Any:
    """Convert pandas and NumPy missing values into JSON-safe nulls."""
    if pd.isna(value):
        return None
    return value


def _annualized_return(returns: pd.Series) -> float:
    """Compute annualized compounded return from monthly returns."""
    if returns.empty:
        return float("nan")
    cumulative_growth = float((1.0 + returns).prod())
    if cumulative_growth <= 0.0:
        return float("nan")
    return float(cumulative_growth ** (PERIODS_PER_YEAR / len(returns)) - 1.0)


def _annualized_volatility(returns: pd.Series) -> float:
    """Compute annualized monthly return volatility."""
    if len(returns) < 2:
        return float("nan")
    return float(returns.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR))


def _sharpe_ratio(returns: pd.Series) -> float:
    """Compute the zero-rate Sharpe ratio from monthly returns."""
    volatility = _annualized_volatility(returns)
    if not np.isfinite(volatility) or volatility == 0.0:
        return float("nan")
    return float(returns.mean() / returns.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR))


def _sortino_ratio(returns: pd.Series) -> float:
    """Compute the zero-rate Sortino ratio from monthly returns."""
    if returns.empty:
        return float("nan")
    downside = returns.clip(upper=0.0)
    downside_deviation = float(np.sqrt(np.mean(np.square(downside))) * np.sqrt(PERIODS_PER_YEAR))
    if downside_deviation == 0.0:
        return float("nan")
    return float((returns.mean() * PERIODS_PER_YEAR) / downside_deviation)


def summarize_return_series(
    returns: pd.Series,
    *,
    turnover: pd.Series | None = None,
) -> dict[str, float | int]:
    """Compute the canonical risk and performance metrics for a monthly series."""
    clean = returns.dropna().astype(float)
    if clean.empty:
        return {
            "period_count": 0,
            "cumulative_return": float("nan"),
            "annualized_return": float("nan"),
            "annualized_volatility": float("nan"),
            "sharpe_ratio": float("nan"),
            "sortino_ratio": float("nan"),
            "max_drawdown": float("nan"),
            "hit_rate": float("nan"),
            "average_turnover": float("nan"),
            "total_turnover": float("nan"),
        }

    summary: dict[str, float | int] = {
        "period_count": int(len(clean)),
        "cumulative_return": float((1.0 + clean).prod() - 1.0),
        "annualized_return": _annualized_return(clean),
        "annualized_volatility": _annualized_volatility(clean),
        "sharpe_ratio": _sharpe_ratio(clean),
        "sortino_ratio": _sortino_ratio(clean),
        "max_drawdown": compute_max_drawdown(clean),
        "hit_rate": float((clean > 0.0).mean()),
        "average_turnover": float("nan"),
        "total_turnover": float("nan"),
    }
    if turnover is not None:
        turnover_clean = turnover.dropna().astype(float)
        if not turnover_clean.empty:
            summary["average_turnover"] = float(turnover_clean.mean())
            summary["total_turnover"] = float(turnover_clean.sum())
    return summary


def build_performance_by_period(
    portfolio_returns: pd.DataFrame, benchmark_returns: pd.DataFrame
) -> pd.DataFrame:
    """Build a period-level comparison table for the strategy and benchmarks."""
    performance = portfolio_returns.copy()
    if benchmark_returns.empty:
        return performance

    benchmark_return_wide = (
        benchmark_returns.pivot(index="date", columns="benchmark_ticker", values="benchmark_return")
        .sort_index()
        .add_prefix("benchmark_return__")
        .reset_index()
    )
    benchmark_cumulative_wide = (
        benchmark_returns.pivot(index="date", columns="benchmark_ticker", values="cumulative_return")
        .sort_index()
        .add_prefix("benchmark_cumulative_return__")
        .reset_index()
    )
    performance = performance.merge(benchmark_return_wide, on="date", how="left")
    performance = performance.merge(benchmark_cumulative_wide, on="date", how="left")
    return performance


def build_risk_metrics_summary(
    portfolio_returns: pd.DataFrame, benchmark_returns: pd.DataFrame
) -> pd.DataFrame:
    """Compile risk metrics for portfolio gross/net series and each benchmark."""
    rows: list[dict[str, Any]] = []
    if not portfolio_returns.empty:
        for series_id, column_name in (
            ("portfolio_gross", "portfolio_gross_return"),
            ("portfolio_net", "portfolio_net_return"),
        ):
            rows.append(
                {
                    "series_id": series_id,
                    "series_type": "portfolio",
                    **summarize_return_series(
                        portfolio_returns[column_name],
                        turnover=portfolio_returns["turnover"] if series_id == "portfolio_net" else None,
                    ),
                }
            )

    if not benchmark_returns.empty:
        for benchmark_ticker, benchmark_frame in benchmark_returns.groupby("benchmark_ticker", sort=True):
            rows.append(
                {
                    "series_id": str(benchmark_ticker),
                    "series_type": "benchmark",
                    **summarize_return_series(benchmark_frame["benchmark_return"]),
                }
            )

    return pd.DataFrame(rows)


def build_backtest_summary(
    config: BacktestPipelineConfig,
    portfolio_returns: pd.DataFrame,
    benchmark_returns: pd.DataFrame,
    risk_metrics_summary: pd.DataFrame,
    qc_summary: dict[str, Any],
) -> dict[str, Any]:
    """Build the JSON summary artifact for the backtest stage."""
    metrics_by_series: dict[str, dict[str, Any]] = {}
    if not risk_metrics_summary.empty:
        for row in risk_metrics_summary.to_dict("records"):
            metrics_by_series[str(row["series_id"])] = {
                key: _json_safe_value(value)
                for key, value in row.items()
                if key not in {"series_id", "series_type"}
            }

    formation_dates = (
        portfolio_returns["formation_date"]
        if not portfolio_returns.empty
        else pd.Series(dtype="datetime64[ns]")
    )
    realized_dates = (
        portfolio_returns["date"] if not portfolio_returns.empty else pd.Series(dtype="datetime64[ns]")
    )

    return {
        "selection_method": config.portfolio.selection_method,
        "selected_top_n": config.portfolio.selected_top_n,
        "weighting_scheme": config.portfolio.weighting_scheme,
        "max_weight": config.portfolio.max_weight,
        "cash_handling_policy": config.portfolio.cash_handling_policy,
        "rebalance_frequency": config.rebalancing.frequency,
        "decision_anchor": config.rebalancing.decision_anchor,
        "trade_timing": config.rebalancing.trade_timing,
        "holding_period_convention": (
            "Signals observed at month-end t form holdings on date t. "
            "Those holdings earn the realized security and benchmark monthly returns "
            "recorded at the next month-end t+1."
        ),
        "transaction_cost_bps": config.costs.transaction_cost_bps,
        "slippage_bps": config.costs.slippage_bps,
        "benchmark_identifiers": list(config.benchmarks.identifiers),
        "formation_start_date": (
            None if formation_dates.empty else formation_dates.min().strftime("%Y-%m-%d")
        ),
        "formation_end_date": (
            None if formation_dates.empty else formation_dates.max().strftime("%Y-%m-%d")
        ),
        "realized_start_date": (
            None if realized_dates.empty else realized_dates.min().strftime("%Y-%m-%d")
        ),
        "realized_end_date": (
            None if realized_dates.empty else realized_dates.max().strftime("%Y-%m-%d")
        ),
        "portfolio_period_count": int(len(portfolio_returns)),
        "benchmark_period_count": int(len(benchmark_returns)),
        "metrics_by_series": metrics_by_series,
        "qc": qc_summary,
    }
