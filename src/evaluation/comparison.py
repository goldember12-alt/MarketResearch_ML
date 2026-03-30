"""Overlap-aware comparison helpers for model evaluation reporting."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.backtest.metrics import summarize_return_series


def _as_float_or_none(value: Any) -> float | None:
    """Convert pandas-compatible scalars into plain floats or nulls."""
    if pd.isna(value):
        return None
    return float(value)


def _as_int_or_zero(value: Any) -> int:
    """Convert a scalar count into a plain integer."""
    if pd.isna(value):
        return 0
    return int(value)


def _as_date_string(value: Any) -> str | None:
    """Format a timestamp-like value as an ISO date string."""
    if pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def build_model_comparison_convention() -> dict[str, Any]:
    """Describe the exact overlap comparison convention used in model reporting."""
    return {
        "aligned_on": "realized_return_date",
        "join_method": "inner_join_on_date_between_deterministic_and_model_performance_tables",
        "portfolio_return_series": "portfolio_net_return",
        "formation_timing": "month_end_t_formations_earn_realized_returns_at_month_end_t_plus_1",
        "cumulative_return_method": "compound_each_strategy_only_across_the_overlapping_realized_months_then_compare_terminal_cumulative_returns",
        "win_rate_definition": "share_of_overlapping_realized_months_where_model_portfolio_net_return_exceeds_deterministic_portfolio_net_return",
        "relative_sharpe_definition": "model_overlap_sharpe_divided_by_deterministic_overlap_sharpe_when_both_are_finite_and_deterministic_overlap_sharpe_is_nonzero_otherwise_null",
        "excluded_data": [
            "deterministic_realized_months_without_model_overlap",
            "model_train_predictions",
            "model_validation_predictions_not_selected_for_the_model_backtest",
        ],
    }


def build_fold_diagnostics(
    *,
    test_predictions: pd.DataFrame,
    model_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Summarize held-out fold coverage from the aggregated out-of-sample predictions."""
    predictions = test_predictions.copy()
    if predictions.empty:
        return {
            "fold_count": int(model_metadata.get("fold_count") or 0),
            "heldout_row_count": 0,
            "heldout_decision_month_count": 0,
            "heldout_realized_month_count": 0,
            "decision_start": None,
            "decision_end": None,
            "realized_start": None,
            "realized_end": None,
            "folds": [],
        }

    predictions["date"] = pd.to_datetime(predictions["date"])
    predictions["realized_label_date"] = pd.to_datetime(predictions["realized_label_date"])

    fold_metrics = {
        str(fold.get("fold_id")): fold
        for fold in model_metadata.get("split_windows", {}).get("folds", [])
    }

    fold_rows: list[dict[str, Any]] = []
    for fold_id, fold_frame in predictions.groupby("fold_id", sort=True):
        fold_frame = fold_frame.sort_values(["date", "ticker"]).reset_index(drop=True)
        fold_meta = fold_metrics.get(str(fold_id), {})
        model_test_metrics = fold_meta.get("metrics_by_split", {}).get("test", {}).get("model", {})
        deterministic_test_metrics = (
            fold_meta.get("metrics_by_split", {})
            .get("test", {})
            .get("deterministic_baseline", {})
        )

        fold_rows.append(
            {
                "fold_id": str(fold_id),
                "fold_index": _as_int_or_zero(
                    fold_meta.get("fold_index", fold_frame["fold_index"].iloc[0])
                ),
                "decision_start": _as_date_string(fold_frame["date"].min()),
                "decision_end": _as_date_string(fold_frame["date"].max()),
                "realized_start": _as_date_string(fold_frame["realized_label_date"].min()),
                "realized_end": _as_date_string(fold_frame["realized_label_date"].max()),
                "heldout_row_count": int(len(fold_frame)),
                "heldout_decision_month_count": int(fold_frame["date"].nunique()),
                "heldout_realized_month_count": int(fold_frame["realized_label_date"].nunique()),
                "heldout_unique_ticker_count": int(fold_frame["ticker"].nunique()),
                "train_row_count": _as_int_or_zero(fold_meta.get("train_row_count")),
                "test_row_count": _as_int_or_zero(
                    fold_meta.get("test_row_count", len(fold_frame))
                ),
                "preprocessing_fit_row_count": _as_int_or_zero(
                    fold_meta.get("preprocessing_fit_row_count")
                ),
                "model_test_accuracy": _as_float_or_none(model_test_metrics.get("accuracy")),
                "model_test_roc_auc": _as_float_or_none(model_test_metrics.get("roc_auc")),
                "deterministic_test_accuracy": _as_float_or_none(
                    deterministic_test_metrics.get("accuracy")
                ),
                "deterministic_test_roc_auc": _as_float_or_none(
                    deterministic_test_metrics.get("roc_auc")
                ),
            }
        )

    return {
        "fold_count": int(model_metadata.get("fold_count") or len(fold_rows)),
        "heldout_row_count": int(len(predictions)),
        "heldout_decision_month_count": int(predictions["date"].nunique()),
        "heldout_realized_month_count": int(predictions["realized_label_date"].nunique()),
        "decision_start": _as_date_string(predictions["date"].min()),
        "decision_end": _as_date_string(predictions["date"].max()),
        "realized_start": _as_date_string(predictions["realized_label_date"].min()),
        "realized_end": _as_date_string(predictions["realized_label_date"].max()),
        "folds": fold_rows,
    }


