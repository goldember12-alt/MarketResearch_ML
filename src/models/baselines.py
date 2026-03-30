"""Baseline model training and prediction helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from src.data.standardize import assert_unique_keys
from src.models.config import ModelPipelineConfig
from src.models.evaluation import build_classification_metrics, build_metrics_by_split
from src.models.preprocessing import FittedPreprocessor, fit_preprocessor, transform_features
from src.models.qc import validate_model_folds, validate_training_targets
from src.models.windows import ModelFoldWindow, build_model_folds


@dataclass(frozen=True)
class ModelRunArtifacts:
    """Outputs produced by one baseline model run."""

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


def _aggregate_feature_importance(feature_importance_frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Aggregate per-fold feature importance into the canonical export."""
    combined = pd.concat(feature_importance_frames, ignore_index=True)
    aggregated = (
        combined.groupby(["feature", "importance_type", "model_type"], as_index=False)
        .agg(
            importance=("importance", "mean"),
            signed_importance=("signed_importance", "mean"),
            window_count=("fold_id", "nunique"),
        )
        .assign(aggregation_method="mean_across_folds")
    )
    return aggregated.sort_values(["importance", "feature"], ascending=[False, True]).reset_index(
        drop=True
    )


def _build_prediction_frame(
    frame: pd.DataFrame,
    *,
    fitted: FittedPreprocessor,
    estimator,
    threshold: float,
    model_type: str,
    split_name: str,
    fold: ModelFoldWindow,
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
            "model_feature_non_missing_count",
        ]
    ].copy()
    predictions["split"] = split_name
    predictions["fold_id"] = fold.fold_id
    predictions["fold_index"] = fold.fold_index
    predictions["fold_scheme"] = fold.scheme
    predictions["train_window_start"] = fold.train_start_date
    predictions["train_window_end"] = fold.train_end_date
    predictions["validation_window_start"] = (
        pd.Timestamp(fold.validation_start_date)
        if fold.validation_start_date is not None
        else pd.NaT
    )
    predictions["validation_window_end"] = (
        pd.Timestamp(fold.validation_end_date)
        if fold.validation_end_date is not None
        else pd.NaT
    )
    predictions["test_window_start"] = fold.test_start_date
    predictions["test_window_end"] = fold.test_end_date
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


def _slice_fold_frame(
    dataset: pd.DataFrame,
    *,
    dates: tuple[pd.Timestamp, ...],
) -> pd.DataFrame:
    """Slice a deterministic fold frame by its decision-date tuple."""
    if not dates:
        return pd.DataFrame(columns=dataset.columns)
    return dataset.loc[dataset["date"].isin(dates)].copy().reset_index(drop=True)


