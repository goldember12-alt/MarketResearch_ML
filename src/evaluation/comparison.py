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


def _empty_overlap_summary() -> dict[str, Any]:
    """Return an empty overlap-comparison payload."""
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


def _prepare_overlap_frame(
    *,
    deterministic_performance_by_period: pd.DataFrame,
    model_performance_by_period: pd.DataFrame,
    primary_benchmark: str | None = None,
) -> pd.DataFrame:
    """Inner-join deterministic and model performance on shared realized dates."""
    deterministic = deterministic_performance_by_period.copy()
    model = model_performance_by_period.copy()
    if deterministic.empty or model.empty:
        return pd.DataFrame()

    deterministic["date"] = pd.to_datetime(deterministic["date"])
    deterministic["formation_date"] = pd.to_datetime(deterministic["formation_date"])
    model["date"] = pd.to_datetime(model["date"])
    model["formation_date"] = pd.to_datetime(model["formation_date"])

    benchmark_column = (
        f"benchmark_return__{primary_benchmark}" if primary_benchmark is not None else None
    )
    deterministic_columns = [
        "date",
        "formation_date",
        "portfolio_net_return",
        "portfolio_gross_return",
        "turnover",
    ]
    if benchmark_column is not None and benchmark_column in deterministic.columns:
        deterministic_columns.append(benchmark_column)

    model_columns = [
        "date",
        "formation_date",
        "portfolio_net_return",
        "portfolio_gross_return",
        "turnover",
    ]
    if benchmark_column is not None and benchmark_column in model.columns:
        model_columns.append(benchmark_column)

    deterministic = deterministic.loc[:, deterministic_columns].rename(
        columns={
            "formation_date": "deterministic_formation_date",
            "portfolio_net_return": "deterministic_portfolio_net_return",
            "portfolio_gross_return": "deterministic_portfolio_gross_return",
            "turnover": "deterministic_turnover",
            benchmark_column: "deterministic_primary_benchmark_return",
        }
    )
    model = model.loc[:, model_columns].rename(
        columns={
            "formation_date": "model_formation_date",
            "portfolio_net_return": "model_portfolio_net_return",
            "portfolio_gross_return": "model_portfolio_gross_return",
            "turnover": "model_turnover",
            benchmark_column: "model_primary_benchmark_return",
        }
    )

    overlap = deterministic.merge(model, on="date", how="inner").sort_values("date").reset_index(
        drop=True
    )
    if overlap.empty:
        return overlap

    if (
        "deterministic_primary_benchmark_return" in overlap.columns
        or "model_primary_benchmark_return" in overlap.columns
    ):
        overlap["primary_benchmark_return"] = overlap.get(
            "deterministic_primary_benchmark_return",
            pd.Series(index=overlap.index, dtype="float64"),
        )
        if "model_primary_benchmark_return" in overlap.columns:
            overlap["primary_benchmark_return"] = overlap["primary_benchmark_return"].fillna(
                overlap["model_primary_benchmark_return"]
            )
    else:
        overlap["primary_benchmark_return"] = pd.NA

    return overlap


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
    overlap = _prepare_overlap_frame(
        deterministic_performance_by_period=deterministic_performance_by_period,
        model_performance_by_period=model_performance_by_period,
    )
    if overlap.empty:
        return _empty_overlap_summary()

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


def _fold_label_by_realized_date(test_predictions: pd.DataFrame) -> pd.DataFrame:
    """Map each realized label date to its contributing fold label."""
    predictions = test_predictions.copy()
    if predictions.empty:
        return pd.DataFrame(columns=["date", "fold_id_label"])

    predictions["realized_label_date"] = pd.to_datetime(predictions["realized_label_date"])
    mapped = (
        predictions.groupby("realized_label_date")["fold_id"]
        .agg(lambda values: ",".join(sorted({str(value) for value in values})))
        .reset_index()
        .rename(
            columns={
                "realized_label_date": "date",
                "fold_id": "fold_id_label",
            }
        )
    )
    return mapped


def _benchmark_direction_label(value: Any) -> str:
    """Bucket a monthly benchmark return into a simple market-direction regime."""
    if pd.isna(value):
        return "benchmark_unavailable"
    if float(value) > 0.0:
        return "benchmark_up"
    if float(value) < 0.0:
        return "benchmark_down"
    return "benchmark_flat"