def build_model_vs_deterministic_overlap_summary(
    *,
    deterministic_performance_by_period: pd.DataFrame,
    model_performance_by_period: pd.DataFrame,
) -> dict[str, Any]:
    """Compare deterministic and model-driven portfolio returns on overlapping realized dates only."""
    deterministic = deterministic_performance_by_period.copy()
    model = model_performance_by_period.copy()

    if deterministic.empty or model.empty:
        return {
            "available": False,
            "overlap_period_count": 0,
            "realized_start": None,
            "realized_end": None,
            "formation_start": None,
            "formation_end": None,
            "model_metrics_on_overlap": {},
            "deterministic_metrics_on_overlap": {},
            "comparison_metrics": {},
            "periods": [],
        }

    deterministic["date"] = pd.to_datetime(deterministic["date"])
    deterministic["formation_date"] = pd.to_datetime(deterministic["formation_date"])
    model["date"] = pd.to_datetime(model["date"])
    model["formation_date"] = pd.to_datetime(model["formation_date"])

    deterministic = deterministic.loc[
        :,
        [
            "date",
            "formation_date",
            "portfolio_net_return",
            "portfolio_gross_return",
            "turnover",
        ],
    ].rename(
        columns={
            "formation_date": "deterministic_formation_date",
            "portfolio_net_return": "deterministic_portfolio_net_return",
            "portfolio_gross_return": "deterministic_portfolio_gross_return",
            "turnover": "deterministic_turnover",
        }
    )
    model = model.loc[
        :,
        [
            "date",
            "formation_date",
            "portfolio_net_return",
            "portfolio_gross_return",
            "turnover",
        ],
    ].rename(
        columns={
            "formation_date": "model_formation_date",
            "portfolio_net_return": "model_portfolio_net_return",
            "portfolio_gross_return": "model_portfolio_gross_return",
            "turnover": "model_turnover",
        }
    )

    overlap = deterministic.merge(model, on="date", how="inner").sort_values("date").reset_index(
        drop=True
    )
    if overlap.empty:
        return {
            "available": False,
            "overlap_period_count": 0,
            "realized_start": None,
            "realized_end": None,
            "formation_start": None,
            "formation_end": None,
            "model_metrics_on_overlap": {},
            "deterministic_metrics_on_overlap": {},
            "comparison_metrics": {},
            "periods": [],
        }

    model_metrics = summarize_return_series(
        overlap["model_portfolio_net_return"],
        turnover=overlap["model_turnover"],
    )
    deterministic_metrics = summarize_return_series(
        overlap["deterministic_portfolio_net_return"],
        turnover=overlap["deterministic_turnover"],
    )
    monthly_gap = overlap["model_portfolio_net_return"] - overlap["deterministic_portfolio_net_return"]

    model_sharpe = model_metrics.get("sharpe_ratio")
    deterministic_sharpe = deterministic_metrics.get("sharpe_ratio")
    relative_sharpe_ratio = None
    if (
        model_sharpe is not None
        and deterministic_sharpe is not None
        and pd.notna(model_sharpe)
        and pd.notna(deterministic_sharpe)
        and float(deterministic_sharpe) != 0.0
    ):
        relative_sharpe_ratio = float(model_sharpe) / float(deterministic_sharpe)

    return {
        "available": True,
        "overlap_period_count": int(len(overlap)),
        "realized_start": _as_date_string(overlap["date"].min()),
        "realized_end": _as_date_string(overlap["date"].max()),
        "formation_start": _as_date_string(
            min(
                overlap["deterministic_formation_date"].min(),
                overlap["model_formation_date"].min(),
            )
        ),
        "formation_end": _as_date_string(
            max(
                overlap["deterministic_formation_date"].max(),
                overlap["model_formation_date"].max(),
            )
        ),
        "model_metrics_on_overlap": {
            key: _as_float_or_none(value) for key, value in model_metrics.items()
        },
        "deterministic_metrics_on_overlap": {
            key: _as_float_or_none(value) for key, value in deterministic_metrics.items()
        },
        "comparison_metrics": {
            "cumulative_return_gap": _as_float_or_none(
                _as_float_or_none(model_metrics.get("cumulative_return"))
                - _as_float_or_none(deterministic_metrics.get("cumulative_return"))
                if _as_float_or_none(model_metrics.get("cumulative_return")) is not None
                and _as_float_or_none(deterministic_metrics.get("cumulative_return")) is not None
                else None
            ),
            "average_monthly_return_gap": _as_float_or_none(monthly_gap.mean()),
            "median_monthly_return_gap": _as_float_or_none(monthly_gap.median()),
            "winning_month_share": _as_float_or_none((monthly_gap > 0.0).mean()),
            "average_turnover_gap": _as_float_or_none(
                overlap["model_turnover"].mean() - overlap["deterministic_turnover"].mean()
            ),
            "best_month_gap": _as_float_or_none(monthly_gap.max()),
            "worst_month_gap": _as_float_or_none(monthly_gap.min()),
            "sharpe_ratio_gap": _as_float_or_none(
                _as_float_or_none(model_sharpe) - _as_float_or_none(deterministic_sharpe)
                if _as_float_or_none(model_sharpe) is not None
                and _as_float_or_none(deterministic_sharpe) is not None
                else None
            ),
            "relative_sharpe_ratio": _as_float_or_none(relative_sharpe_ratio),
        },
        "periods": [
            {
                "date": _as_date_string(row["date"]),
                "deterministic_formation_date": _as_date_string(
                    row["deterministic_formation_date"]
                ),
                "model_formation_date": _as_date_string(row["model_formation_date"]),
                "deterministic_portfolio_net_return": _as_float_or_none(
                    row["deterministic_portfolio_net_return"]
                ),
                "model_portfolio_net_return": _as_float_or_none(row["model_portfolio_net_return"]),
                "monthly_return_gap": _as_float_or_none(
                    row["model_portfolio_net_return"] - row["deterministic_portfolio_net_return"]
                ),
                "model_won_month": bool(
                    row["model_portfolio_net_return"] > row["deterministic_portfolio_net_return"]
                ),
            }
            for _, row in overlap.iterrows()
        ],
    }
