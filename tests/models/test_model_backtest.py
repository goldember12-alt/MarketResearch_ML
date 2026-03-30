"""Focused tests for model-driven backtest preparation."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from src.backtest.config import load_backtest_pipeline_config
from src.models.backtest import build_model_signal_rankings
from src.models.config import load_model_pipeline_config


def _model_config():
    config = load_model_pipeline_config()
    return replace(
        config,
        backtest=replace(
            config.backtest,
            score_column="predicted_probability",
            prediction_splits=("test",),
        ),
    )


def _backtest_config():
    config = load_backtest_pipeline_config()
    return replace(config, portfolio=replace(config.portfolio, selected_top_n=2))


def _predictions_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [
                "AAA",
                "BBB",
                "CCC",
                "DDD",
                "AAA",
                "BBB",
                "CCC",
                "DDD",
                "AAA",
                "BBB",
                "CCC",
                "DDD",
            ],
            "date": pd.to_datetime(
                [
                    "2024-02-29",
                    "2024-02-29",
                    "2024-02-29",
                    "2024-02-29",
                    "2024-03-31",
                    "2024-03-31",
                    "2024-03-31",
                    "2024-03-31",
                    "2024-04-30",
                    "2024-04-30",
                    "2024-04-30",
                    "2024-04-30",
                ]
            ),
            "realized_label_date": pd.to_datetime(
                [
                    "2024-03-31",
                    "2024-03-31",
                    "2024-03-31",
                    "2024-03-31",
                    "2024-04-30",
                    "2024-04-30",
                    "2024-04-30",
                    "2024-04-30",
                    "2024-05-31",
                    "2024-05-31",
                    "2024-05-31",
                    "2024-05-31",
                ]
            ),
            "benchmark_ticker": ["SPY"] * 12,
            "sector": ["Technology"] * 12,
            "industry": ["Software"] * 12,
            "true_label": [1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0],
            "forward_raw_return": [0.1] * 12,
            "forward_benchmark_return": [0.03] * 12,
            "forward_excess_return": [0.07] * 12,
            "split": ["train"] * 4 + ["test"] * 8,
            "fold_id": ["fold_001"] * 8 + ["fold_002"] * 4,
            "fold_index": [1] * 8 + [2] * 4,
            "fold_scheme": ["expanding_walk_forward"] * 12,
            "train_window_start": pd.to_datetime(["2024-01-31"] * 12),
            "train_window_end": pd.to_datetime(["2024-02-29"] * 8 + ["2024-03-31"] * 4),
            "validation_window_start": [pd.NaT] * 12,
            "validation_window_end": [pd.NaT] * 12,
            "test_window_start": pd.to_datetime(
                ["2024-02-29"] * 4 + ["2024-03-31"] * 4 + ["2024-04-30"] * 4
            ),
            "test_window_end": pd.to_datetime(
                ["2024-02-29"] * 4 + ["2024-03-31"] * 4 + ["2024-04-30"] * 4
            ),
            "model_feature_non_missing_count": [10] * 12,
            "model_type": ["logistic_regression"] * 12,
            "predicted_probability": [0.9, 0.8, 0.2, 0.1, 0.7, 0.4, 0.9, 0.3, 0.2, 0.95, 0.8, 0.1],
            "predicted_class": [1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0],
            "deterministic_composite_score": [0.6] * 12,
            "deterministic_selected_top_n": [True, True, False, False] * 3,
        }
    )


def test_build_model_signal_rankings_filters_aggregated_oos_splits_and_ranks_scores() -> None:
    """Only aggregated out-of-sample rows should be used for model-driven ranking."""
    rankings, metadata = build_model_signal_rankings(
        _predictions_fixture(),
        model_config=_model_config(),
        backtest_config=_backtest_config(),
    )

    assert set(rankings["split"].unique()) == {"test"}
    assert pd.Timestamp("2024-02-29") not in set(rankings["date"])

    march = rankings.loc[rankings["date"] == pd.Timestamp("2024-03-31")]
    assert march.sort_values("score_rank")["ticker"].tolist() == ["CCC", "AAA", "BBB", "DDD"]
    assert march["selected_top_n"].sum() == 2
    assert metadata["prediction_splits"] == ["test"]
    assert metadata["selection_top_n"] == 2
    assert metadata["model_type"] == "logistic_regression"


def test_build_model_signal_rankings_rejects_duplicate_keys() -> None:
    """Duplicate ticker-date prediction rows should fail before ranking."""
    predictions = pd.concat([_predictions_fixture(), _predictions_fixture().iloc[[4]]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicate keys"):
        build_model_signal_rankings(
            predictions,
            model_config=_model_config(),
            backtest_config=_backtest_config(),
        )
