"""CLI entrypoint for evaluation reporting."""

from __future__ import annotations

import json
import logging
import sys

import pandas as pd

from src.backtest.config import configure_backtest_logging, load_backtest_pipeline_config
from src.data.io import read_parquet_required
from src.evaluation.coverage import build_run_summary_artifact, build_stage_coverage_summary
from src.evaluation.summary import build_evaluation_summary
from src.reporting.markdown import render_strategy_report
from src.reporting.registry import append_experiment_record, build_experiment_record
from src.signals.config import load_signal_pipeline_config
from src.utils.cli import parse_execution_mode_args
from src.utils.config import ensure_output_directories, load_project_config


def main(argv: list[str] | None = None) -> int:
    """Assemble a benchmark-aware report and append an experiment-registry record."""
    args = parse_execution_mode_args(argv)
    project_config = load_project_config(execution_mode=args.execution_mode)
    backtest_config = load_backtest_pipeline_config(
        project_config.root_dir,
        execution_mode=args.execution_mode,
    )
    signal_config = load_signal_pipeline_config(
        project_config.root_dir,
        execution_mode=args.execution_mode,
    )
    configure_backtest_logging(backtest_config)
    ensure_output_directories(project_config)

    logger = logging.getLogger(__name__)
    logger.info("Starting evaluation and reporting stage.")

    backtest_summary = json.loads(
        project_config.outputs.backtest_summary.read_text(encoding="utf-8")
    )
    portfolio_returns = read_parquet_required(
        project_config.outputs.portfolio_returns, "portfolio_returns"
    )
    _ = read_parquet_required(project_config.outputs.benchmark_returns, "benchmark_returns")
    performance_by_period = pd.read_csv(project_config.outputs.performance_by_period)
    risk_metrics_summary = pd.read_csv(project_config.outputs.risk_metrics_summary)
    prices_qc_summary = json.loads(project_config.outputs.prices_qc_summary.read_text(encoding="utf-8"))
    fundamentals_qc_summary = json.loads(
        project_config.outputs.fundamentals_qc_summary.read_text(encoding="utf-8")
    )
    benchmarks_qc_summary = json.loads(
        project_config.outputs.benchmarks_qc_summary.read_text(encoding="utf-8")
    )
    panel_qc_summary = json.loads(project_config.outputs.panel_qc_summary.read_text(encoding="utf-8"))
    feature_qc_summary = json.loads(
        project_config.outputs.feature_qc_summary.read_text(encoding="utf-8")
    )
    signal_qc_summary = json.loads(
        project_config.outputs.signal_qc_summary.read_text(encoding="utf-8")
    )
    stage_coverage = build_stage_coverage_summary(
        project_config=project_config,
        prices_qc_summary=prices_qc_summary,
        fundamentals_qc_summary=fundamentals_qc_summary,
        benchmarks_qc_summary=benchmarks_qc_summary,
        panel_qc_summary=panel_qc_summary,
        feature_qc_summary=feature_qc_summary,
        signal_qc_summary=signal_qc_summary,
        backtest_summary=backtest_summary,
    )

    summary = build_evaluation_summary(
        project_config=project_config,
        signal_config=signal_config,
        backtest_config=backtest_config,
        backtest_summary=backtest_summary,
        portfolio_returns=portfolio_returns,
        performance_by_period=performance_by_period,
        risk_metrics_summary=risk_metrics_summary,
        stage_coverage=stage_coverage,
    )
    report_text = render_strategy_report(
        summary,
        strategy_report_path=str(project_config.outputs.strategy_report),
        registry_path=str(project_config.outputs.experiment_registry),
    )
    project_config.outputs.strategy_report.parent.mkdir(parents=True, exist_ok=True)
    project_config.outputs.strategy_report.write_text(report_text, encoding="utf-8")
    run_summary = build_run_summary_artifact(
        summary=summary,
        stage="evaluation_report",
        artifacts_written=[
            str(project_config.outputs.strategy_report),
            str(project_config.outputs.run_summary),
            str(project_config.outputs.experiment_registry),
        ],
    )
    project_config.outputs.run_summary.write_text(
        json.dumps(run_summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    record = build_experiment_record(
        summary,
        artifacts_written=[
            str(project_config.outputs.strategy_report),
            str(project_config.outputs.run_summary),
            str(project_config.outputs.experiment_registry),
        ],
    )
    append_experiment_record(record, project_config.outputs.experiment_registry)

    logger.info("Wrote %s", project_config.outputs.strategy_report)
    print("Evaluation reporting completed.")
    print(project_config.outputs.strategy_report)
    print(project_config.outputs.run_summary)
    print(project_config.outputs.experiment_registry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
