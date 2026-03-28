"""CLI entrypoint for baseline modeling experiments."""

from src.utils import StageDefinition, run_stage_cli


STAGE = StageDefinition(
    name="modeling_baselines",
    purpose="Run leakage-safe deterministic and simple ML baseline experiments after the deterministic backtest workflow is in place.",
    next_step="Implement label construction and walk-forward dataset preparation in src.models before fitting baseline models.",
    expected_inputs=(
        "outputs/features/feature_panel.parquet",
        "outputs/data/monthly_panel.parquet",
        "config/model.yaml",
    ),
    expected_outputs=(
        "outputs/models/train_predictions.parquet",
        "outputs/models/test_predictions.parquet",
        "outputs/models/model_metadata.json",
    ),
)


def main() -> int:
    """Run the scaffolded modeling-baselines stage."""
    return run_stage_cli(STAGE)


if __name__ == "__main__":
    raise SystemExit(main())
