"""Validation helpers for the modeling-baselines stage."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.data.standardize import assert_unique_keys
from src.models.config import ModelPipelineConfig
from src.models.windows import ModelFoldWindow


def validate_input_keys(
    *,
    feature_panel: pd.DataFrame,
    monthly_panel: pd.DataFrame,
    signal_rankings: pd.DataFrame | None,
) -> None:
    """Validate deterministic-key contracts for modeling inputs."""
    assert_unique_keys(feature_panel, ["ticker", "date"], "feature_panel")
    assert_unique_keys(monthly_panel, ["ticker", "date"], "monthly_panel")
    if signal_rankings is not None:
        assert_unique_keys(signal_rankings, ["ticker", "date"], "signal_rankings")


def validate_feature_columns(frame: pd.DataFrame, feature_columns: tuple[str, ...]) -> None:
    """Raise a clear error when configured model features are missing."""
    missing = [column for column in feature_columns if column not in frame.columns]
    if missing:
        raise ValueError(
            "Configured model feature columns are missing from the modeling dataset: "
            f"{missing}"
        )


def validate_split_windows(config: ModelPipelineConfig) -> None:
    """Validate chronological ordering and non-overlap of configured split windows."""
    if config.splits.scheme != "fixed_date_windows":
        return

    train_start = pd.Timestamp(config.splits.train.start_date)
    train_end = pd.Timestamp(config.splits.train.end_date)
    validation_start = pd.Timestamp(config.splits.validation.start_date)
    validation_end = pd.Timestamp(config.splits.validation.end_date)
    test_start = pd.Timestamp(config.splits.test.start_date)
    test_end = pd.Timestamp(config.splits.test.end_date)

    if not train_start <= train_end:
        raise ValueError("Training split start_date must be on or before end_date.")
    if not validation_start <= validation_end:
        raise ValueError("Validation split start_date must be on or before end_date.")
    if not test_start <= test_end:
        raise ValueError("Test split start_date must be on or before end_date.")
    if not train_end < validation_start:
        raise ValueError("Training and validation windows must not overlap.")
    if not validation_end < test_start:
        raise ValueError("Validation and test windows must not overlap.")


def validate_modeling_dataset(frame: pd.DataFrame) -> None:
    """Validate that the filtered modeling dataset is non-empty and uniquely keyed."""
    if frame.empty:
        raise ValueError("Modeling dataset is empty after label and feature eligibility filters.")
    assert_unique_keys(frame, ["ticker", "date"], "modeling_dataset")


def validate_model_folds(folds: tuple[ModelFoldWindow, ...]) -> None:
    """Validate chronological ordering and held-out uniqueness across folds."""
    if not folds:
        raise ValueError("At least one model fold is required.")

    heldout_dates: list[pd.Timestamp] = []
    for fold in folds:
        if not fold.train_dates:
            raise ValueError(f"{fold.fold_id} has no training dates.")
        if not fold.test_dates:
            raise ValueError(f"{fold.fold_id} has no test dates.")
        if fold.validation_dates and fold.train_end_date >= fold.validation_start_date:
            raise ValueError(f"{fold.fold_id} training dates overlap validation dates.")
        if fold.validation_dates and fold.validation_end_date >= fold.test_start_date:
            raise ValueError(f"{fold.fold_id} validation dates overlap test dates.")
        if fold.train_end_date >= fold.test_start_date:
            raise ValueError(f"{fold.fold_id} training dates overlap held-out test dates.")
        heldout_dates.extend(fold.prediction_dates)

    heldout_index = pd.Index(heldout_dates)
    if heldout_index.has_duplicates:
        duplicate_dates = heldout_index[heldout_index.duplicated()].strftime("%Y-%m-%d").tolist()
        raise ValueError(
            "Model folds produce duplicate held-out decision dates across windows: "
            f"{duplicate_dates}"
        )


def validate_training_targets(frame: pd.DataFrame) -> None:
    """Ensure the training split contains both target classes."""
    unique_targets = sorted(frame["true_label"].dropna().astype(int).unique().tolist())
    if unique_targets != [0, 1]:
        raise ValueError(
            "The training split must contain both binary classes for model fitting. "
            f"Observed classes: {unique_targets}"
        )


def build_qc_summary(
    *,
    dataset: pd.DataFrame,
    dropped_rows_summary: dict[str, int],
    feature_columns: tuple[str, ...],
    label_definition: dict[str, Any],
    deterministic_baseline_available: bool,
) -> dict[str, Any]:
    """Build a compact QC summary for model metadata."""
    return {
        "eligible_row_count": int(len(dataset)),
        "eligible_unique_dates": int(dataset["date"].nunique()),
        "eligible_positive_labels": int(dataset["true_label"].astype(int).sum()),
        "eligible_decision_date_range": {
            "decision_start": dataset["date"].min().date().isoformat(),
            "decision_end": dataset["date"].max().date().isoformat(),
            "realized_start": dataset["realized_label_date"].min().date().isoformat(),
            "realized_end": dataset["realized_label_date"].max().date().isoformat(),
        },
        "configured_feature_count": len(feature_columns),
        "feature_columns": list(feature_columns),
        "label_target_type": label_definition["target_type"],
        "deterministic_baseline_available": deterministic_baseline_available,
        "dropped_rows": dropped_rows_summary,
    }
