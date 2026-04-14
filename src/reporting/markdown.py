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


def _format_raw_dataset_overview(dataset_name: str, dataset_overview: dict[str, Any]) -> str:
    """Render one compact raw-dataset provenance line for markdown reports."""
    selected_files = dataset_overview.get("selected_file_names", [])
    observed_date_columns = dataset_overview.get("observed_date_columns", [])
    selected_files_text = ", ".join(str(name) for name in selected_files) if selected_files else "n/a"
    observed_date_columns_text = (
        ", ".join(str(name) for name in observed_date_columns) if observed_date_columns else "n/a"
    )
    return (
        f"Raw dataset provenance `{dataset_name}`: selected input "
        f"`{dataset_overview.get('selected_source_kind')}`, broader local raw on disk "
        f"`{dataset_overview.get('broader_local_raw_available_on_disk')}`, "
        f"research-scale fallback triggered "
        f"`{dataset_overview.get('seeded_sample_fallback_used_in_run')}`, files "
        f"`{dataset_overview.get('selected_file_count')}`, raw rows "
        f"`{dataset_overview.get('observed_total_row_count')}`, raw date columns "
        f"`{observed_date_columns_text}`, raw span "
        f"`{dataset_overview.get('observed_min_date')}` to "
        f"`{dataset_overview.get('observed_max_date')}`, selected files "
        f"`{selected_files_text}`"
    )


def _format_selected_input_profile(profile: Any) -> str:
    """Convert the run-level raw-input profile into clearer report text."""
    profile_map = {
        "seeded_sample_only": "seeded sample only",
        "broader_local_raw_only": "broader local raw only",
        "mixed_selected_inputs": "mixed seeded sample and broader local raw",
        "no_selection_recorded": "no raw selection recorded",
    }
    return profile_map.get(str(profile), str(profile))


def _format_dataset_list(dataset_names: list[Any]) -> str:
    """Render a dataset-name list compactly for markdown."""
    if not dataset_names:
        return "none"
    return ", ".join(f"`{dataset_name}`" for dataset_name in dataset_names)


def _build_raw_selection_note(raw_data_selection: dict[str, Any]) -> str | None:
    """Render a short note that separates on-disk availability from run-selected inputs."""
    broader_datasets = raw_data_selection.get("datasets_with_broader_local_raw_available", [])
    selected_seeded = raw_data_selection.get("uses_only_seeded_sample_inputs")
    selected_broader = raw_data_selection.get("uses_any_broader_local_raw_inputs")
    fallback_datasets = raw_data_selection.get("datasets_using_seeded_sample_fallback", [])

    if selected_seeded and broader_datasets:
        return (
            "Broader local raw files were present on disk for "
            f"{_format_dataset_list(broader_datasets)}, but this run still selected seeded "
            "sample inputs only."
        )
    if fallback_datasets:
        return (
            "This run triggered research-scale seeded fallback for "
            f"{_format_dataset_list(fallback_datasets)} because broader local raw files were "
            "not selected for those datasets."
        )
    if selected_broader and raw_data_selection.get("datasets_using_seeded_sample_inputs"):
        return (
            "This run used a mixed raw-input selection across datasets: "
            f"seeded sample for {_format_dataset_list(raw_data_selection.get('datasets_using_seeded_sample_inputs', []))} "
            f"and broader local raw for {_format_dataset_list(raw_data_selection.get('datasets_using_broader_local_raw_inputs', []))}."
        )
    return None


