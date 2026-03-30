"""Validation helpers for the modeling-baselines stage."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.data.standardize import assert_unique_keys
from src.models.config import ModelPipelineConfig


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


def validate_split_dataset(frame: pd.DataFrame) -> None:
    """Validate that split assignment remains strictly chronological."""
    required_splits = {"train", "validation", "test"}
    observed_splits = set(frame["split"].unique())
    if observed_splits != required_splits:
        raise ValueError(
            f"Modeling dataset must include train, validation, and test rows. Found {observed_splits}."
        )

    split_dates = (
        frame.groupby("split", sort=False)["date"]
        .agg(["min", "max", "nunique"])
        .to_dict(orient="index")
    )
    if split_dates["train"]["max"] >= split_dates["validation"]["min"]:
        raise ValueError("Training dates must end before validation dates begin.")
    if split_dates["validation"]["max"] >= split_dates["test"]["min"]:
        raise ValueError("Validation dates must end before test dates begin.")
    if split_dates["train"]["max"] >= split_dates["test"]["min"]:
        raise ValueError("Training and test dates must not overlap.")


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
    split_counts = (
        dataset.groupby("split", sort=False)
        .agg(
            row_count=("ticker", "size"),
            unique_dates=("date", "nunique"),
            positive_labels=("true_label", lambda series: int(series.astype(int).sum())),
        )
        .to_dict(orient="index")
    )

    split_date_ranges = {
        split: {
            "decision_start": frame["date"].min().date().isoformat(),
            "decision_end": frame["date"].max().date().isoformat(),
            "realized_start": frame["realized_label_date"].min().date().isoformat(),
            "realized_end": frame["realized_label_date"].max().date().isoformat(),
        }
        for split, frame in dataset.groupby("split", sort=False)
    }

    return {
        "configured_feature_count": len(feature_columns),
        "feature_columns": list(feature_columns),
        "label_target_type": label_definition["target_type"],
        "deterministic_baseline_available": deterministic_baseline_available,
        "row_counts_by_split": split_counts,
        "date_ranges_by_split": split_date_ranges,
        "dropped_rows": dropped_rows_summary,
    }
