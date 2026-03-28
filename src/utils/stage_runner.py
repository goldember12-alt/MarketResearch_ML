"""Shared no-op stage runner used by the scaffold CLI entrypoints."""

from __future__ import annotations

from dataclasses import dataclass

from src.utils.config import ensure_output_directories, load_project_config


@dataclass(frozen=True)
class StageDefinition:
    """Minimal metadata describing a pipeline stage scaffold."""

    name: str
    purpose: str
    next_step: str
    expected_inputs: tuple[str, ...]
    expected_outputs: tuple[str, ...]


def run_stage_cli(stage: StageDefinition) -> int:
    """Load project config, ensure directories exist, and print stage context."""
    config = load_project_config()
    ensure_output_directories(config)

    print(f"Stage: {stage.name}")
    print(f"Purpose: {stage.purpose}")
    print(f"Universe preset: {config.universe.preset_name}")
    print(f"Universe size: {len(config.universe.all_tickers)} seeded tickers")
    print(
        "Benchmarks: "
        + ", ".join(config.universe.explicit_benchmarks + config.universe.derived_benchmarks)
    )
    print(
        "Rebalance: "
        f"{config.backtest.frequency}, "
        f"selection_method={config.backtest.selection_method}, "
        f"top_n={config.backtest.top_n}"
    )
    print(
        "Costs: "
        f"transaction_cost_bps={config.backtest.transaction_cost_bps}, "
        f"slippage_bps={config.backtest.slippage_bps}"
    )
    print("Expected inputs: " + ", ".join(stage.expected_inputs))
    print("Expected outputs: " + ", ".join(stage.expected_outputs))
    print("Status: scaffold_only")
    print(f"Next implementation step: {stage.next_step}")
    return 0