def _render_fold_diagnostics(fold_diagnostics: dict[str, Any]) -> list[str]:
    """Render the fold-coverage block for the model strategy report."""
    lines = [
        "## Fold Coverage",
        f"- Held-out decision date range: `{fold_diagnostics.get('decision_start')}` to `{fold_diagnostics.get('decision_end')}`",
        f"- Held-out realized date range: `{fold_diagnostics.get('realized_start')}` to `{fold_diagnostics.get('realized_end')}`",
        f"- Held-out decision month count: `{fold_diagnostics.get('heldout_decision_month_count')}`",
        f"- Held-out realized month count: `{fold_diagnostics.get('heldout_realized_month_count')}`",
        f"- Held-out unique ticker count: `{fold_diagnostics.get('heldout_unique_ticker_count')}`",
        f"- Held-out row count: `{fold_diagnostics.get('heldout_row_count')}`",
    ]
    for fold in fold_diagnostics.get("folds", []):
        lines.append(
            "- "
            + (
                f"`{fold['fold_id']}`: decision `{fold['decision_start']}` to `{fold['decision_end']}`, "
                f"realized `{fold['realized_start']}` to `{fold['realized_end']}`, "
                f"held-out rows `{fold['heldout_row_count']}`, "
                f"model accuracy `{_pct(fold['model_test_accuracy'])}`, "
                f"deterministic accuracy `{_pct(fold['deterministic_test_accuracy'])}`, "
                f"model ROC AUC `{_num(fold['model_test_roc_auc'])}`, "
                f"deterministic ROC AUC `{_num(fold['deterministic_test_roc_auc'])}`"
            )
        )
    return lines


def _render_overlap_comparison(
    comparison: dict[str, Any],
    convention: dict[str, Any],
) -> list[str]:
    """Render the overlap-aware deterministic-vs-model comparison block."""
    if not comparison.get("available"):
        return [
            "## Deterministic Baseline Overlap Comparison",
            "- No overlapping realized dates were available between the deterministic and model-driven backtests.",
        ]

    metrics = comparison["comparison_metrics"]
    model_overlap = comparison["model_metrics_on_overlap"]
    deterministic_overlap = comparison["deterministic_metrics_on_overlap"]
    lines = [
        "## Deterministic Baseline Overlap Comparison",
        f"- Alignment convention: `{convention['join_method']}` on `{convention['aligned_on']}` using `{convention['portfolio_return_series']}` only",
        f"- Overlap realized date range: `{comparison['realized_start']}` to `{comparison['realized_end']}` across `{comparison['overlap_period_count']}` months",
        f"- Model overlap cumulative return: `{_pct(model_overlap.get('cumulative_return'))}`",
        f"- Deterministic overlap cumulative return: `{_pct(deterministic_overlap.get('cumulative_return'))}`",
        f"- Cumulative return gap: `{_pct(metrics.get('cumulative_return_gap'))}`",
        f"- Average monthly return gap: `{_pct(metrics.get('average_monthly_return_gap'))}`",
        f"- Winning-month share: `{_pct(metrics.get('winning_month_share'))}`",
        f"- Relative Sharpe ratio: `{_num(metrics.get('relative_sharpe_ratio'))}`",
        f"- Average turnover gap: `{_pct(metrics.get('average_turnover_gap'))}`",
    ]
    for period in comparison.get("periods", []):
        lines.append(
            "- "
            + (
                f"`{period['date']}`: model `{_pct(period['model_portfolio_net_return'])}`, "
                f"deterministic `{_pct(period['deterministic_portfolio_net_return'])}`, "
                f"gap `{_pct(period['monthly_return_gap'])}`"
            )
        )
    return lines


def _render_subperiod_diagnostics(subperiod_diagnostics: dict[str, Any]) -> list[str]:
    """Render the subperiod and regime diagnostics block."""
    if not subperiod_diagnostics.get("available"):
        return [
            "## Regime And Subperiod Diagnostics",
            "- No overlapping realized dates were available for subperiod or regime diagnostics.",
        ]

    lines = [
        "## Regime And Subperiod Diagnostics",
        f"- Primary regime benchmark: `{subperiod_diagnostics['primary_benchmark']}`",
        f"- Segment types evaluated: `{', '.join(subperiod_diagnostics['segment_types_evaluated'])}`",
        f"- Distinct benchmark-direction regimes in overlap: `{', '.join(subperiod_diagnostics['distinct_benchmark_regimes']) if subperiod_diagnostics['distinct_benchmark_regimes'] else 'none'}`",
        f"- Regime comparison note: {subperiod_diagnostics['regime_comparison_note']}",
        f"- Segment evidence counts: `{subperiod_diagnostics.get('segment_evidence_counts', {})}`",
    ]
    for segment in subperiod_diagnostics.get("segments", []):
        lines.append(
            "- "
            + (
                f"`{segment['segment_type']}` / `{segment['segment_id']}`: "
                f"{segment['period_count']} months, "
                f"gap `{_pct(segment['cumulative_return_gap'])}`, "
                f"winning-month share `{_pct(segment['winning_month_share'])}`, "
                f"benchmark cumulative `{_pct(segment['primary_benchmark_cumulative_return'])}`, "
                f"evidence `{segment.get('evidence_level')}`, "
                f"note `{segment['note']}`"
            )
        )
    return lines


