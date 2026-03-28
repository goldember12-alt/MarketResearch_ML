"""Canonical monthly panel assembly."""

from __future__ import annotations

import pandas as pd

from src.data.benchmarks import select_primary_benchmark_series
from src.data.standardize import assert_unique_keys


def build_panel_calendar(
    prices_monthly: pd.DataFrame, benchmarks_monthly: pd.DataFrame, primary_benchmark: str
) -> pd.DatetimeIndex:
    """Build the canonical monthly panel calendar from price and benchmark dates."""
    benchmark_dates = benchmarks_monthly.loc[
        benchmarks_monthly["benchmark_ticker"] == primary_benchmark, "date"
    ]
    calendar = pd.Index(prices_monthly["date"]).union(pd.Index(benchmark_dates))
    return pd.DatetimeIndex(calendar.dropna().sort_values().unique())


def validate_one_row_per_ticker_per_month(
    panel: pd.DataFrame,
    *,
    expected_tickers: tuple[str, ...],
    expected_dates: pd.DatetimeIndex,
) -> None:
    """Validate the canonical one-row-per-ticker-per-month panel shape."""
    assert_unique_keys(panel, ["ticker", "date"], "monthly_panel")
    expected_rows = len(expected_tickers) * len(expected_dates)
    if len(panel) != expected_rows:
        raise ValueError(
            "monthly_panel does not satisfy the canonical ticker-month grid. "
            f"Expected {expected_rows} rows, found {len(panel)}."
        )


def assemble_monthly_panel(
    prices_monthly: pd.DataFrame,
    fundamentals_monthly: pd.DataFrame,
    benchmarks_monthly: pd.DataFrame,
    *,
    universe_tickers: tuple[str, ...],
    primary_benchmark: str,
) -> pd.DataFrame:
    """Join prices, fundamentals, and the primary benchmark into the canonical panel."""
    assert_unique_keys(prices_monthly, ["ticker", "date"], "prices_monthly")
    assert_unique_keys(fundamentals_monthly, ["ticker", "date"], "fundamentals_monthly")
    assert_unique_keys(benchmarks_monthly, ["benchmark_ticker", "date"], "benchmarks_monthly")

    panel_dates = build_panel_calendar(prices_monthly, benchmarks_monthly, primary_benchmark)
    panel_index = pd.MultiIndex.from_product(
        [universe_tickers, panel_dates.tolist()],
        names=["ticker", "date"],
    ).to_frame(index=False)

    primary_benchmark_series = select_primary_benchmark_series(benchmarks_monthly, primary_benchmark)

    panel = panel_index.merge(prices_monthly, on=["ticker", "date"], how="left")
    panel = panel.merge(fundamentals_monthly, on=["ticker", "date"], how="left")
    panel = panel.merge(primary_benchmark_series, on="date", how="left")

    ordered_columns = [
        "ticker",
        "date",
        "adjusted_close",
        "monthly_return",
        "benchmark_ticker",
        "benchmark_return",
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
        "fundamentals_source_date",
        "fundamentals_effective_date",
        "volume",
    ]
    panel = panel[[column for column in ordered_columns if column in panel.columns]]
    panel = panel.sort_values(["ticker", "date"]).reset_index(drop=True)
    validate_one_row_per_ticker_per_month(
        panel, expected_tickers=universe_tickers, expected_dates=panel_dates
    )
    return panel
