"""QC summaries for processed data artifacts."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.data.standardize import find_duplicate_keys


def _to_iso_or_none(value: Any) -> str | None:
    """Convert scalar timestamps to ISO strings."""
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return str(value)


def build_dataset_qc_summary(
    frame: pd.DataFrame,
    *,
    dataset_name: str,
    id_column: str,
    key_columns: list[str],
) -> dict[str, Any]:
    """Build a lightweight QC summary suitable for JSON output."""
    duplicates = find_duplicate_keys(frame, key_columns)
    summary: dict[str, Any] = {
        "dataset_name": dataset_name,
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "columns": [str(column) for column in frame.columns],
        "unique_identifier_count": int(frame[id_column].nunique(dropna=True))
        if id_column in frame.columns
        else 0,
        "min_date": _to_iso_or_none(frame["date"].min()) if "date" in frame.columns else None,
        "max_date": _to_iso_or_none(frame["date"].max()) if "date" in frame.columns else None,
        "duplicate_key_count": int(len(duplicates[key_columns].drop_duplicates()))
        if not duplicates.empty
        else 0,
        "missing_by_column": {
            str(column): int(frame[column].isna().sum()) for column in frame.columns
        },
    }
    if id_column in frame.columns:
        summary["sample_identifiers"] = sorted(
            frame[id_column].dropna().astype(str).unique().tolist()
        )[:10]
    return summary


def build_panel_qc_summary(
    panel: pd.DataFrame,
    *,
    expected_ticker_count: int,
) -> dict[str, Any]:
    """Build panel-specific row-count and missingness diagnostics."""
    unique_dates = int(panel["date"].nunique(dropna=True))
    duplicates = find_duplicate_keys(panel, ["ticker", "date"])
    return {
        "dataset_name": "monthly_panel",
        "row_count": int(len(panel)),
        "unique_ticker_count": int(panel["ticker"].nunique(dropna=True)),
        "unique_date_count": unique_dates,
        "expected_grid_rows": int(expected_ticker_count * unique_dates),
        "duplicate_key_count": int(len(duplicates[["ticker", "date"]].drop_duplicates()))
        if not duplicates.empty
        else 0,
        "missing_adjusted_close_count": int(panel["adjusted_close"].isna().sum()),
        "missing_benchmark_return_count": int(panel["benchmark_return"].isna().sum()),
        "missing_market_cap_count": int(panel["market_cap"].isna().sum())
        if "market_cap" in panel.columns
        else 0,
        "min_date": _to_iso_or_none(panel["date"].min()),
        "max_date": _to_iso_or_none(panel["date"].max()),
    }


def build_ticker_coverage_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """Summarize per-ticker panel coverage and missingness."""
    total_dates = panel["date"].nunique(dropna=True)
    summary = (
        panel.groupby("ticker", as_index=False)
        .agg(
            first_date=("date", "min"),
            last_date=("date", "max"),
            row_count=("date", "size"),
            non_missing_adjusted_close=("adjusted_close", lambda series: int(series.notna().sum())),
            non_missing_market_cap=("market_cap", lambda series: int(series.notna().sum())),
            non_missing_sector=("sector", lambda series: int(series.notna().sum())),
        )
        .sort_values("ticker")
    )
    summary["price_coverage_ratio"] = summary["non_missing_adjusted_close"] / max(total_dates, 1)
    summary["fundamentals_coverage_ratio"] = summary["non_missing_market_cap"] / max(total_dates, 1)
    summary["first_date"] = summary["first_date"].dt.date.astype(str)
    summary["last_date"] = summary["last_date"].dt.date.astype(str)
    return summary.reset_index(drop=True)


def build_date_coverage_summary(panel: pd.DataFrame, *, expected_ticker_count: int) -> pd.DataFrame:
    """Summarize per-date panel coverage and missingness."""
    summary = (
        panel.groupby("date", as_index=False)
        .agg(
            row_count=("ticker", "size"),
            non_missing_adjusted_close=("adjusted_close", lambda series: int(series.notna().sum())),
            non_missing_benchmark_return=(
                "benchmark_return",
                lambda series: int(series.notna().sum()),
            ),
            non_missing_market_cap=("market_cap", lambda series: int(series.notna().sum())),
        )
        .sort_values("date")
    )
    summary["expected_ticker_count"] = expected_ticker_count
    summary["price_coverage_ratio"] = summary["non_missing_adjusted_close"] / max(
        expected_ticker_count, 1
    )
    summary["benchmark_coverage_ratio"] = summary["non_missing_benchmark_return"] / max(
        expected_ticker_count, 1
    )
    summary["fundamentals_coverage_ratio"] = summary["non_missing_market_cap"] / max(
        expected_ticker_count, 1
    )
    summary["date"] = summary["date"].dt.date.astype(str)
    return summary.reset_index(drop=True)
