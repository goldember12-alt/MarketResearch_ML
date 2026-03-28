"""CLI entrypoint for canonical monthly panel assembly."""

from __future__ import annotations

import logging

from src.data.config import configure_logging, load_data_pipeline_config
from src.data.io import read_parquet_required, write_csv, write_json, write_parquet
from src.data.panel_assembly import assemble_monthly_panel
from src.data.qc import (
    build_date_coverage_summary,
    build_panel_qc_summary,
    build_ticker_coverage_summary,
)
from src.utils.config import ensure_output_directories


def main() -> int:
    """Assemble the canonical one-row-per-ticker-per-month panel."""
    config = load_data_pipeline_config()
    configure_logging(config)
    ensure_output_directories(config.project)

    logger = logging.getLogger(__name__)
    logger.info("Starting panel assembly.")

    prices_monthly = read_parquet_required(config.outputs.prices_monthly, "prices_monthly")
    fundamentals_monthly = read_parquet_required(
        config.outputs.fundamentals_monthly, "fundamentals_monthly"
    )
    benchmarks_monthly = read_parquet_required(
        config.outputs.benchmarks_monthly, "benchmarks_monthly"
    )

    monthly_panel = assemble_monthly_panel(
        prices_monthly,
        fundamentals_monthly,
        benchmarks_monthly,
        universe_tickers=config.universe_tickers,
        primary_benchmark=config.processing.primary_benchmark,
    )
    write_parquet(monthly_panel, config.outputs.monthly_panel)

    panel_qc = build_panel_qc_summary(
        monthly_panel, expected_ticker_count=len(config.universe_tickers)
    )
    write_json(panel_qc, config.outputs.panel_qc_summary)
    write_csv(build_ticker_coverage_summary(monthly_panel), config.outputs.ticker_coverage_summary)
    write_csv(
        build_date_coverage_summary(
            monthly_panel, expected_ticker_count=len(config.universe_tickers)
        ),
        config.outputs.date_coverage_summary,
    )

    logger.info("Wrote %s", config.outputs.monthly_panel)
    print("Panel assembly completed.")
    print(config.outputs.monthly_panel)
    print(config.outputs.panel_qc_summary)
    print(config.outputs.ticker_coverage_summary)
    print(config.outputs.date_coverage_summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
