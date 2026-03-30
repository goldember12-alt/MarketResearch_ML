"""CLI entrypoint for the logistic-regression baseline."""

import sys

from src.models.pipeline import run_modeling_stage
from src.utils.cli import parse_execution_mode_args


def main(argv: list[str] | None = None) -> int:
    """Run the leakage-safe logistic-regression baseline."""
    args = parse_execution_mode_args(argv)
    return run_modeling_stage("logistic_regression", execution_mode=args.execution_mode)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
