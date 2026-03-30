"""Train-only preprocessing helpers for modeling baselines."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.models.config import ModelPipelineConfig


@dataclass(frozen=True)
class FittedPreprocessor:
    """Resolved train-only preprocessing pipeline and feature metadata."""

    pipeline: Pipeline
    feature_columns: tuple[str, ...]


def fit_preprocessor(
    train_frame: pd.DataFrame,
    *,
    feature_columns: tuple[str, ...],
    config: ModelPipelineConfig,
) -> FittedPreprocessor:
    """Fit the numeric preprocessing pipeline on training data only."""
    steps: list[tuple[str, object]] = [
        (
            "imputer",
            SimpleImputer(
                strategy=config.preprocessing.numeric_imputation_strategy,
                keep_empty_features=True,
            ),
        )
    ]
    if config.preprocessing.scale_numeric:
        steps.append(("scaler", StandardScaler()))

    pipeline = Pipeline(steps)
    pipeline.fit(train_frame.loc[:, list(feature_columns)])
    return FittedPreprocessor(pipeline=pipeline, feature_columns=feature_columns)


def transform_features(
    frame: pd.DataFrame,
    fitted: FittedPreprocessor,
) -> np.ndarray:
    """Transform a frame into the train-aligned numeric model matrix."""
    transformed = fitted.pipeline.transform(frame.loc[:, list(fitted.feature_columns)])
    return np.asarray(transformed, dtype="float64")
