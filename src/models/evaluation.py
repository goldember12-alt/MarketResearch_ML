"""Evaluation helpers for classification-style modeling baselines."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def _safe_score(score_fn, y_true: np.ndarray, values: np.ndarray) -> float | None:
    """Return a metric when well-defined, otherwise null."""
    unique_classes = np.unique(y_true)
    if unique_classes.size < 2:
        return None
    try:
        return float(score_fn(y_true, values))
    except ValueError:
        return None


def build_classification_metrics(
    frame: pd.DataFrame,
    *,
    score_column: str,
    class_column: str,
) -> dict[str, Any]:
    """Compute compact binary-classification metrics for one prediction table."""
    if frame.empty:
        return {"row_count": 0}

    y_true = frame["true_label"].astype(int).to_numpy()
    y_pred = frame[class_column].astype(int).to_numpy()
    score_mask = frame[score_column].notna()

    metrics: dict[str, Any] = {
        "row_count": int(len(frame)),
        "positive_label_count": int(y_true.sum()),
        "positive_label_rate": float(y_true.mean()),
        "predicted_positive_count": int(y_pred.sum()),
        "predicted_positive_rate": float(y_pred.mean()),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
    }

    if score_mask.any():
        scored_true = frame.loc[score_mask, "true_label"].astype(int).to_numpy()
        scored_values = frame.loc[score_mask, score_column].to_numpy(dtype="float64", copy=False)
        metrics["scored_row_count"] = int(score_mask.sum())
        metrics["roc_auc"] = _safe_score(roc_auc_score, scored_true, scored_values)
        metrics["average_precision"] = _safe_score(
            average_precision_score,
            scored_true,
            scored_values,
        )
    else:
        metrics["scored_row_count"] = 0
        metrics["roc_auc"] = None
        metrics["average_precision"] = None

    return metrics


def build_metrics_by_split(predictions: pd.DataFrame) -> dict[str, Any]:
    """Build model and deterministic-baseline metrics by split."""
    metrics_by_split: dict[str, Any] = {}
    for split, frame in predictions.groupby("split", sort=False):
        split_metrics: dict[str, Any] = {
            "model": build_classification_metrics(
                frame,
                score_column="predicted_probability",
                class_column="predicted_class",
            )
        }
        if {
            "deterministic_composite_score",
            "deterministic_selected_top_n",
        }.issubset(frame.columns):
            deterministic_frame = frame.dropna(
                subset=["deterministic_selected_top_n"]
            ).copy()
            if not deterministic_frame.empty:
                deterministic_frame["deterministic_selected_top_n"] = deterministic_frame[
                    "deterministic_selected_top_n"
                ].astype(int)
                split_metrics["deterministic_baseline"] = build_classification_metrics(
                    deterministic_frame,
                    score_column="deterministic_composite_score",
                    class_column="deterministic_selected_top_n",
                )
        metrics_by_split[split] = split_metrics
    return metrics_by_split
