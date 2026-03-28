"""QC helpers for feature-generation outputs."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.data.standardize import find_duplicate_keys


def build_feature_qc_summary(
    feature_panel: pd.DataFrame,
    *,
    feature_columns: list[str],
    feature_groups: dict[str, list[str]],
) -> dict[str, Any]:
    """Build a compact QC summary for the feature panel."""
    duplicates = find_duplicate_keys(feature_panel, ["ticker", "date"])
    feature_cell_count = len(feature_panel) * len(feature_columns)

    by_date = (
        feature_panel.groupby("date")[feature_columns]
        .apply(lambda frame: int(frame.isna().sum().sum()))
        .reset_index(name="missing_feature_cells")
    )
    by_date["feature_cell_count"] = len(feature_columns) * feature_panel["ticker"].nunique()
    by_date["missing_ratio"] = by_date["missing_feature_cells"] / by_date["feature_cell_count"].replace(0, 1)

    return {
        "dataset_name": "feature_panel",
        "row_count": int(len(feature_panel)),
        "feature_column_count": int(len(feature_columns)),
        "feature_columns": feature_columns,
        "feature_groups": feature_groups,
        "unique_ticker_count": int(feature_panel["ticker"].nunique(dropna=True)),
        "unique_date_count": int(feature_panel["date"].nunique(dropna=True)),
        "min_date": feature_panel["date"].min().date().isoformat(),
        "max_date": feature_panel["date"].max().date().isoformat(),
        "duplicate_key_count": int(len(duplicates[["ticker", "date"]].drop_duplicates()))
        if not duplicates.empty
        else 0,
        "feature_cell_count": int(feature_cell_count),
        "feature_missing_cell_count": int(feature_panel[feature_columns].isna().sum().sum()),
        "feature_missing_by_date": [
            {
                "date": row["date"].date().isoformat(),
                "missing_feature_cells": int(row["missing_feature_cells"]),
                "feature_cell_count": int(row["feature_cell_count"]),
                "missing_ratio": float(row["missing_ratio"]),
            }
            for _, row in by_date.iterrows()
        ],
    }


def build_feature_missingness_summary(
    feature_panel: pd.DataFrame,
    *,
    feature_columns: list[str],
    feature_groups: dict[str, list[str]],
) -> pd.DataFrame:
    """Build a per-feature missingness summary table."""
    group_lookup = {
        feature_name: group_name
        for group_name, features in feature_groups.items()
        for feature_name in features
    }
    summary_rows: list[dict[str, Any]] = []
    row_count = max(len(feature_panel), 1)
    for feature_name in feature_columns:
        missing_count = int(feature_panel[feature_name].isna().sum())
        first_valid = feature_panel.loc[feature_panel[feature_name].notna(), "date"].min()
        summary_rows.append(
            {
                "feature_name": feature_name,
                "feature_group": group_lookup.get(feature_name, "unknown"),
                "missing_count": missing_count,
                "non_missing_count": int(row_count - missing_count),
                "missing_ratio": missing_count / row_count,
                "first_valid_date": (
                    "" if pd.isna(first_valid) else pd.Timestamp(first_valid).date().isoformat()
                ),
            }
        )
    return pd.DataFrame(summary_rows).sort_values(["feature_group", "feature_name"]).reset_index(
        drop=True
    )
