"""Structured evaluation summaries derived from backtest artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from src.backtest.config import BacktestPipelineConfig
from src.signals.config import SignalPipelineConfig
from src.utils.config import ProjectConfig


def _metrics_lookup(risk_metrics_summary: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Convert the risk metrics table into a keyed lookup."""
    if risk_metrics_summary.empty:
        return {}
    return {
        str(row["series_id"]): {
            key: (None if pd.isna(value) else value)
            for key, value in row.items()
        }
        for row in risk_metrics_summary.to_dict("records")
    }


def _as_float_or_none(value: Any) -> float | None:
    """Convert pandas-compatible scalars into plain floats or nulls."""
    if pd.isna(value):
        return None
    return float(value)


def _build_benchmark_comparison(
    performance_by_period: pd.DataFrame,
    metrics_by_series: dict[str, dict[str, Any]],
    benchmark_ids: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Summarize portfolio net performance versus each configured benchmark."""
    comparisons: list[dict[str, Any]] = []
    if performance_by_period.empty:
        return comparisons

    for benchmark_id in benchmark_ids:
        benchmark_column = f"benchmark_return__{benchmark_id}"
        if benchmark_column not in performance_by_period.columns:
            continue
        monthly_gap = (
            performance_by_period["portfolio_net_return"] - performance_by_period[benchmark_column]
        )
        benchmark_metrics = metrics_by_series.get(benchmark_id, {})
        portfolio_metrics = metrics_by_series.get("portfolio_net", {})
        comparisons.append(
            {
                "benchmark": benchmark_id,
                "portfolio_cumulative_return": _as_float_or_none(
                    portfolio_metrics.get("cumulative_return")
                ),
                "benchmark_cumulative_return": _as_float_or_none(
                    benchmark_metrics.get("cumulative_return")
                ),
                "cumulative_return_gap": (
                    None
                    if pd.isna(portfolio_metrics.get("cumulative_return"))
                    or pd.isna(benchmark_metrics.get("cumulative_return"))
                    else float(
                        portfolio_metrics["cumulative_return"]
                        - benchmark_metrics["cumulative_return"]
                    )
                ),
                "mean_monthly_return_gap": _as_float_or_none(monthly_gap.mean()),
                "winning_month_share": _as_float_or_none((monthly_gap > 0.0).mean()),
            }
        )
    return comparisons


def _risk_controls() -> list[str]:
    """Return the currently implemented risk controls."""
    return [
        "Predictive features and deterministic signals only use information available through the prior month.",
        "Holdings formed at month-end t earn realized returns at the next month-end t+1.",
        "Transaction costs are explicit and config-driven.",
        "Benchmark comparisons are explicit for SPY, QQQ, and equal_weight_universe.",
        "Duplicate-key, holdings-weight, and benchmark-alignment checks run before reporting.",
    ]


def _bias_caveats() -> list[str]:
    """Return the current known caveats that must accompany reported results."""
    return [
        "Fundamentals are lagged but not truly point-in-time safe, so revised-history bias remains possible.",
        "Current sample data are local deterministic fixtures rather than benchmark-quality research data.",
        "The current history is short, so annualized metrics are unstable and descriptive only.",
        "Cash is assumed to earn 0.0 and transaction costs use a simple linear turnover model.",
    ]


def build_evaluation_summary(
    *,
    project_config: ProjectConfig,
    signal_config: SignalPipelineConfig,
    backtest_config: BacktestPipelineConfig,
    backtest_summary: dict[str, Any],
    portfolio_returns: pd.DataFrame,
    performance_by_period: pd.DataFrame,
    risk_metrics_summary: pd.DataFrame,
) -> dict[str, Any]:
    """Build a report-ready summary from implemented backtest artifacts."""
    metrics_by_series = _metrics_lookup(risk_metrics_summary)
    portfolio_net_metrics = metrics_by_series.get("portfolio_net", {})
    benchmark_comparison = _build_benchmark_comparison(
        performance_by_period,
        metrics_by_series,
        backtest_config.benchmarks.identifiers,
    )

    realized_period_count = int(len(portfolio_returns))
    positive_periods = (
        int((portfolio_returns["portfolio_net_return"] > 0.0).sum())
        if not portfolio_returns.empty
        else 0
    )
    cumulative_return = portfolio_net_metrics.get("cumulative_return")
    if cumulative_return is None:
        portfolio_result_text = (
            f"Across {realized_period_count} realized monthly periods, the portfolio net cumulative "
            "return was unavailable. "
        )
    else:
        portfolio_result_text = (
            f"Across {realized_period_count} realized monthly periods, the portfolio net cumulative "
            f"return was {cumulative_return:.2%}. "
        )
    interpretation = "This run is exploratory. " + portfolio_result_text + (
        "These results should not be treated as benchmark-quality evidence because the sample is short, "
        "the data are local fixtures, and fundamentals are not point-in-time safe."
    )

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Summarize the deterministic monthly backtest baseline and log a benchmark-aware exploratory run.",
        "status": "exploratory_completed",
        "universe_preset": project_config.universe.preset_name,
        "benchmark_set": list(backtest_config.benchmarks.identifiers),
        "feature_set": list(signal_config.features.all_features),
        "signal_or_model": signal_config.strategy.name,
        "date_range": {
            "formation_start": backtest_summary.get("formation_start_date"),
            "formation_end": backtest_summary.get("formation_end_date"),
            "realized_start": backtest_summary.get("realized_start_date"),
            "realized_end": backtest_summary.get("realized_end_date"),
        },
        "portfolio_rules": {
            "selection_method": backtest_config.portfolio.selection_method,
            "selected_top_n": backtest_config.portfolio.selected_top_n,
            "weighting_scheme": backtest_config.portfolio.weighting_scheme,
            "max_weight": backtest_config.portfolio.max_weight,
            "cash_handling_policy": backtest_config.portfolio.cash_handling_policy,
            "holding_period_convention": backtest_summary.get("holding_period_convention"),
        },
        "rebalance_frequency": backtest_config.rebalancing.frequency,
        "transaction_cost_bps": backtest_config.costs.transaction_cost_bps,
        "slippage_bps": backtest_config.costs.slippage_bps,
        "portfolio_metrics": {
            "gross": metrics_by_series.get("portfolio_gross", {}),
            "net": portfolio_net_metrics,
        },
        "benchmark_metrics": {
            benchmark_id: metrics_by_series.get(benchmark_id, {})
            for benchmark_id in backtest_config.benchmarks.identifiers
        },
        "benchmark_comparison": benchmark_comparison,
        "sample_characteristics": {
            "realized_period_count": realized_period_count,
            "positive_net_month_count": positive_periods,
            "positive_net_month_share": (
                None if realized_period_count == 0 else positive_periods / realized_period_count
            ),
            "average_turnover": _as_float_or_none(portfolio_returns["turnover"].mean())
            if not portfolio_returns.empty
            else None,
            "max_turnover": _as_float_or_none(portfolio_returns["turnover"].max())
            if not portfolio_returns.empty
            else None,
        },
        "risk_controls": _risk_controls(),
        "bias_caveats": _bias_caveats(),
        "qc_summary": backtest_summary.get("qc", {}),
        "interpretation": interpretation,
        "next_step": "Implement chronology-safe modeling baselines and compare them against the deterministic signal baseline.",
    }
