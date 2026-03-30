"""Model-score ranking and model-driven backtest helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from src.backtest.config import BacktestPipelineConfig
from src.backtest.metrics import build_backtest_summary
from src.data.standardize import assert_unique_keys
from src.models.config import ModelPipelineConfig


def build_model_signal_rankings(
    predictions: pd.DataFrame,
    *,
    model_config: ModelPipelineConfig,
    backtest_config: BacktestPipelineConfig,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Convert held-out model predictions into monthly ranking selections."""
    assert_unique_keys(predictions, ["ticker", "date"], "model_test_predictions")
    if model_config.backtest.score_column not in predictions.columns:
        raise ValueError(
            f"Prediction artifact is missing backtest score column "
            f"{model_config.backtest.score_column!r}."
        )

    filtered = predictions.loc[
        predictions["split"].isin(model_config.backtest.prediction_splits)
    ].copy()
    if filtered.empty:
        raise ValueError(
            "No prediction rows matched the configured model backtest splits: "
            f"{list(model_config.backtest.prediction_splits)}"
        )
    if filtered["model_type"].nunique() != 1:
        raise ValueError("Model backtest expects exactly one model_type in test_predictions.")

    ranked_frames: list[pd.DataFrame] = []
    for _, month_frame in filtered.groupby("date", sort=False):
        ranked = month_frame.sort_values(
            [model_config.backtest.score_column, "ticker"],
            ascending=[False, True],
            na_position="last",
        ).reset_index(drop=True)
        ranked["composite_score"] = ranked[model_config.backtest.score_column].astype(float)
        ranked["score_rank"] = ranked["composite_score"].rank(
            method="first",
            ascending=False,
        )
        ranked["score_rank_pct"] = ranked["score_rank"] / len(ranked)
        ranked["selected_top_n"] = ranked["score_rank"] <= backtest_config.portfolio.selected_top_n
        ranked_frames.append(ranked)

    model_signal_rankings = (
        pd.concat(ranked_frames, ignore_index=True)
        .sort_values(["date", "ticker"])
        .reset_index(drop=True)
    )
    assert_unique_keys(model_signal_rankings, ["ticker", "date"], "model_signal_rankings")

    metadata = {
        "score_column": model_config.backtest.score_column,
        "prediction_splits": list(model_config.backtest.prediction_splits),
        "selection_top_n": backtest_config.portfolio.selected_top_n,
        "model_type": str(model_signal_rankings["model_type"].iloc[0]),
    }
    return model_signal_rankings, metadata


def build_model_backtest_summary(
    *,
    model_config: ModelPipelineConfig,
    backtest_config: BacktestPipelineConfig,
    model_metadata: dict[str, Any],
    portfolio_returns: pd.DataFrame,
    benchmark_returns: pd.DataFrame,
    risk_metrics_summary: pd.DataFrame,
    qc_summary: dict[str, Any],
    signal_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Build a model-driven backtest summary on top of the shared backtest summary."""
    summary = build_backtest_summary(
        backtest_config,
        portfolio_returns,
        benchmark_returns,
        risk_metrics_summary,
        qc_summary,
    )
    summary.update(
        {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "stage": "model_backtest",
            "signal_source": "model_predictions",
            "model_type": model_metadata["model_type"],
            "model_label_definition": model_metadata["label_definition"],
            "model_split_scheme": model_metadata["split_scheme"],
            "model_fold_count": model_metadata.get("fold_count"),
            "prediction_score_column": signal_metadata["score_column"],
            "prediction_splits_used": signal_metadata["prediction_splits"],
            "feature_columns": model_metadata["feature_columns"],
            "status": "exploratory_completed",
            "key_caveats": [
                "This is a model-score backtest built only from aggregated out-of-sample prediction windows.",
                "The realized sample is still very short, so return metrics are descriptive only.",
                "Fundamentals remain lagged heuristics rather than fully point-in-time-safe history.",
            ],
            "next_step": "Extend the multi-window model backtest with richer reporting, longer realized history, and broader robustness diagnostics.",
        }
    )
    return summary


def build_model_backtest_registry_record(
    *,
    model_config: ModelPipelineConfig,
    backtest_summary: dict[str, Any],
    artifacts_written: list[str],
) -> dict[str, Any]:
    """Build a compact experiment-registry record for the model-driven backtest."""
    portfolio_net = backtest_summary["metrics_by_series"].get("portfolio_net", {})
    return {
        "experiment_id": f"model_backtest_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "run_timestamp": backtest_summary["generated_at_utc"],
        "stage": "model_backtest",
        "purpose": "Backtest held-out model-score rankings under the same monthly portfolio construction and benchmark controls as the deterministic baseline.",
        "date_range": {
            "formation_start": backtest_summary.get("formation_start_date"),
            "formation_end": backtest_summary.get("formation_end_date"),
            "realized_start": backtest_summary.get("realized_start_date"),
            "realized_end": backtest_summary.get("realized_end_date"),
        },
        "universe_preset": model_config.project.universe.preset_name,
        "benchmark_set": backtest_summary.get("benchmark_identifiers", []),
        "feature_set": model_config.dataset.feature_columns,
        "signal_or_model": backtest_summary["model_type"],
        "portfolio_rules": {
            "selection_method": "top_n_from_model_scores",
            "selected_top_n": backtest_summary["selected_top_n"],
            "weighting_scheme": backtest_summary["weighting_scheme"],
            "cash_handling_policy": backtest_summary["cash_handling_policy"],
            "holding_period_convention": backtest_summary["holding_period_convention"],
            "prediction_splits_used": backtest_summary["prediction_splits_used"],
            "model_split_scheme": backtest_summary.get("model_split_scheme"),
            "model_fold_count": backtest_summary.get("model_fold_count"),
        },
        "rebalance_frequency": backtest_summary["rebalance_frequency"],
        "transaction_cost_bps": backtest_summary["transaction_cost_bps"],
        "artifacts_written": artifacts_written,
        "result_summary": {
            "portfolio_net_cumulative_return": portfolio_net.get("cumulative_return"),
            "portfolio_net_annualized_return": portfolio_net.get("annualized_return"),
            "portfolio_net_sharpe_ratio": portfolio_net.get("sharpe_ratio"),
            "portfolio_period_count": backtest_summary.get("portfolio_period_count"),
        },
        "interpretation": (
            "This model-driven backtest is exploratory because it uses a short aggregated "
            "out-of-sample sample and fixture-style local data. It is useful for pipeline "
            "verification, not for strong strategy claims."
        ),
        "status": backtest_summary["status"],
        "next_step": backtest_summary["next_step"],
    }
