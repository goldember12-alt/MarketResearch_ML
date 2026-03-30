"""Markdown rendering for benchmark-aware strategy reports."""

from __future__ import annotations

from typing import Any


def _pct(value: Any) -> str:
    """Format a decimal metric as a percentage string when available."""
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def _num(value: Any) -> str:
    """Format a scalar metric compactly when available."""
    if value is None:
        return "n/a"
    return f"{float(value):.3f}"


def render_strategy_report(
    summary: dict[str, Any],
    *,
    strategy_report_path: str,
    registry_path: str,
) -> str:
    """Render the human-readable strategy report markdown."""
    portfolio_net = summary["portfolio_metrics"]["net"]
    portfolio_gross = summary["portfolio_metrics"]["gross"]
    lines = [
        "# Strategy Report",
        "",
        "## Run Status",
        f"- Status: `{summary['status']}`",
        f"- Generated at (UTC): `{summary['generated_at_utc']}`",
        f"- Universe preset: `{summary['universe_preset']}`",
        f"- Signal baseline: `{summary['signal_or_model']}`",
        "",
        "## Method Snapshot",
        f"- Realized date range: `{summary['date_range']['realized_start']}` to `{summary['date_range']['realized_end']}`",
        f"- Rebalance frequency: `{summary['rebalance_frequency']}`",
        f"- Benchmarks: `{', '.join(summary['benchmark_set'])}`",
        f"- Portfolio rules: top `{summary['portfolio_rules']['selected_top_n']}`, `{summary['portfolio_rules']['weighting_scheme']}`, cash policy `{summary['portfolio_rules']['cash_handling_policy']}`",
        f"- Transaction cost: `{summary['transaction_cost_bps']}` bps; slippage: `{summary['slippage_bps']}` bps",
        f"- Holding convention: {summary['portfolio_rules']['holding_period_convention']}",
        "",
        "## Portfolio Summary",
        f"- Net cumulative return: `{_pct(portfolio_net.get('cumulative_return'))}`",
        f"- Net annualized return: `{_pct(portfolio_net.get('annualized_return'))}`",
        f"- Net annualized volatility: `{_pct(portfolio_net.get('annualized_volatility'))}`",
        f"- Net Sharpe ratio: `{_num(portfolio_net.get('sharpe_ratio'))}`",
        f"- Net Sortino ratio: `{_num(portfolio_net.get('sortino_ratio'))}`",
        f"- Net max drawdown: `{_pct(portfolio_net.get('max_drawdown'))}`",
        f"- Hit rate: `{_pct(portfolio_net.get('hit_rate'))}`",
        f"- Average turnover: `{_pct(portfolio_net.get('average_turnover'))}`",
        f"- Gross cumulative return: `{_pct(portfolio_gross.get('cumulative_return'))}`",
        "",
        "## Benchmark Comparison",
    ]

    for comparison in summary["benchmark_comparison"]:
        lines.append(
            "- "
            + (
                f"`{comparison['benchmark']}`: portfolio net cumulative `{_pct(comparison['portfolio_cumulative_return'])}`, "
                f"benchmark cumulative `{_pct(comparison['benchmark_cumulative_return'])}`, "
                f"gap `{_pct(comparison['cumulative_return_gap'])}`, "
                f"winning-month share `{_pct(comparison['winning_month_share'])}`"
            )
        )

    lines.extend(
        [
            "",
            "## Risk Controls",
            *[f"- {item}" for item in summary["risk_controls"]],
            "",
            "## Bias Caveats",
            *[f"- {item}" for item in summary["bias_caveats"]],
            "",
            "## Interpretation",
            summary["interpretation"],
            "",
            "## Artifacts",
            f"- Strategy report: `{strategy_report_path}`",
            f"- Experiment registry append target: `{registry_path}`",
            "",
            "## Next Step",
            f"- {summary['next_step']}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_model_strategy_report(
    summary: dict[str, Any],
    *,
    strategy_report_path: str,
    registry_path: str,
) -> str:
    """Render the human-readable model strategy report markdown."""
    portfolio_net = summary["portfolio_metrics"]["net"]
    portfolio_gross = summary["portfolio_metrics"]["gross"]
    diagnostics = summary["model_diagnostics"]
    oos_metrics = diagnostics["out_of_sample_evaluation"]
    lines = [
        "# Model Strategy Report",
        "",
        "## Run Status",
        f"- Status: `{summary['status']}`",
        f"- Generated at (UTC): `{summary['generated_at_utc']}`",
        f"- Universe preset: `{summary['universe_preset']}`",
        f"- Model: `{summary['signal_or_model']}`",
        "",
        "## Method Snapshot",
        f"- Prediction decision date range: `{summary['date_range']['prediction_decision_start']}` to `{summary['date_range']['prediction_decision_end']}`",
        f"- Realized date range: `{summary['date_range']['realized_start']}` to `{summary['date_range']['realized_end']}`",
        f"- Rebalance frequency: `{summary['rebalance_frequency']}`",
        f"- Benchmarks: `{', '.join(summary['benchmark_set'])}`",
        f"- Portfolio rules: top `{summary['portfolio_rules']['selected_top_n']}`, `{summary['portfolio_rules']['weighting_scheme']}`, cash policy `{summary['portfolio_rules']['cash_handling_policy']}`",
        f"- Transaction cost: `{summary['transaction_cost_bps']}` bps; slippage: `{summary['slippage_bps']}` bps",
        f"- Holding convention: {summary['portfolio_rules']['holding_period_convention']}",
        "",
        "## Model Diagnostics",
        f"- Label definition: `{diagnostics['label_definition']}`",
        f"- Split scheme: `{diagnostics['split_scheme']}`",
        f"- Fold count: `{diagnostics['fold_count']}`",
        f"- Classification threshold: `{diagnostics['classification_threshold']}`",
        f"- Out-of-sample accuracy: `{_pct(oos_metrics.get('accuracy'))}`",
        f"- Out-of-sample ROC AUC: `{_num(oos_metrics.get('roc_auc'))}`",
        f"- Out-of-sample average precision: `{_num(oos_metrics.get('average_precision'))}`",
        "",
        "## Portfolio Summary",
        f"- Net cumulative return: `{_pct(portfolio_net.get('cumulative_return'))}`",
        f"- Net annualized return: `{_pct(portfolio_net.get('annualized_return'))}`",
        f"- Net annualized volatility: `{_pct(portfolio_net.get('annualized_volatility'))}`",
        f"- Net Sharpe ratio: `{_num(portfolio_net.get('sharpe_ratio'))}`",
        f"- Net Sortino ratio: `{_num(portfolio_net.get('sortino_ratio'))}`",
        f"- Net max drawdown: `{_pct(portfolio_net.get('max_drawdown'))}`",
        f"- Hit rate: `{_pct(portfolio_net.get('hit_rate'))}`",
        f"- Average turnover: `{_pct(portfolio_net.get('average_turnover'))}`",
        f"- Gross cumulative return: `{_pct(portfolio_gross.get('cumulative_return'))}`",
        "",
        "## Benchmark Comparison",
    ]

    for comparison in summary["benchmark_comparison"]:
        lines.append(
            "- "
            + (
                f"`{comparison['benchmark']}`: portfolio net cumulative `{_pct(comparison['portfolio_cumulative_return'])}`, "
                f"benchmark cumulative `{_pct(comparison['benchmark_cumulative_return'])}`, "
                f"gap `{_pct(comparison['cumulative_return_gap'])}`, "
                f"winning-month share `{_pct(comparison['winning_month_share'])}`"
            )
        )

    lines.extend(
        [
            "",
            "## Risk Controls",
            *[f"- {item}" for item in summary["risk_controls"]],
            "",
            "## Bias Caveats",
            *[f"- {item}" for item in summary["bias_caveats"]],
            "",
            "## Interpretation",
            summary["interpretation"],
            "",
            "## Artifacts",
            f"- Model strategy report: `{strategy_report_path}`",
            f"- Experiment registry append target: `{registry_path}`",
            "",
            "## Next Step",
            f"- {summary['next_step']}",
        ]
    )
    return "\n".join(lines) + "\n"
