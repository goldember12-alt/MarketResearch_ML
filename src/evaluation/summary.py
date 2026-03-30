"""Structured evaluation summaries derived from backtest artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from src.backtest.config import BacktestPipelineConfig
from src.evaluation.comparison import (
    build_fold_diagnostics,
    build_model_comparison_convention,
    build_overlap_subperiod_diagnostics,
    build_model_vs_deterministic_overlap_summary,
)
from src.models.config import ModelPipelineConfig
from src.signals.config import SignalPipelineConfig
from src.utils.config import EvaluationConfig, ProjectConfig


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


def _coverage_evidence_label(
    period_count: int,
    *,
    evaluation_config: EvaluationConfig,
) -> str:
    """Classify available overlap history into a simple report-evidence tier."""
    if period_count < evaluation_config.evidence.minimum_months_for_descriptive_segment:
        return "insufficient_segment_history"
    if period_count < evaluation_config.evidence.minimum_months_for_broader_coverage_segment:
        return "descriptive_segment_evidence"
    return "broader_coverage_exploratory_evidence"


def _build_evidence_context(
    *,
    evaluation_config: EvaluationConfig,
    overlap_period_count: int | None = None,
) -> dict[str, Any]:
    """Build a concise evidence-tier summary for downstream reports and registries."""
    if overlap_period_count is None:
        overlap_period_count = 0
    return {
        "minimum_months_for_descriptive_segment": evaluation_config.evidence.minimum_months_for_descriptive_segment,
        "minimum_months_for_broader_coverage_segment": evaluation_config.evidence.minimum_months_for_broader_coverage_segment,
        "overlap_period_count": overlap_period_count,
        "coverage_evidence_level": _coverage_evidence_label(
            overlap_period_count,
            evaluation_config=evaluation_config,
        ),
    }


def _model_risk_controls() -> list[str]:
    """Return the currently implemented model-path risk controls."""
    return [
        "Model labels align month-end decision date t to realized outcomes at month-end t+1 only.",
        "Chronological fold generation is explicit and config-driven; no random row shuffling is used.",
        "Preprocessing is refit separately inside each fold on training rows only.",
        "Model-driven backtests consume only aggregated out-of-sample predictions, never in-fold training predictions.",
        "Model backtests reuse the same turnover, cost, holdings, and benchmark logic as the deterministic baseline.",
    ]


def _model_bias_caveats() -> list[str]:
    """Return the current known model-path caveats that must accompany reported results."""
    return [
        "Fundamentals are lagged but not truly point-in-time safe, so revised-history bias remains possible.",
        "Current sample data are local deterministic fixtures rather than benchmark-quality research data.",
        "The current walk-forward history is short, so model diagnostics and annualized portfolio metrics are descriptive only.",
        "Canonical model artifact paths are overwritten by the latest selected-model run unless richer versioning is added later.",
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
    stage_coverage: dict[str, Any],
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
        "execution_mode": project_config.execution.mode_name,
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
        "coverage_summary": stage_coverage,
        "evidence_context": _build_evidence_context(
            evaluation_config=project_config.evaluation,
        ),
        "interpretation": interpretation,
        "next_step": "Run the chronology-safe model path on broader local raw coverage so overlap-aware robustness reporting has materially longer history.",
    }


def build_model_evaluation_summary(
    *,
    project_config: ProjectConfig,
    model_config: ModelPipelineConfig,
    backtest_config: BacktestPipelineConfig,
    model_metadata: dict[str, Any],
    model_backtest_summary: dict[str, Any],
    portfolio_returns: pd.DataFrame,
    performance_by_period: pd.DataFrame,
    deterministic_performance_by_period: pd.DataFrame,
    risk_metrics_summary: pd.DataFrame,
    test_predictions: pd.DataFrame,
    stage_coverage: dict[str, Any],
) -> dict[str, Any]:
    """Build a report-ready summary for the model-driven backtest and modeling diagnostics."""
    metrics_by_series = _metrics_lookup(risk_metrics_summary)
    portfolio_net_metrics = metrics_by_series.get("portfolio_net", {})
    benchmark_comparison = _build_benchmark_comparison(
        performance_by_period,
        metrics_by_series,
        backtest_config.benchmarks.identifiers,
    )
    comparison_convention = build_model_comparison_convention()
    fold_diagnostics = build_fold_diagnostics(
        test_predictions=test_predictions,
        model_metadata=model_metadata,
    )
    deterministic_baseline_overlap_comparison = build_model_vs_deterministic_overlap_summary(
        deterministic_performance_by_period=deterministic_performance_by_period,
        model_performance_by_period=performance_by_period,
    )
    subperiod_diagnostics = build_overlap_subperiod_diagnostics(
        deterministic_performance_by_period=deterministic_performance_by_period,
        model_performance_by_period=performance_by_period,
        test_predictions=test_predictions,
        evaluation_config=project_config.evaluation,
        primary_benchmark=model_config.label.benchmark,
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
            f"Across {realized_period_count} realized model-backtest monthly periods, the portfolio "
            "net cumulative return was unavailable. "
        )
    else:
        portfolio_result_text = (
            f"Across {realized_period_count} realized model-backtest monthly periods, the portfolio "
            f"net cumulative return was {cumulative_return:.2%}. "
        )
    overlap_text = ""
    overlap_metrics = deterministic_baseline_overlap_comparison.get("comparison_metrics", {})
    overlap_period_count = deterministic_baseline_overlap_comparison.get("overlap_period_count", 0)
    overlap_cumulative_gap = overlap_metrics.get("cumulative_return_gap")
    if deterministic_baseline_overlap_comparison.get("available") and overlap_cumulative_gap is not None:
        relative_phrase = (
            "outperformed"
            if overlap_cumulative_gap > 0.0
            else "lagged"
            if overlap_cumulative_gap < 0.0
            else "matched"
        )
        overlap_text = (
            f"Across the {overlap_period_count} realized months overlapping the deterministic "
            f"baseline, the model-driven portfolio {relative_phrase} by "
            f"{abs(overlap_cumulative_gap):.2%} in cumulative net return. "
        )
    interpretation = "This model run is exploratory. " + portfolio_result_text + (
        overlap_text
        if overlap_text
        else ""
    ) + (
        "The model is now evaluated through chronology-safe out-of-sample folds and a downstream "
        "model-driven backtest, but the sample remains short, the data are local fixtures, and "
        "fundamentals are not point-in-time safe."
    )

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Summarize the model-driven backtest together with the current model's out-of-sample diagnostics and log an exploratory model evaluation run.",
        "status": "exploratory_completed",
        "universe_preset": project_config.universe.preset_name,
        "execution_mode": project_config.execution.mode_name,
        "benchmark_set": list(backtest_config.benchmarks.identifiers),
        "feature_set": list(model_config.dataset.feature_columns),
        "signal_or_model": model_metadata["model_type"],
        "date_range": {
            "formation_start": model_backtest_summary.get("formation_start_date"),
            "formation_end": model_backtest_summary.get("formation_end_date"),
            "realized_start": model_backtest_summary.get("realized_start_date"),
            "realized_end": model_backtest_summary.get("realized_end_date"),
            "prediction_decision_start": model_metadata.get("out_of_sample_date_range", {}).get(
                "decision_start"
            ),
            "prediction_decision_end": model_metadata.get("out_of_sample_date_range", {}).get(
                "decision_end"
            ),
        },
        "portfolio_rules": {
            "selection_method": backtest_config.portfolio.selection_method,
            "selected_top_n": backtest_config.portfolio.selected_top_n,
            "weighting_scheme": backtest_config.portfolio.weighting_scheme,
            "max_weight": backtest_config.portfolio.max_weight,
            "cash_handling_policy": backtest_config.portfolio.cash_handling_policy,
            "holding_period_convention": model_backtest_summary.get("holding_period_convention"),
            "prediction_score_column": model_backtest_summary.get("prediction_score_column"),
            "prediction_splits_used": model_backtest_summary.get("prediction_splits_used"),
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
        "model_diagnostics": {
            "model_type": model_metadata["model_type"],
            "label_definition": model_metadata["label_definition"],
            "split_scheme": model_metadata["split_scheme"],
            "fold_count": model_metadata.get("fold_count"),
            "out_of_sample_date_range": model_metadata.get("out_of_sample_date_range", {}),
            "out_of_sample_evaluation": model_metadata.get("out_of_sample_evaluation", {}),
            "classification_threshold": model_metadata.get("classification_threshold"),
            "deterministic_baseline_context": model_metadata.get(
                "deterministic_baseline_context", {}
            ),
        },
        "comparison_convention": comparison_convention,
        "fold_diagnostics": fold_diagnostics,
        "deterministic_baseline_overlap_comparison": deterministic_baseline_overlap_comparison,
        "subperiod_diagnostics": subperiod_diagnostics,
        "risk_controls": _model_risk_controls(),
        "bias_caveats": _model_bias_caveats(),
        "qc_summary": model_backtest_summary.get("qc", {}),
        "coverage_summary": stage_coverage,
        "evidence_context": _build_evidence_context(
            evaluation_config=project_config.evaluation,
            overlap_period_count=deterministic_baseline_overlap_comparison.get(
                "overlap_period_count", 0
            ),
        ),
        "interpretation": interpretation,
        "next_step": "Extend realized history so the new subperiod and regime diagnostics can be evaluated over materially longer overlap windows.",
    }
