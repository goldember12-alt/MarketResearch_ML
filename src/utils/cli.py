"""Shared CLI parsing helpers for optional execution-mode overrides."""

from __future__ import annotations

import argparse
from typing import Sequence


def parse_execution_mode_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the optional execution-mode override shared by runnable entrypoints."""
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--execution-mode",
        choices=("seeded", "research_scale"),
        default=None,
        help=(
            "Optional execution profile. "
            "'seeded' uses packaged sample raw files only. "
            "'research_scale' prefers broader non-sample local raw files and falls back "
            "to the sample files when broader history is unavailable."
        ),
    )
    return parser.parse_args(list(argv) if argv is not None else [])
