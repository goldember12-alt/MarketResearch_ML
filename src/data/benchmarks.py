"""Benchmark ingestion and derived benchmark construction."""

from __future__ import annotations

import pandas as pd

from src.data.config import DataPipelineConfig
from src.data.io import read_tabular_files
from src.data.market_data import standardize_price_history
from src.data.standardize import assert_unique_keys


def build_equal_weight_benchmark(
    prices_monthly: pd.DataFrame,
    *,
    benchmark_id: str,
    start_value: float,
) -> pd.DataFrame:
    """Construct an equal-weight universe benchmark from monthly constituent returns."""
    equal_weight = (
        prices_monthly.groupby("date", as_index=False)
        .agg(monthly_return=("monthly_return", "mean"))
        .sort_values("date")
    )
    equal_weight["benchmark_ticker"] = benchmark_id
    compounded = (1.0 + equal_weight["monthly_return"].fillna(0.0)).cumprod()
    equal_weight["adjusted_close"] = start_value * compounded
    return equal_weight[["benchmark_ticker", "date", "adjusted_close", "monthly_return"]]


def build_benchmarks_monthly(
    config: DataPipelineConfig, prices_monthly: pd.DataFrame
) -> pd.DataFrame:
    """Read explicit benchmarks and append the derived equal-weight universe benchmark."""
    raw_benchmarks = read_tabular_files(
        config.raw.benchmarks_dir,
        config.raw.file_patterns,
        execution=config.project.execution,
    )
    explicit = standardize_price_history(
        raw_benchmarks,
        dataset_name="benchmarks",
        id_candidates=("benchmark_ticker", *config.processing.ticker_column_priority),
        date_candidates=config.processing.date_column_priority,
        adjusted_close_candidates=config.processing.adjusted_close_priority,
        allowed_identifiers=set(config.explicit_benchmarks),
        start_date=config.project.universe.start_date,
        end_date=config.project.universe.end_date,
        output_id_column="benchmark_ticker",
    )

    equal_weight = build_equal_weight_benchmark(
        prices_monthly,
        benchmark_id=config.processing.equal_weight_benchmark_id,
        start_value=config.processing.equal_weight_start_value,
    )

    benchmarks = pd.concat([explicit, equal_weight], ignore_index=True)
    benchmarks = benchmarks.sort_values(["benchmark_ticker", "date"]).reset_index(drop=True)
    assert_unique_keys(benchmarks, ["benchmark_ticker", "date"], "benchmarks_monthly")
    raw_manifest = dict(raw_benchmarks.attrs.get("raw_file_selection_manifest") or {})
    raw_manifest["derived_benchmarks_added"] = [config.processing.equal_weight_benchmark_id]
    benchmarks.attrs["raw_file_selection_manifest"] = raw_manifest
    return benchmarks


def select_primary_benchmark_series(
    benchmarks_monthly: pd.DataFrame, primary_benchmark: str
) -> pd.DataFrame:
    """Return the configured benchmark series used for panel-level alignment."""
    benchmark_series = benchmarks_monthly.loc[
        benchmarks_monthly["benchmark_ticker"] == primary_benchmark,
        ["date", "monthly_return"],
    ].copy()
    if benchmark_series.empty:
        raise ValueError(f"Primary benchmark {primary_benchmark!r} was not found in benchmark data.")
    benchmark_series["benchmark_ticker"] = primary_benchmark
    benchmark_series = benchmark_series.rename(columns={"monthly_return": "benchmark_return"})
    return benchmark_series[["date", "benchmark_ticker", "benchmark_return"]]
