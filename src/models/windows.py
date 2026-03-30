"""Chronology-safe fold generation for fixed and walk-forward modeling schemes."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.models.config import ModelPipelineConfig


@dataclass(frozen=True)
class ModelFoldWindow:
    """One deterministic fold definition for model fitting and scoring."""

    fold_id: str
    fold_index: int
    scheme: str
    train_dates: tuple[pd.Timestamp, ...]
    validation_dates: tuple[pd.Timestamp, ...]
    test_dates: tuple[pd.Timestamp, ...]

    @property
    def train_start_date(self) -> pd.Timestamp:
        """Return the earliest decision date in the training window."""
        return self.train_dates[0]

    @property
    def train_end_date(self) -> pd.Timestamp:
        """Return the latest decision date in the training window."""
        return self.train_dates[-1]

    @property
    def validation_start_date(self) -> pd.Timestamp | None:
        """Return the earliest validation date when present."""
        return self.validation_dates[0] if self.validation_dates else None

    @property
    def validation_end_date(self) -> pd.Timestamp | None:
        """Return the latest validation date when present."""
        return self.validation_dates[-1] if self.validation_dates else None

    @property
    def test_start_date(self) -> pd.Timestamp:
        """Return the earliest held-out test date."""
        return self.test_dates[0]

    @property
    def test_end_date(self) -> pd.Timestamp:
        """Return the latest held-out test date."""
        return self.test_dates[-1]

    @property
    def prediction_dates(self) -> tuple[pd.Timestamp, ...]:
        """Return the ordered held-out dates emitted by the fold."""
        return self.validation_dates + self.test_dates


def _normalized_unique_dates(decision_dates: pd.Series | pd.Index) -> tuple[pd.Timestamp, ...]:
    """Return sorted unique decision dates as timestamps."""
    dates = pd.Index(pd.to_datetime(decision_dates)).drop_duplicates().sort_values()
    return tuple(pd.Timestamp(value) for value in dates)


def _build_fixed_date_fold(
    available_dates: tuple[pd.Timestamp, ...],
    config: ModelPipelineConfig,
) -> tuple[ModelFoldWindow, ...]:
    """Build the legacy fixed train/validation/test split as one fold."""
    train_dates = tuple(
        date
        for date in available_dates
        if pd.Timestamp(config.splits.train.start_date)
        <= date
        <= pd.Timestamp(config.splits.train.end_date)
    )
    validation_dates = tuple(
        date
        for date in available_dates
        if pd.Timestamp(config.splits.validation.start_date)
        <= date
        <= pd.Timestamp(config.splits.validation.end_date)
    )
    test_dates = tuple(
        date
        for date in available_dates
        if pd.Timestamp(config.splits.test.start_date)
        <= date
        <= pd.Timestamp(config.splits.test.end_date)
    )
    if not train_dates:
        raise ValueError("Configured fixed train window does not match any eligible modeling dates.")
    if not validation_dates:
        raise ValueError(
            "Configured fixed validation window does not match any eligible modeling dates."
        )
    if not test_dates:
        raise ValueError("Configured fixed test window does not match any eligible modeling dates.")

    return (
        ModelFoldWindow(
            fold_id="fold_001",
            fold_index=1,
            scheme="fixed_date_windows",
            train_dates=train_dates,
            validation_dates=validation_dates,
            test_dates=test_dates,
        ),
    )


def _build_expanding_walk_forward_folds(
    available_dates: tuple[pd.Timestamp, ...],
    config: ModelPipelineConfig,
) -> tuple[ModelFoldWindow, ...]:
    """Build expanding-window folds that emit unique held-out prediction dates."""
    settings = config.splits.walk_forward
    folds: list[ModelFoldWindow] = []
    cursor = settings.min_train_periods
    prediction_span = settings.validation_window_periods + settings.test_window_periods

    while cursor + prediction_span <= len(available_dates):
        train_dates = tuple(available_dates[:cursor])
        validation_dates = tuple(
            available_dates[cursor : cursor + settings.validation_window_periods]
        )
        test_start = cursor + settings.validation_window_periods
        test_dates = tuple(available_dates[test_start : test_start + settings.test_window_periods])
        fold_index = len(folds) + 1
        folds.append(
            ModelFoldWindow(
                fold_id=f"fold_{fold_index:03d}",
                fold_index=fold_index,
                scheme="expanding_walk_forward",
                train_dates=train_dates,
                validation_dates=validation_dates,
                test_dates=test_dates,
            )
        )
        cursor += settings.step_periods

    if not folds:
        raise ValueError(
            "Walk-forward split settings did not yield any folds from the eligible modeling dates."
        )
    return tuple(folds)


def build_model_folds(
    decision_dates: pd.Series | pd.Index,
    config: ModelPipelineConfig,
) -> tuple[ModelFoldWindow, ...]:
    """Build deterministic model folds from the configured split scheme."""
    available_dates = _normalized_unique_dates(decision_dates)
    if not available_dates:
        raise ValueError("No eligible modeling dates are available for split generation.")

    if config.splits.scheme == "fixed_date_windows":
        return _build_fixed_date_fold(available_dates, config)
    if config.splits.scheme == "expanding_walk_forward":
        return _build_expanding_walk_forward_folds(available_dates, config)
    raise ValueError(f"Unsupported modeling split scheme: {config.splits.scheme!r}")
