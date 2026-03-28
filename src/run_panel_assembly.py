"""CLI entrypoint for monthly panel assembly."""

from src.utils import StageDefinition, run_stage_cli


STAGE = StageDefinition(
    name="panel_assembly",
    purpose="Join standardized market, benchmark, and fundamentals data into the canonical one-row-per-ticker-per-month panel.",
    next_step="Implement deterministic keyed joins and monthly panel QC in src.data using the standardized ingestion outputs.",
    expected_inputs=(
        "outputs/data/prices_monthly.parquet",
        "outputs/data/fundamentals_monthly.parquet",
        "outputs/data/benchmarks_monthly.parquet",
    ),
    expected_outputs=("outputs/data/monthly_panel.parquet",),
)


def main() -> int:
    """Run the scaffolded panel-assembly stage."""
    return run_stage_cli(STAGE)


if __name__ == "__main__":
    raise SystemExit(main())
