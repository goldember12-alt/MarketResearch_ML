"""Dataset assembly and chronological split logic for modeling baselines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.models.config import ModelPipelineConfig
from src.models.labels import build_label_table
from src.models.qc import (
    build_qc_summary,
    validate_feature_columns,
    validate_input_keys,
    validate_split_dataset,
    validate_split_windows,
)


@dataclass(frozen=True)
class ModelingDatasetBundle:
    """Resolved modeling dataset and related QC metadata."""

    dataset: pd.DataFrame
    label_metadata: dict[str, Any]
    dropped_rows_summary: dict[str, int]
    qc_summary: dict[str, Any]


def _assign_split(date: pd.Timestamp, config: ModelPipelineConfig) -> str | None:
    """Map one decision date into the configured chronological split."""
    if pd.Timestamp(config.splits.train.start_date) <= date <= pd.Timestamp(config.splits.train.end_date):
        return "train"
    if pd.Timestamp(config.splits.validation.start_date) <= date <= pd.Timestamp(
        config.splits.validation.end_date
    ):
        return "validation"
    if pd.Timestamp(config.splits.test.start_date) <= date <= pd.Timestamp(config.splits.test.end_date):
        return "test"
    return None


def build_modeling_dataset(
    *,
    feature_panel: pd.DataFrame,
    monthly_panel: pd.DataFrame,
    config: ModelPipelineConfig,
    signal_rankings: pd.DataFrame | None = None,
) -> ModelingDatasetBundle:
    """Build the modeling dataset aligned to feature rows and chronological splits."""
    validate_input_keys(
        feature_panel=feature_panel,
        monthly_panel=monthly_panel,
        signal_rankings=signal_rankings,
    )
    validate_split_windows(config)
    validate_feature_columns(feature_panel, config.dataset.feature_columns)

    label_table, label_metadata = build_label_table(monthly_panel, config.label)

    dataset = feature_panel.copy().sort_values(["date", "ticker"]).reset_index(drop=True)
    dataset = dataset.merge(
        label_table.drop(columns=["benchmark_ticker"]),
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )

    deterministic_available = False
    if signal_rankings is not None and config.deterministic_baseline.enabled:
        baseline_columns = [
            "ticker",
            "date",
            config.deterministic_baseline.score_column,
            config.deterministic_baseline.class_column,
            "score_rank",
            "score_rank_pct",
        ]
        available_baseline_columns = [
            column for column in baseline_columns if column in signal_rankings.columns
        ]
        renamed_baseline = signal_rankings[available_baseline_columns].rename(
            columns={
                config.deterministic_baseline.score_column: "deterministic_composite_score",
                config.deterministic_baseline.class_column: "deterministic_selected_top_n",
                "score_rank": "deterministic_score_rank",
                "score_rank_pct": "deterministic_score_rank_pct",
            }
        )
        dataset = dataset.merge(
            renamed_baseline,
            on=["ticker", "date"],
            how="left",
            validate="one_to_one",
        )
        deterministic_available = {
            "deterministic_composite_score",
            "deterministic_selected_top_n",
        }.issubset(dataset.columns)

    dataset["model_feature_non_missing_count"] = dataset.loc[
        :, list(config.dataset.feature_columns)
    ].notna().sum(axis=1)
    dataset["split"] = dataset["date"].map(lambda value: _assign_split(pd.Timestamp(value), config))

    dropped_rows_summary = {
        "missing_label": int(dataset["true_label"].isna().sum()),
        "missing_realized_label_date": int(dataset["realized_label_date"].isna().sum()),
        "insufficient_non_missing_features": int(
            (
                dataset["model_feature_non_missing_count"]
                < config.dataset.minimum_non_missing_features
            ).sum()
        ),
        "outside_configured_windows": int(dataset["split"].isna().sum()),
    }

    keep_mask = (
        dataset["true_label"].notna()
        & dataset["realized_label_date"].notna()
        & (
            dataset["model_feature_non_missing_count"]
            >= config.dataset.minimum_non_missing_features
        )
        & dataset["split"].notna()
    )
    modeled = dataset.loc[keep_mask].copy().reset_index(drop=True)
    modeled["true_label"] = modeled["true_label"].astype("Int64")

    validate_split_dataset(modeled)
    qc_summary = build_qc_summary(
        dataset=modeled,
        dropped_rows_summary=dropped_rows_summary,
        feature_columns=config.dataset.feature_columns,
        label_definition=label_metadata,
        deterministic_baseline_available=bool(deterministic_available),
    )
    return ModelingDatasetBundle(
        dataset=modeled,
        label_metadata=label_metadata,
        dropped_rows_summary=dropped_rows_summary,
        qc_summary=qc_summary,
    )