def _build_preprocessing_metadata(
    *,
    config: ModelPipelineConfig,
    fold_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize per-fold preprocessing fits for metadata export."""
    fit_row_counts = [summary["train_row_count"] for summary in fold_summaries]
    return {
        "numeric_imputation_strategy": config.preprocessing.numeric_imputation_strategy,
        "scale_numeric": config.preprocessing.scale_numeric,
        "fit_strategy": "fit_separately_per_fold_on_training_rows_only",
        "fit_window_count": len(fold_summaries),
        "fit_row_count_min": int(min(fit_row_counts)),
        "fit_row_count_max": int(max(fit_row_counts)),
    }


def run_baseline_model(
    dataset: pd.DataFrame,
    *,
    model_type: str,
    config: ModelPipelineConfig,
) -> ModelRunArtifacts:
    """Fit one baseline model using chronology-safe fold-level preprocessing and scoring."""
    folds = build_model_folds(dataset["date"], config)
    validate_model_folds(folds)

    train_prediction_frames: list[pd.DataFrame] = []
    test_prediction_frames: list[pd.DataFrame] = []
    feature_importance_frames: list[pd.DataFrame] = []
    fold_summaries: list[dict[str, Any]] = []
    last_fitted: FittedPreprocessor | None = None

    for fold in folds:
        train_frame = _slice_fold_frame(dataset, dates=fold.train_dates)
        validation_frame = _slice_fold_frame(dataset, dates=fold.validation_dates)
        test_frame = _slice_fold_frame(dataset, dates=fold.test_dates)

        validate_training_targets(train_frame)
        fitted = fit_preprocessor(
            train_frame,
            feature_columns=config.dataset.feature_columns,
            config=config,
        )

        estimator = _create_estimator(model_type, config)
        train_matrix = transform_features(train_frame, fitted)
        estimator.fit(train_matrix, train_frame["true_label"].astype(int).to_numpy())

        fold_train_predictions = _build_prediction_frame(
            train_frame,
            fitted=fitted,
            estimator=estimator,
            threshold=config.classification.class_threshold,
            model_type=model_type,
            split_name="train",
            fold=fold,
        )
        fold_prediction_frames: list[pd.DataFrame] = []
        if not validation_frame.empty:
            fold_prediction_frames.append(
                _build_prediction_frame(
                    validation_frame,
                    fitted=fitted,
                    estimator=estimator,
                    threshold=config.classification.class_threshold,
                    model_type=model_type,
                    split_name="validation",
                    fold=fold,
                )
            )
        if not test_frame.empty:
            fold_prediction_frames.append(
                _build_prediction_frame(
                    test_frame,
                    fitted=fitted,
                    estimator=estimator,
                    threshold=config.classification.class_threshold,
                    model_type=model_type,
                    split_name="test",
                    fold=fold,
                )
            )
        fold_oos_predictions = pd.concat(fold_prediction_frames, ignore_index=True)

        fold_all_predictions = pd.concat(
            [fold_train_predictions, fold_oos_predictions],
            ignore_index=True,
        )
        fold_metrics_by_split = build_metrics_by_split(fold_all_predictions)
        fold_oos_metrics = build_classification_metrics(
            fold_oos_predictions,
            score_column="predicted_probability",
            class_column="predicted_class",
        )

        fold_feature_importance = _feature_importance_frame(
            model_type,
            estimator,
            config.dataset.feature_columns,
        ).assign(fold_id=fold.fold_id)

        train_prediction_frames.append(fold_train_predictions)
        test_prediction_frames.append(fold_oos_predictions)
        feature_importance_frames.append(fold_feature_importance)
        fold_summaries.append(
            {
                "fold_id": fold.fold_id,
                "fold_index": fold.fold_index,
                "scheme": fold.scheme,
                "train_decision_start": fold.train_start_date.date().isoformat(),
                "train_decision_end": fold.train_end_date.date().isoformat(),
                "validation_decision_start": (
                    None
                    if fold.validation_start_date is None
                    else fold.validation_start_date.date().isoformat()
                ),
                "validation_decision_end": (
                    None
                    if fold.validation_end_date is None
                    else fold.validation_end_date.date().isoformat()
                ),
                "test_decision_start": fold.test_start_date.date().isoformat(),
                "test_decision_end": fold.test_end_date.date().isoformat(),
                "train_row_count": int(len(train_frame)),
                "validation_row_count": int(len(validation_frame)),
                "test_row_count": int(len(test_frame)),
                "preprocessing_fit_row_count": int(len(train_frame)),
                "metrics_by_split": fold_metrics_by_split,
                "out_of_sample_metrics": fold_oos_metrics,
            }
        )
        last_fitted = fitted

    train_predictions = pd.concat(train_prediction_frames, ignore_index=True)
    test_predictions = pd.concat(test_prediction_frames, ignore_index=True)
    assert_unique_keys(test_predictions, ["ticker", "date"], "aggregated_oos_predictions")

    all_predictions = pd.concat([train_predictions, test_predictions], ignore_index=True)
    metrics_by_split = build_metrics_by_split(all_predictions)
    out_of_sample_metrics = build_classification_metrics(
        test_predictions,
        score_column="predicted_probability",
        class_column="predicted_class",
    )
    feature_importance = _aggregate_feature_importance(feature_importance_frames)

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
        "preprocessing": _build_preprocessing_metadata(
            config=config,
            fold_summaries=fold_summaries,
        ),
        "classification_threshold": config.classification.class_threshold,
        "metrics_by_split": metrics_by_split,
        "out_of_sample_metrics": out_of_sample_metrics,
        "folds": fold_summaries,
    }
    if last_fitted is None:
        raise ValueError("No folds were fitted for the requested model run.")
    return ModelRunArtifacts(
        train_predictions=train_predictions,
        test_predictions=test_predictions,
        feature_importance=feature_importance,
        metadata=metadata,
        preprocessor=last_fitted,
    )
