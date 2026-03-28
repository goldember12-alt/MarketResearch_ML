"""CLI entrypoint for raw market and fundamentals data ingestion."""

from src.utils import StageDefinition, run_stage_cli


STAGE = StageDefinition(
    name="data_ingestion",
    purpose="Ingest raw prices, fundamentals, and benchmark inputs into standardized monthly datasets.",
    next_step="Implement source adapters and schema validation in src.data before writing prices_monthly, fundamentals_monthly, and benchmarks_monthly.",
    expected_inputs=("config/universe.yaml",),
    expected_outputs=(
        "outputs/data/prices_monthly.parquet",
        "outputs/data/fundamentals_monthly.parquet",
        "outputs/data/benchmarks_monthly.parquet",
    ),
)


def main() -> int:
    """Run the scaffolded data-ingestion stage."""
    return run_stage_cli(STAGE)


if __name__ == "__main__":
    raise SystemExit(main())
