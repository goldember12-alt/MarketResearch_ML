"""CLI entrypoint for leakage-safe feature generation."""

from src.utils import StageDefinition, run_stage_cli


STAGE = StageDefinition(
    name="feature_generation",
    purpose="Create leakage-safe monthly features from the canonical panel with documented lookbacks and lags.",
    next_step="Implement lagged return, momentum, valuation, profitability, growth, and missingness QC outputs in src.features.",
    expected_inputs=("outputs/data/monthly_panel.parquet", "config/features.yaml"),
    expected_outputs=(
        "outputs/features/feature_panel.parquet",
        "outputs/features/feature_qc_summary.json",
        "outputs/features/feature_missingness_summary.csv",
    ),
)


def main() -> int:
    """Run the scaffolded feature-generation stage."""
    return run_stage_cli(STAGE)


if __name__ == "__main__":
    raise SystemExit(main())
