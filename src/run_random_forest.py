"""CLI entrypoint for the random-forest baseline."""

from src.models.pipeline import run_modeling_stage


def main() -> int:
    """Run the leakage-safe random-forest baseline."""
    return run_modeling_stage("random_forest")


if __name__ == "__main__":
    raise SystemExit(main())
