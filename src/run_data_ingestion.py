"""CLI entrypoint for raw market, benchmark, and fundamentals ingestion."""

from __future__ import annotations

import logging

import pandas as pd

from src.data.benchmarks import build_benchmarks_monthly
from src.data.config import configure_logging, load_data_pipeline_config
from src.data.fundamentals_data import build_fundamentals_monthly
from src.data.io import write_json, write_parquet
from src.data.market_data import build_prices_monthly
from src.data.qc import build_dataset_qc_summary
from src.data.universe import validate_primary_benchmark
from src.utils.config import ensure_output_directories


def main() -> int:
    """Run the local-file-first ingestion pipeline and persist standardized artifacts."""
    config = load_data_pipeline_config()
    configure_logging(config)
    ensure_output_directories(config.project)
    validate_primary_benchmark(config)

    logger = logging.getLogger(__name__)
    logger.info("Starting data ingestion for preset %s", config.project.universe.preset_name)

    prices_monthly = build_prices_monthly(config)
    write_parquet(prices_monthly, config.outputs.prices_monthly)
    write_json(
        build_dataset_qc_summary(
            prices_monthly,
            dataset_name="prices_monthly",
            id_column="ticker",
            key_columns=["ticker", "date"],
        ),
        config.outputs.prices_qc_summary,
    )

    benchmarks_monthly = build_benchmarks_monthly(config, prices_monthly)
    write_parquet(benchmarks_monthly, config.outputs.benchmarks_monthly)
    write_json(
        build_dataset_qc_summary(
            benchmarks_monthly,
            dataset_name="benchmarks_monthly",
            id_column="benchmark_ticker",
            key_columns=["benchmark_ticker", "date"],
        ),
        config.outputs.benchmarks_qc_summary,
    )

    monthly_dates = pd.Index(prices_monthly["date"]).union(pd.Index(benchmarks_monthly["date"]))
    fundamentals_monthly = build_fundamentals_monthly(
        config,
        monthly_dates=pd.Series(monthly_dates.sort_values().unique()),
    )
    write_parquet(fundamentals_monthly, config.outputs.fundamentals_monthly)
    write_json(
        build_dataset_qc_summary(
            fundamentals_monthly,
            dataset_name="fundamentals_monthly",
            id_column="ticker",
            key_columns=["ticker", "date"],
        ),
        config.outputs.fundamentals_qc_summary,
    )

    logger.info("Wrote %s", config.outputs.prices_monthly)
    logger.info("Wrote %s", config.outputs.benchmarks_monthly)
    logger.info("Wrote %s", config.outputs.fundamentals_monthly)
    print("Data ingestion completed.")
    print(config.outputs.prices_monthly)
    print(config.outputs.benchmarks_monthly)
    print(config.outputs.fundamentals_monthly)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
