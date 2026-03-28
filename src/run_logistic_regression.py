"""CLI entrypoint for logistic-regression experiments."""

from src.utils import StageDefinition, run_stage_cli


STAGE = StageDefinition(
    name="logistic_regression",
    purpose="Fit the initial regularized classification baseline using chronology-safe training and validation splits.",
    next_step="Implement train-only preprocessing and walk-forward logistic regression evaluation in src.models.",
    expected_inputs=("outputs/features/feature_panel.parquet", "config/model.yaml"),
    expected_outputs=(
        "outputs/models/train_predictions.parquet",
        "outputs/models/test_predictions.parquet",
        "outputs/models/model_metadata.json",
    ),
)


def main() -> int:
    """Run the scaffolded logistic-regression stage."""
    return run_stage_cli(STAGE)


if __name__ == "__main__":
    raise SystemExit(main())
