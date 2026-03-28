"""Universe and benchmark helpers for config-driven data processing."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.data.config import DataPipelineConfig


@dataclass(frozen=True)
class UniverseSummary:
    """Convenience summary for the seeded research universe."""

    preset_name: str
    tickers: tuple[str, ...]
    explicit_benchmarks: tuple[str, ...]
    derived_benchmarks: tuple[str, ...]
    primary_benchmark: str


def get_universe_summary(config: DataPipelineConfig) -> UniverseSummary:
    """Return the configured universe and benchmark metadata."""
    return UniverseSummary(
        preset_name=config.project.universe.preset_name,
        tickers=config.universe_tickers,
        explicit_benchmarks=config.explicit_benchmarks,
        derived_benchmarks=config.project.universe.derived_benchmarks,
        primary_benchmark=config.processing.primary_benchmark,
    )


def build_universe_membership_frame(config: DataPipelineConfig) -> pd.DataFrame:
    """Build a simple universe-membership table for reporting or QC."""
    tech = pd.DataFrame(
        {"ticker": list(config.project.universe.tech_tickers), "universe_group": "tech_large_cap"}
    )
    comparison = pd.DataFrame(
        {
            "ticker": list(config.project.universe.comparison_tickers),
            "universe_group": "comparison_large_cap_non_tech",
        }
    )
    return pd.concat([tech, comparison], ignore_index=True)


def validate_primary_benchmark(config: DataPipelineConfig) -> None:
    """Ensure the configured panel benchmark exists in the explicit benchmark set."""
    if config.processing.primary_benchmark not in config.explicit_benchmarks:
        raise ValueError(
            "Primary benchmark must be one of the explicit benchmark tickers. "
            f"Received {config.processing.primary_benchmark!r}."
        )
