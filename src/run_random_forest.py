"""CLI entrypoint for random-forest experiments."""

from src.utils import StageDefinition, run_stage_cli


STAGE = StageDefinition(
    name="random_forest",
    purpose="Fit the initial tree-based baseline only after deterministic and linear-model baselines are available for comparison.",
    next_step="Implement chronology-safe random forest training, feature importance export, and benchmarked evaluation in src.models.",
    expected_inputs=("outputs/features/feature_panel.parquet", "config/model.yaml"),
    expected_outputs=(
        "outputs/models/test_predictions.parquet",
        "outputs/models/model_metadata.json",
        "outputs/models/feature_importance.csv",
    ),
)


def main() -> int:
    """Run the scaffolded random-forest stage."""
    return run_stage_cli(STAGE)


if __name__ == "__main__":
    raise SystemExit(main())
