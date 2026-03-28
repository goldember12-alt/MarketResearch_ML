"""CLI entrypoint for evaluation reporting."""

from src.utils import StageDefinition, run_stage_cli


STAGE = StageDefinition(
    name="evaluation_report",
    purpose="Assemble benchmark-aware strategy evaluation outputs and the experiment registry updates that document what was actually run.",
    next_step="Implement report assembly and experiment logging in src.evaluation and src.reporting once backtest artifacts exist.",
    expected_inputs=(
        "outputs/backtests/backtest_summary.json",
        "outputs/backtests/portfolio_returns.parquet",
        "outputs/backtests/benchmark_returns.parquet",
    ),
    expected_outputs=(
        "outputs/reports/strategy_report.md",
        "outputs/reports/experiment_registry.jsonl",
        "outputs/reports/performance_by_period.csv",
        "outputs/reports/risk_metrics_summary.csv",
    ),
)


def main() -> int:
    """Run the scaffolded evaluation-report stage."""
    return run_stage_cli(STAGE)


if __name__ == "__main__":
    raise SystemExit(main())