def _summarize_overlap_segment(
    *,
    frame: pd.DataFrame,
    segment_type: str,
    segment_id: str,
    primary_benchmark: str,
    overlap_period_count: int,
) -> dict[str, Any]:
    """Summarize one overlap subperiod or regime segment."""
    model_metrics = summarize_return_series(
        frame["model_portfolio_net_return"],
        turnover=frame["model_turnover"],
    )
    deterministic_metrics = summarize_return_series(
        frame["deterministic_portfolio_net_return"],
        turnover=frame["deterministic_turnover"],
    )
    monthly_gap = frame["model_portfolio_net_return"] - frame["deterministic_portfolio_net_return"]

    model_sharpe = _as_float_or_none(model_metrics.get("sharpe_ratio"))
    deterministic_sharpe = _as_float_or_none(deterministic_metrics.get("sharpe_ratio"))
    relative_sharpe_ratio = None
    if (
        model_sharpe is not None
        and deterministic_sharpe is not None
        and deterministic_sharpe != 0.0
    ):
        relative_sharpe_ratio = model_sharpe / deterministic_sharpe

    benchmark_cumulative_return = None
    if "primary_benchmark_return" in frame.columns and frame["primary_benchmark_return"].notna().any():
        benchmark_cumulative_return = float((1.0 + frame["primary_benchmark_return"].fillna(0.0)).prod() - 1.0)

    period_count = int(len(frame))
    sparse_segment = period_count < 3
    note = (
        "descriptive_only_short_segment"
        if sparse_segment
        else "segment_has_minimum_history_for_basic_descriptive_comparison"
    )
    return {
        "segment_type": segment_type,
        "segment_id": segment_id,
        "period_count": period_count,
        "realized_start": _as_date_string(frame["date"].min()),
        "realized_end": _as_date_string(frame["date"].max()),
        "coverage_share_of_overlap": _as_float_or_none(period_count / overlap_period_count),
        "primary_benchmark": primary_benchmark,
        "primary_benchmark_average_monthly_return": _as_float_or_none(
            frame["primary_benchmark_return"].mean()
        )
        if "primary_benchmark_return" in frame.columns
        else None,
        "primary_benchmark_cumulative_return": _as_float_or_none(benchmark_cumulative_return),
        "model_cumulative_return": _as_float_or_none(model_metrics.get("cumulative_return")),
        "deterministic_cumulative_return": _as_float_or_none(
            deterministic_metrics.get("cumulative_return")
        ),
        "cumulative_return_gap": _as_float_or_none(
            _as_float_or_none(model_metrics.get("cumulative_return"))
            - _as_float_or_none(deterministic_metrics.get("cumulative_return"))
            if _as_float_or_none(model_metrics.get("cumulative_return")) is not None
            and _as_float_or_none(deterministic_metrics.get("cumulative_return")) is not None
            else None
        ),
        "average_monthly_return_gap": _as_float_or_none(monthly_gap.mean()),
        "winning_month_share": _as_float_or_none((monthly_gap > 0.0).mean()),
        "model_sharpe_ratio": model_sharpe,
        "deterministic_sharpe_ratio": deterministic_sharpe,
        "relative_sharpe_ratio": _as_float_or_none(relative_sharpe_ratio),
        "average_turnover_gap": _as_float_or_none(
            frame["model_turnover"].mean() - frame["deterministic_turnover"].mean()
        ),
        "sparse_segment": sparse_segment,
        "note": note,
    }


def build_overlap_subperiod_diagnostics(
    *,
    deterministic_performance_by_period: pd.DataFrame,
    model_performance_by_period: pd.DataFrame,
    test_predictions: pd.DataFrame,
    primary_benchmark: str = "SPY",
) -> dict[str, Any]:
    """Summarize overlap performance by fold, calendar bucket, and benchmark-direction regime."""
    overlap = _prepare_overlap_frame(
        deterministic_performance_by_period=deterministic_performance_by_period,
        model_performance_by_period=model_performance_by_period,
        primary_benchmark=primary_benchmark,
    )
    if overlap.empty:
        return {
            "available": False,
            "primary_benchmark": primary_benchmark,
            "segment_types_evaluated": [],
            "segment_counts_by_type": {},
            "distinct_benchmark_regimes": [],
            "regime_comparison_supported": False,
            "regime_comparison_note": "No overlapping realized dates were available for subperiod diagnostics.",
            "segments": [],
        }

    overlap = overlap.merge(_fold_label_by_realized_date(test_predictions), on="date", how="left")
    overlap["fold_id_label"] = overlap["fold_id_label"].fillna("fold_unavailable")
    overlap["calendar_month"] = overlap["date"].dt.strftime("%Y-%m")
    overlap["calendar_quarter"] = overlap["date"].dt.to_period("Q").astype(str)
    overlap["benchmark_direction"] = overlap["primary_benchmark_return"].apply(
        _benchmark_direction_label
    )
    overlap_period_count = len(overlap)

    segment_specs = (
        ("fold_id", "fold_id_label"),
        ("calendar_month", "calendar_month"),
        ("calendar_quarter", "calendar_quarter"),
        ("benchmark_direction", "benchmark_direction"),
    )
    segments: list[dict[str, Any]] = []
    segment_counts_by_type: dict[str, int] = {}
    for segment_type, column_name in segment_specs:
        grouped_segments = []
        for segment_id, frame in overlap.groupby(column_name, sort=True):
            row = _summarize_overlap_segment(
                frame=frame.sort_values("date").reset_index(drop=True),
                segment_type=segment_type,
                segment_id=str(segment_id),
                primary_benchmark=primary_benchmark,
                overlap_period_count=overlap_period_count,
            )
            grouped_segments.append(row)
        segments.extend(grouped_segments)
        segment_counts_by_type[segment_type] = len(grouped_segments)

    distinct_benchmark_regimes = sorted(
        {
            str(value)
            for value in overlap["benchmark_direction"].dropna().unique().tolist()
            if str(value) != "benchmark_unavailable"
        }
    )
    regime_comparison_supported = len(distinct_benchmark_regimes) >= 2
    regime_comparison_note = (
        "At least two benchmark-direction regimes are present inside the overlap window."
        if regime_comparison_supported
        else "The current overlap window contains fewer than two benchmark-direction regimes, so regime comparison remains descriptive only."
    )

    return {
        "available": True,
        "primary_benchmark": primary_benchmark,
        "segment_types_evaluated": [segment_type for segment_type, _ in segment_specs],
        "segment_counts_by_type": segment_counts_by_type,
        "distinct_benchmark_regimes": distinct_benchmark_regimes,
        "regime_comparison_supported": regime_comparison_supported,
        "regime_comparison_note": regime_comparison_note,
        "segments": segments,
    }