def _render_coverage_summary(coverage_summary: dict[str, Any]) -> list[str]:
    """Render the run-coverage audit block."""
    raw_data_selection = coverage_summary.get("raw_data_selection", {})
    lines = [
        "## Coverage Audit",
        f"- Execution mode: `{coverage_summary.get('execution_mode')}`",
        f"- Raw inputs selected for this run: `{_format_selected_input_profile(raw_data_selection.get('selected_input_profile'))}`",
        f"- This run used only seeded sample inputs: `{raw_data_selection.get('uses_only_seeded_sample_inputs')}`",
        f"- This run used any broader local raw inputs: `{raw_data_selection.get('uses_any_broader_local_raw_inputs')}`",
        f"- Broader local raw files present somewhere on disk: `{raw_data_selection.get('broader_local_raw_available_on_disk', raw_data_selection.get('broader_local_raw_available'))}`",
        f"- Datasets with broader local raw files on disk: {_format_dataset_list(raw_data_selection.get('datasets_with_broader_local_raw_available', []))}",
        f"- Research-scale seeded fallback triggered in this run: `{raw_data_selection.get('seeded_sample_fallback_used_in_run', raw_data_selection.get('seeded_sample_fallback_used'))}`",
    ]
    raw_selection_note = _build_raw_selection_note(raw_data_selection)
    if raw_selection_note:
        lines.append(f"- Note: {raw_selection_note}")
    for dataset_name, dataset_overview in raw_data_selection.get("dataset_overview", {}).items():
        lines.append("- " + _format_raw_dataset_overview(dataset_name, dataset_overview))
    for stage_name, stage_summary in coverage_summary.get("stages", {}).items():
        lines.append("- " + f"`{stage_name}`: `{stage_summary}`")
    return lines


def _render_evidence_context(evidence_context: dict[str, Any]) -> list[str]:
    """Render the summary evidence-tier block."""
    return [
        "## Evidence Context",
        f"- Coverage evidence level: `{evidence_context.get('coverage_evidence_level')}`",
        f"- Minimum months for descriptive segment evidence: `{evidence_context.get('minimum_months_for_descriptive_segment')}`",
        f"- Minimum months for broader-coverage exploratory evidence: `{evidence_context.get('minimum_months_for_broader_coverage_segment')}`",
        f"- Overlap month count used for evidence tier: `{evidence_context.get('overlap_period_count')}`",
    ]


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
        f"- Execution mode: `{summary['execution_mode']}`",
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
        ]
    )
    lines.extend(_render_coverage_summary(summary["coverage_summary"]))
    lines.extend(
        [
            "",
        ]
    )
    lines.extend(_render_evidence_context(summary["evidence_context"]))
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
    fold_diagnostics = summary["fold_diagnostics"]
    overlap_comparison = summary["deterministic_baseline_overlap_comparison"]
    comparison_convention = summary["comparison_convention"]
    subperiod_diagnostics = summary["subperiod_diagnostics"]
    lines = [
        "# Model Strategy Report",
        "",
        "## Run Status",
        f"- Status: `{summary['status']}`",
        f"- Generated at (UTC): `{summary['generated_at_utc']}`",
        f"- Universe preset: `{summary['universe_preset']}`",
        f"- Execution mode: `{summary['execution_mode']}`",
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
    ]
    lines.extend(_render_fold_diagnostics(fold_diagnostics))
    lines.extend(
        [
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
        ]
    )
    lines.extend(_render_overlap_comparison(overlap_comparison, comparison_convention))
    lines.extend([""])
    lines.extend(_render_subperiod_diagnostics(subperiod_diagnostics))
    lines.extend([""])
    lines.extend(_render_coverage_summary(summary["coverage_summary"]))
    lines.extend([""])
    lines.extend(_render_evidence_context(summary["evidence_context"]))
    lines.extend(["", "## Benchmark Comparison"])

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
