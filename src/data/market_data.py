"""Market-data ingestion and monthly price standardization."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from src.data.config import DataPipelineConfig
from src.data.io import read_tabular_files
from src.data.standardize import (
    assert_unique_keys,
    coerce_numeric,
    compute_monthly_returns,
    filter_date_window,
    maybe_select_column,
    normalize_columns,
    normalize_month_end,
    normalize_ticker_series,
    select_first_available_column,
)


def standardize_price_history(
    raw_frame: pd.DataFrame,
    *,
    dataset_name: str,
    id_candidates: Iterable[str],
    date_candidates: Iterable[str],
    adjusted_close_candidates: Iterable[str],
    allowed_identifiers: set[str],
    start_date: str,
    end_date: str | None,
    output_id_column: str,
) -> pd.DataFrame:
    """Convert raw daily or monthly price data into canonical monthly observations."""
    frame = normalize_columns(raw_frame).copy()

    identifier_column = select_first_available_column(frame.columns, id_candidates, dataset_name)
    date_column = select_first_available_column(frame.columns, date_candidates, dataset_name)
    adjusted_close_column = select_first_available_column(
        frame.columns, adjusted_close_candidates, dataset_name
    )
    volume_column = maybe_select_column(frame.columns, ("volume", "share_volume"))

    standardized = pd.DataFrame(
        {
            output_id_column: normalize_ticker_series(frame[identifier_column]),
            "raw_date": pd.to_datetime(frame[date_column], errors="coerce"),
            "adjusted_close": frame[adjusted_close_column],
        }
    )
    if volume_column is not None:
        standardized["volume"] = frame[volume_column]

    standardized = coerce_numeric(standardized, ["adjusted_close", "volume"])
    standardized = standardized.dropna(subset=[output_id_column, "raw_date", "adjusted_close"])

    if allowed_identifiers:
        standardized = standardized[
            standardized[output_id_column].isin(sorted(allowed_identifiers))
        ].copy()

    standardized["date"] = normalize_month_end(standardized["raw_date"])
    standardized = filter_date_window(
        standardized, date_column="date", start_date=start_date, end_date=end_date
    )
    standardized = standardized.sort_values([output_id_column, "raw_date"])

    aggregations: dict[str, str] = {"adjusted_close": "last"}
    if "volume" in standardized.columns:
        aggregations["volume"] = "last"

    monthly = (
        standardized.groupby([output_id_column, "date"], as_index=False)
        .agg(aggregations)
        .sort_values([output_id_column, "date"])
    )
    monthly = compute_monthly_returns(
        monthly, id_column=output_id_column, value_column="adjusted_close"
    )
    assert_unique_keys(monthly, [output_id_column, "date"], dataset_name)
    return monthly.reset_index(drop=True)


def build_prices_monthly(config: DataPipelineConfig) -> pd.DataFrame:
    """Read local raw market files and produce canonical monthly security prices."""
    raw_prices = read_tabular_files(config.raw.market_dir, config.raw.file_patterns)
    return standardize_price_history(
        raw_prices,
        dataset_name="market prices",
        id_candidates=config.processing.ticker_column_priority,
        date_candidates=config.processing.date_column_priority,
        adjusted_close_candidates=config.processing.adjusted_close_priority,
        allowed_identifiers=set(config.universe_tickers),
        start_date=config.project.universe.start_date,
        end_date=config.project.universe.end_date,
        output_id_column="ticker",
    )
