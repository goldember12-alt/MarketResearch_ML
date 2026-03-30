"""CLI entrypoint for the configured modeling-baselines stage."""

from src.models.pipeline import run_modeling_stage


def main() -> int:
    """Run the configured leakage-safe modeling baseline stage."""
    return run_modeling_stage()


if __name__ == "__main__":
    raise SystemExit(main())
