"""CLI entrypoint for portfolio backtesting."""

from src.utils import StageDefinition, run_stage_cli


STAGE = StageDefinition(
    name="backtest",
    purpose="Construct top-N monthly portfolios and compare them against explicit benchmarks under documented trading assumptions.",
    next_step="Implement portfolio construction, holdings history, turnover, and benchmark comparison outputs across src.portfolio and src.backtest.",
    expected_inputs=(
        "outputs/features/feature_panel.parquet",
        "deterministic ranking table from src.signals",
        "config/backtest.yaml",
    ),
    expected_outputs=(
        "outputs/backtests/holdings_history.parquet",
        "outputs/backtests/trade_log.parquet",
        "outputs/backtests/portfolio_returns.parquet",
        "outputs/backtests/benchmark_returns.parquet",
        "outputs/backtests/backtest_summary.json",
    ),
)


def main() -> int:
    """Run the scaffolded backtest stage."""
    return run_stage_cli(STAGE)


if __name__ == "__main__":
    raise SystemExit(main())
