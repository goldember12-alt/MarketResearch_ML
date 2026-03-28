"""QC helpers for deterministic signal artifacts."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.data.standardize import find_duplicate_keys


def build_signal_qc_summary(
    rankings: pd.DataFrame,
    *,
    configured_features: list[str],
    selection_top_n: int,
) -> dict[str, Any]:
    """Build a compact QC summary for signal rankings."""
    duplicates = find_duplicate_keys(rankings, ["ticker", "date"])
    selection_by_date = (
        rankings.groupby("date", as_index=False)
        .agg(
            scored_row_count=("composite_score", lambda series: int(series.notna().sum())),
            selected_count=("selected_top_n", lambda series: int(series.sum())),
            min_score=("composite_score", "min"),
            max_score=("composite_score", "max"),
        )
        .sort_values("date")
    )

    return {
        "dataset_name": "signal_rankings",
        "row_count": int(len(rankings)),
        "unique_ticker_count": int(rankings["ticker"].nunique(dropna=True)),
        "unique_date_count": int(rankings["date"].nunique(dropna=True)),
        "min_date": rankings["date"].min().date().isoformat(),
        "max_date": rankings["date"].max().date().isoformat(),
        "duplicate_key_count": int(len(duplicates[["ticker", "date"]].drop_duplicates()))
        if not duplicates.empty
        else 0,
        "configured_feature_count": len(configured_features),
        "selection_top_n": selection_top_n,
        "fully_scored_row_count": int(rankings["composite_score"].notna().sum()),
        "selection_by_date": [
            {
                "date": row["date"].date().isoformat(),
                "scored_row_count": int(row["scored_row_count"]),
                "selected_count": int(row["selected_count"]),
                "min_score": None if pd.isna(row["min_score"]) else float(row["min_score"]),
                "max_score": None if pd.isna(row["max_score"]) else float(row["max_score"]),
            }
            for _, row in selection_by_date.iterrows()
        ],
    }


def build_signal_selection_summary(rankings: pd.DataFrame) -> pd.DataFrame:
    """Build a simple per-date summary of ranked and selected names."""
    rows: list[dict[str, Any]] = []
    for date, month in rankings.groupby("date", sort=False):
        selected_ranks = month.loc[month["selected_top_n"], "score_rank"].dropna()
        rows.append(
            {
                "date": date,
                "scored_row_count": int(month["composite_score"].notna().sum()),
                "selected_count": int(month["selected_top_n"].sum()),
                "top_score": month["composite_score"].max(),
                "bottom_selected_rank": (
                    float(selected_ranks.max()) if not selected_ranks.empty else float("nan")
                ),
            }
        )
    summary = pd.DataFrame(rows).sort_values("date")
    summary["date"] = summary["date"].dt.date.astype(str)
    return summary.reset_index(drop=True)
