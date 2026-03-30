"""CLI entrypoint for model-aware evaluation reporting."""

from __future__ import annotations

import json
import logging

import pandas as pd

from src.backtest.config import configure_backtest_logging, load_backtest_pipeline_config
from src.data.io import read_parquet_required, write_csv, write_json
from src.evaluation.summary import build_model_evaluation_summary
from src.models.config import load_model_pipeline_config
from src.reporting.markdown import render_model_strategy_report
from src.reporting.registry import append_experiment_record, build_model_experiment_record
from src.utils.config import ensure_output_directories, load_project_config


def main() -> int:
    """Assemble a model-aware report and append an experiment-registry record."""
    project_config = load_project_config()
    model_config = load_model_pipeline_config(project_config.root_dir)
    backtest_config = load_backtest_pipeline_config(project_config.root_dir)
    configure_backtest_logging(backtest_config)
    ensure_output_directories(project_config)

    logger = logging.getLogger(__name__)
    logger.info("Starting model evaluation and reporting stage.")

    model_metadata = json.loads(project_config.outputs.model_metadata.read_text(encoding="utf-8"))
    model_backtest_summary = json.loads(
        project_config.outputs.model_backtest_summary.read_text(encoding="utf-8")
    )
    portfolio_returns = read_parquet_required(
        project_config.outputs.model_portfolio_returns,
        "model_portfolio_returns",
    )
    _ = read_parquet_required(
        project_config.outputs.model_benchmark_returns,
        "model_benchmark_returns",
    )
    performance_by_period = pd.read_csv(project_config.outputs.model_performance_by_period)
    deterministic_performance_by_period = pd.read_csv(project_config.outputs.performance_by_period)
    risk_metrics_summary = pd.read_csv(project_config.outputs.model_risk_metrics_summary)
    test_predictions = read_parquet_required(project_config.outputs.test_predictions, "test_predictions")

    summary = build_model_evaluation_summary(
        project_config=project_config,
        model_config=model_config,
        backtest_config=backtest_config,
        model_metadata=model_metadata,
        model_backtest_summary=model_backtest_summary,
        portfolio_returns=portfolio_returns,
        performance_by_period=performance_by_period,
        deterministic_performance_by_period=deterministic_performance_by_period,
        risk_metrics_summary=risk_metrics_summary,
        test_predictions=test_predictions,
    )
    report_text = render_model_strategy_report(
        summary,
        strategy_report_path=str(project_config.outputs.model_strategy_report),
        registry_path=str(project_config.outputs.experiment_registry),
    )
    project_config.outputs.model_strategy_report.parent.mkdir(parents=True, exist_ok=True)
    project_config.outputs.model_strategy_report.write_text(report_text, encoding="utf-8")
    write_json(
        {
            "generated_at_utc": summary["generated_at_utc"],
            "stage": "model_evaluation_report",
            "status": summary["status"],
            "model_type": summary["signal_or_model"],
            "comparison_convention": summary["comparison_convention"],
            "fold_diagnostics": summary["fold_diagnostics"],
            "deterministic_baseline_overlap_comparison": summary[
                "deterministic_baseline_overlap_comparison"
            ],
            "subperiod_diagnostics": summary["subperiod_diagnostics"],
            "bias_caveats": summary["bias_caveats"],
        },
        project_config.outputs.model_comparison_summary,
    )
    write_csv(
        pd.DataFrame(summary["subperiod_diagnostics"].get("segments", [])),
        project_config.outputs.model_subperiod_comparison,
    )

    record = build_model_experiment_record(
        summary,
        artifacts_written=[
            str(project_config.outputs.model_strategy_report),
            str(project_config.outputs.model_comparison_summary),
            str(project_config.outputs.model_subperiod_comparison),
            str(project_config.outputs.experiment_registry),
        ],
    )
    append_experiment_record(record, project_config.outputs.experiment_registry)

    logger.info("Wrote %s", project_config.outputs.model_strategy_report)
    print("Model evaluation reporting completed.")
    print(project_config.outputs.model_strategy_report)
    print(project_config.outputs.model_comparison_summary)
    print(project_config.outputs.model_subperiod_comparison)
    print(project_config.outputs.experiment_registry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
