"""CLI entrypoint for the logistic-regression baseline."""

from src.models.pipeline import run_modeling_stage


def main() -> int:
    """Run the leakage-safe logistic-regression baseline."""
    return run_modeling_stage("logistic_regression")


if __name__ == "__main__":
    raise SystemExit(main())
