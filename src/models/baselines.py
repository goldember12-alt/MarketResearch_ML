"""Baseline model training and prediction helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from src.models.config import ModelPipelineConfig
from src.models.evaluation import build_metrics_by_split
from src.models.preprocessing import FittedPreprocessor, fit_preprocessor, transform_features
from src.models.qc import validate_training_targets


@dataclass(frozen=True)
class ModelRunArtifacts:
    """Outputs produced by one baseline model fit."""

    train_predictions: pd.DataFrame
    test_predictions: pd.DataFrame
    feature_importance: pd.DataFrame
    metadata: dict[str, Any]
    preprocessor: FittedPreprocessor


def _create_estimator(model_type: str, config: ModelPipelineConfig):
    """Instantiate the configured baseline estimator."""
    if model_type == "logistic_regression":
        params = config.logistic_regression
        logistic_kwargs: dict[str, Any] = {
            "C": params.c,
            "solver": params.solver,
            "max_iter": params.max_iter,
            "random_state": config.execution.random_state,
        }
        if params.penalty != "l2":
            logistic_kwargs["penalty"] = params.penalty
        return LogisticRegression(**logistic_kwargs)
    if model_type == "random_forest":
        params = config.random_forest
        return RandomForestClassifier(
            n_estimators=params.n_estimators,
            max_depth=params.max_depth,
            min_samples_leaf=params.min_samples_leaf,
            max_features=params.max_features,
            random_state=config.execution.random_state,
            n_jobs=1,
        )
    raise ValueError(f"Unsupported model_type: {model_type}")


def _feature_importance_frame(model_type: str, estimator, feature_columns: tuple[str, ...]) -> pd.DataFrame:
    """Build the canonical feature-importance export for one fitted model."""
    if model_type == "logistic_regression":
        signed = estimator.coef_.ravel()
        importance = np.abs(signed)
        frame = pd.DataFrame(
            {
                "feature": list(feature_columns),
                "importance": importance,
                "signed_importance": signed,
                "importance_type": "standardized_logistic_coefficient",
                "model_type": model_type,
            }
        )
    elif model_type == "random_forest":
        frame = pd.DataFrame(
            {
                "feature": list(feature_columns),
                "importance": estimator.feature_importances_,
                "signed_importance": estimator.feature_importances_,
                "importance_type": "impurity_importance",
                "model_type": model_type,
            }
        )
    else:
        raise ValueError(f"Unsupported model_type: {model_type}")

    return frame.sort_values(["importance", "feature"], ascending=[False, True]).reset_index(drop=True)


def _build_prediction_frame(
    frame: pd.DataFrame,
    *,
    fitted: FittedPreprocessor,
    estimator,
    threshold: float,
    model_type: str,
) -> pd.DataFrame:
    """Score one split and return an auditable prediction table."""
    matrix = transform_features(frame, fitted)
    probabilities = estimator.predict_proba(matrix)[:, 1]
    predicted_class = (probabilities >= threshold).astype(int)

    predictions = frame[
        [
            "ticker",
            "date",
            "realized_label_date",
            "benchmark_ticker",
            "sector",
            "industry",
            "true_label",
            "forward_raw_return",
            "forward_benchmark_return",
            "forward_excess_return",
            "split",
            "model_feature_non_missing_count",
        ]
    ].copy()
    predictions["model_type"] = model_type
    predictions["predicted_probability"] = probabilities
    predictions["predicted_class"] = predicted_class
    if "deterministic_composite_score" in frame.columns:
        predictions["deterministic_composite_score"] = frame["deterministic_composite_score"].to_numpy()
    if "deterministic_selected_top_n" in frame.columns:
        predictions["deterministic_selected_top_n"] = (
            frame["deterministic_selected_top_n"].astype("boolean").to_numpy()
        )
    if "deterministic_score_rank" in frame.columns:
        predictions["deterministic_score_rank"] = frame["deterministic_score_rank"].to_numpy()
    if "deterministic_score_rank_pct" in frame.columns:
        predictions["deterministic_score_rank_pct"] = frame["deterministic_score_rank_pct"].to_numpy()
    return predictions


def run_baseline_model(
    dataset: pd.DataFrame,
    *,
    model_type: str,
    config: ModelPipelineConfig,
) -> ModelRunArtifacts:
    """Fit one baseline model using train-only preprocessing and emit predictions."""
    train_frame = dataset.loc[dataset["split"] == "train"].copy().reset_index(drop=True)
    validation_frame = dataset.loc[dataset["split"] == "validation"].copy().reset_index(drop=True)
    test_frame = dataset.loc[dataset["split"] == "test"].copy().reset_index(drop=True)

    validate_training_targets(train_frame)
    fitted = fit_preprocessor(
        train_frame,
        feature_columns=config.dataset.feature_columns,
        config=config,
    )

    estimator = _create_estimator(model_type, config)
    train_matrix = transform_features(train_frame, fitted)
    estimator.fit(train_matrix, train_frame["true_label"].astype(int).to_numpy())

    train_predictions = _build_prediction_frame(
        train_frame,
        fitted=fitted,
        estimator=estimator,
        threshold=config.classification.class_threshold,
        model_type=model_type,
    )
    validation_predictions = _build_prediction_frame(
        validation_frame,
        fitted=fitted,
        estimator=estimator,
        threshold=config.classification.class_threshold,
        model_type=model_type,
    )
    test_predictions = _build_prediction_frame(
        test_frame,
        fitted=fitted,
        estimator=estimator,
        threshold=config.classification.class_threshold,
        model_type=model_type,
    )
    combined_test_predictions = pd.concat(
        [validation_predictions, test_predictions],
        ignore_index=True,
    )

    all_predictions = pd.concat([train_predictions, combined_test_predictions], ignore_index=True)
    metrics_by_split = build_metrics_by_split(all_predictions)
    feature_importance = _feature_importance_frame(model_type, estimator, config.dataset.feature_columns)

    metadata = {
        "model_type": model_type,
        "model_hyperparameters": {
            "logistic_regression": {
                "penalty": config.logistic_regression.penalty,
                "c": config.logistic_regression.c,
                "solver": config.logistic_regression.solver,
                "max_iter": config.logistic_regression.max_iter,
            },
            "random_forest": {
                "n_estimators": config.random_forest.n_estimators,
                "max_depth": config.random_forest.max_depth,
                "min_samples_leaf": config.random_forest.min_samples_leaf,
                "max_features": config.random_forest.max_features,
            },
        }[model_type],
        "preprocessing": {
            "numeric_imputation_strategy": config.preprocessing.numeric_imputation_strategy,
            "scale_numeric": config.preprocessing.scale_numeric,
            "fit_row_count": int(len(train_frame)),
            "fit_decision_start": train_frame["date"].min().date().isoformat(),
            "fit_decision_end": train_frame["date"].max().date().isoformat(),
        },
        "classification_threshold": config.classification.class_threshold,
        "metrics_by_split": metrics_by_split,
    }
    return ModelRunArtifacts(
        train_predictions=train_predictions,
        test_predictions=combined_test_predictions,
        feature_importance=feature_importance,
        metadata=metadata,
        preprocessor=fitted,
    )
