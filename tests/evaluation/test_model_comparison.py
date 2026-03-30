"""Focused tests for overlap-aware model comparison helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from src.evaluation.comparison import (
    build_fold_diagnostics,
    build_model_comparison_convention,
    build_model_vs_deterministic_overlap_summary,
)


def test_build_model_vs_deterministic_overlap_summary_uses_only_shared_realized_dates() -> None:
    """Overlap comparison should inner-join on realized dates and recompute metrics on that slice."""
    deterministic = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-04-30", "2024-05-31", "2024-06-30"]),
            "formation_date": pd.to_datetime(["2024-03-31", "2024-04-30", "2024-05-31"]),
            "portfolio_net_return": [0.03, 0.01, 0.02],
            "portfolio_gross_return": [0.031, 0.011, 0.021],
            "turnover": [0.0, 0.2, 0.1],
        }
    )
    model = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-05-31", "2024-06-30"]),
            "formation_date": pd.to_datetime(["2024-04-30", "2024-05-31"]),
            "portfolio_net_return": [0.02, 0.01],
            "portfolio_gross_return": [0.021, 0.011],
            "turnover": [0.4, 0.1],
        }
    )

    summary = build_model_vs_deterministic_overlap_summary(
        deterministic_performance_by_period=deterministic,
        model_performance_by_period=model,
    )

    assert summary["available"] is True
    assert summary["overlap_period_count"] == 2
    assert summary["realized_start"] == "2024-05-31"
    assert summary["realized_end"] == "2024-06-30"
    assert summary["comparison_metrics"]["average_monthly_return_gap"] == 0.0
    assert summary["comparison_metrics"]["cumulative_return_gap"] == 0.0
    assert summary["comparison_metrics"]["winning_month_share"] == 0.5
    assert summary["comparison_metrics"]["average_turnover_gap"] == pytest.approx(0.1)
    assert [period["date"] for period in summary["periods"]] == ["2024-05-31", "2024-06-30"]


def test_build_fold_diagnostics_reports_heldout_coverage_and_fold_metrics() -> None:
    """Fold diagnostics should expose held-out coverage plus model and deterministic metrics by fold."""
    test_predictions = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT", "AAPL", "MSFT"],
            "date": pd.to_datetime(["2024-04-30", "2024-04-30", "2024-05-31", "2024-05-31"]),
            "realized_label_date": pd.to_datetime(
                ["2024-05-31", "2024-05-31", "2024-06-30", "2024-06-30"]
            ),
            "fold_id": ["fold_001", "fold_001", "fold_002", "fold_002"],
            "fold_index": [1, 1, 2, 2],
        }
    )
    model_metadata = {
        "fold_count": 2,
        "split_windows": {
            "folds": [
                {
                    "fold_id": "fold_001",
                    "fold_index": 1,
                    "train_row_count": 40,
                    "test_row_count": 2,
                    "preprocessing_fit_row_count": 40,
                    "metrics_by_split": {
                        "test": {
                            "model": {"accuracy": 0.75, "roc_auc": 0.84},
                            "deterministic_baseline": {"accuracy": 0.2, "roc_auc": 0.19},
                        }
                    },
                },
                {
                    "fold_id": "fold_002",
                    "fold_index": 2,
                    "train_row_count": 60,
                    "test_row_count": 2,
                    "preprocessing_fit_row_count": 60,
                    "metrics_by_split": {
                        "test": {
                            "model": {"accuracy": 0.9, "roc_auc": 0.97},
                            "deterministic_baseline": {"accuracy": 0.3, "roc_auc": 0.31},
                        }
                    },
                },
            ]
        },
    }

    diagnostics = build_fold_diagnostics(
        test_predictions=test_predictions,
        model_metadata=model_metadata,
    )

    assert diagnostics["fold_count"] == 2
    assert diagnostics["heldout_decision_month_count"] == 2
    assert diagnostics["heldout_realized_month_count"] == 2
    assert diagnostics["decision_start"] == "2024-04-30"
    assert diagnostics["realized_end"] == "2024-06-30"
    assert diagnostics["folds"][0]["fold_id"] == "fold_001"
    assert diagnostics["folds"][0]["model_test_accuracy"] == 0.75
    assert diagnostics["folds"][1]["deterministic_test_roc_auc"] == 0.31


def test_build_model_comparison_convention_documents_alignment_rules() -> None:
    """The comparison convention should explicitly state alignment, exclusions, and win-rate logic."""
    convention = build_model_comparison_convention()

    assert convention["aligned_on"] == "realized_return_date"
    assert convention["portfolio_return_series"] == "portfolio_net_return"
    assert "model_train_predictions" in convention["excluded_data"]
