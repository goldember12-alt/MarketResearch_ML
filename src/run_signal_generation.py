"""CLI entrypoint for deterministic signal generation."""

from src.utils import StageDefinition, run_stage_cli


STAGE = StageDefinition(
    name="signal_generation",
    purpose="Translate the feature panel into deterministic cross-sectional rankings for baseline portfolio construction.",
    next_step="Implement deterministic score aggregation and rank outputs in src.signals before any ML modeling work.",
    expected_inputs=("outputs/features/feature_panel.parquet",),
    expected_outputs=("deterministic ranking table to be formalized in src.signals",),
)


def main() -> int:
    """Run the scaffolded signal-generation stage."""
    return run_stage_cli(STAGE)


if __name__ == "__main__":
    raise SystemExit(main())
