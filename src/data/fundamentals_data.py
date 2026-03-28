"""Fundamentals ingestion and monthly temporal alignment."""

from __future__ import annotations

import pandas as pd

from src.data.config import DataPipelineConfig
from src.data.io import read_tabular_files
from src.data.standardize import (
    assert_unique_keys,
    coerce_numeric,
    month_difference,
    normalize_columns,
    normalize_month_end,
    normalize_ticker_series,
    select_first_available_column,
)


FUNDAMENTALS_ALIASES: dict[str, tuple[str, ...]] = {
    "sector": ("sector", "gics_sector"),
    "industry": ("industry", "gics_industry"),
    "market_cap": ("market_cap", "market_capitalization"),
    "pe_ratio": ("pe_ratio", "price_earnings", "pe"),
    "price_to_sales": ("price_to_sales", "ps_ratio"),
    "price_to_book": ("price_to_book", "pb_ratio"),
    "ev_to_ebitda": ("ev_to_ebitda",),
    "gross_margin": ("gross_margin",),
    "operating_margin": ("operating_margin",),
    "roe": ("roe", "return_on_equity"),
    "roa": ("roa", "return_on_assets"),
    "revenue_growth": ("revenue_growth", "sales_growth"),
    "eps_growth": ("eps_growth",),
    "debt_to_equity": ("debt_to_equity",),
    "current_ratio": ("current_ratio",),
}


def standardize_fundamentals_raw(
    raw_frame: pd.DataFrame,
    *,
    config: DataPipelineConfig,
) -> pd.DataFrame:
    """Standardize raw fundamentals observations to canonical column names."""
    frame = normalize_columns(raw_frame).copy()

    ticker_column = select_first_available_column(
        frame.columns, config.processing.ticker_column_priority, "fundamentals"
    )
    report_date_column = select_first_available_column(
        frame.columns,
        config.processing.fundamentals_date_column_priority,
        "fundamentals",
    )

    standardized = pd.DataFrame(
        {
            "ticker": normalize_ticker_series(frame[ticker_column]),
            "fundamentals_source_date": pd.to_datetime(frame[report_date_column], errors="coerce"),
        }
    )

    for canonical, aliases in FUNDAMENTALS_ALIASES.items():
        for alias in aliases:
            if alias in frame.columns:
                standardized[canonical] = frame[alias]
                break
        else:
            standardized[canonical] = pd.NA

    numeric_columns = [
        column
        for column in standardized.columns
        if column not in {"ticker", "fundamentals_source_date", "sector", "industry"}
    ]
    standardized = coerce_numeric(standardized, numeric_columns)
    standardized = standardized.dropna(subset=["ticker", "fundamentals_source_date"])

    if config.processing.strict_universe_filter:
        standardized = standardized[
            standardized["ticker"].isin(config.universe_tickers)
        ].copy()

    standardized["fundamentals_source_date"] = normalize_month_end(
        standardized["fundamentals_source_date"]
    )
    standardized["fundamentals_effective_date"] = (
        standardized["fundamentals_source_date"]
        + pd.offsets.MonthEnd(config.processing.fundamentals_effective_lag_months)
    )
    standardized = standardized.sort_values(["ticker", "fundamentals_source_date"]).reset_index(
        drop=True
    )
    assert_unique_keys(
        standardized,
        ["ticker", "fundamentals_source_date"],
        "raw_fundamentals_standardized",
    )
    return standardized


def build_fundamentals_monthly(
    config: DataPipelineConfig,
    *,
    monthly_dates: pd.Series,
) -> pd.DataFrame:
    """Map raw fundamentals observations onto the monthly panel calendar."""
    raw_fundamentals = read_tabular_files(config.raw.fundamentals_dir, config.raw.file_patterns)
    standardized = standardize_fundamentals_raw(raw_fundamentals, config=config)

    calendar_dates = pd.Series(pd.to_datetime(monthly_dates)).dropna().drop_duplicates().sort_values()
    universe_calendar = pd.MultiIndex.from_product(
        [config.universe_tickers, calendar_dates.tolist()],
        names=["ticker", "date"],
    ).to_frame(index=False)
    universe_calendar = universe_calendar.sort_values(["ticker", "date"]).reset_index(drop=True)
    merged_frames: list[pd.DataFrame] = []
    right_columns = [column for column in standardized.columns if column != "ticker"]
    for ticker, ticker_calendar in universe_calendar.groupby("ticker", sort=False):
        left = ticker_calendar[["ticker", "date"]].sort_values("date").reset_index(drop=True)
        ticker_right = standardized.loc[standardized["ticker"] == ticker].copy()

        if ticker_right.empty:
            empty = left.copy()
            for column in right_columns:
                empty[column] = pd.NA
            merged_frames.append(empty)
            continue

        merged_ticker = pd.merge_asof(
            left,
            ticker_right[right_columns].sort_values("fundamentals_effective_date"),
            left_on="date",
            right_on="fundamentals_effective_date",
            direction="backward",
            allow_exact_matches=True,
        )
        merged_ticker["ticker"] = ticker
        merged_frames.append(merged_ticker)

    merged = pd.concat(merged_frames, ignore_index=True)

    stale_mask = (
        merged["fundamentals_effective_date"].notna()
        & (
            month_difference(merged["date"], merged["fundamentals_effective_date"])
            > config.processing.fundamentals_max_staleness_months
        )
    )
    stale_columns = [column for column in merged.columns if column not in {"ticker", "date"}]
    merged.loc[stale_mask, stale_columns] = pd.NA

    ordered_columns = [
        "ticker",
        "date",
        "fundamentals_source_date",
        "fundamentals_effective_date",
        "sector",
        "industry",
        "market_cap",
        "pe_ratio",
        "price_to_sales",
        "price_to_book",
        "ev_to_ebitda",
        "gross_margin",
        "operating_margin",
        "roe",
        "roa",
        "revenue_growth",
        "eps_growth",
        "debt_to_equity",
        "current_ratio",
    ]
    merged = merged[ordered_columns].sort_values(["ticker", "date"]).reset_index(drop=True)
    assert_unique_keys(merged, ["ticker", "date"], "fundamentals_monthly")
    return merged
