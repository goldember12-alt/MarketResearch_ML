"""Standardization helpers shared across the data-ingestion pipeline."""

from __future__ import annotations

import re
from typing import Iterable

import pandas as pd


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize incoming column names to snake_case identifiers."""
    renamed = {
        column: re.sub(r"[^a-z0-9]+", "_", str(column).strip().lower()).strip("_")
        for column in frame.columns
    }
    return frame.rename(columns=renamed)


def normalize_ticker_series(series: pd.Series) -> pd.Series:
    """Uppercase and trim security identifiers."""
    return series.astype("string").str.strip().str.upper()


def normalize_month_end(series: pd.Series) -> pd.Series:
    """Map timestamps to the canonical calendar month-end convention."""
    return pd.to_datetime(series, errors="coerce").dt.to_period("M").dt.to_timestamp("M")


def select_first_available_column(
    columns: Iterable[str], candidates: Iterable[str], dataset_name: str
) -> str:
    """Select the first available canonical column alias from a priority list."""
    available = {str(column) for column in columns}
    for candidate in candidates:
        if candidate in available:
            return candidate
    raise ValueError(
        f"Could not find any of the expected columns {tuple(candidates)!r} in {dataset_name}."
    )


def maybe_select_column(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    """Return the first matching candidate column if present."""
    available = {str(column) for column in columns}
    for candidate in candidates:
        if candidate in available:
            return candidate
    return None


def coerce_numeric(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Convert selected columns to numeric dtype where present."""
    for column in columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def compute_monthly_returns(
    frame: pd.DataFrame,
    *,
    id_column: str,
    value_column: str,
    output_column: str = "monthly_return",
) -> pd.DataFrame:
    """Compute month-over-month returns from an adjusted close column."""
    sorted_frame = frame.sort_values([id_column, "date"]).copy()
    sorted_frame[output_column] = sorted_frame.groupby(id_column, sort=False)[value_column].pct_change()
    return sorted_frame


def filter_date_window(
    frame: pd.DataFrame,
    *,
    date_column: str,
    start_date: str,
    end_date: str | None,
) -> pd.DataFrame:
    """Filter rows to the configured date window if bounds are provided."""
    filtered = frame.copy()
    start = pd.Timestamp(start_date)
    filtered = filtered[filtered[date_column] >= start]
    if end_date is not None:
        filtered = filtered[filtered[date_column] <= pd.Timestamp(end_date)]
    return filtered


def find_duplicate_keys(frame: pd.DataFrame, key_columns: list[str]) -> pd.DataFrame:
    """Return all duplicated key rows, including both the original and duplicate entries."""
    if frame.empty:
        return frame.copy()
    mask = frame.duplicated(subset=key_columns, keep=False)
    return frame.loc[mask].sort_values(key_columns).copy()


def assert_unique_keys(frame: pd.DataFrame, key_columns: list[str], dataset_name: str) -> None:
    """Raise a clear error when a dataset violates its deterministic key contract."""
    duplicates = find_duplicate_keys(frame, key_columns)
    if duplicates.empty:
        return
    duplicate_preview = duplicates[key_columns].drop_duplicates().head(5).to_dict("records")
    raise ValueError(
        f"{dataset_name} contains duplicate keys for {key_columns!r}. "
        f"Sample duplicates: {duplicate_preview}"
    )


def month_difference(left: pd.Series, right: pd.Series) -> pd.Series:
    """Compute whole-month differences between two datetime series."""
    return (
        (left.dt.year - right.dt.year) * 12
        + (left.dt.month - right.dt.month)
    ).astype("Int64")
