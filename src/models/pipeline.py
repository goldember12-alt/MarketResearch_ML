"""End-to-end orchestration for modeling-baselines CLI runners."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from src.backtest.config import load_backtest_pipeline_config
from src.data.io import read_parquet_required, write_csv, write_json, write_parquet
from src.models.baselines import run_baseline_model
from src.models.config import (
    ModelPipelineConfig,
    configure_model_logging,
    load_model_pipeline_config,
)
from src.models.datasets import build_modeling_dataset
from src.reporting.registry import append_experiment_record
from src.utils.config import ensure_output_directories


def _config_with_model_override(
    config: ModelPipelineConfig,
    model_type: str | None,
) -> ModelPipelineConfig:
    """Apply an optional CLI-level model override without mutating the base config."""
    if model_type is None:
        return config
    return replace(config, execution=replace(config.execution, selected_model=model_type))


def _build_model_metadata(
    *,
    config: ModelPipelineConfig,
    selected_model: str,
    dataset_bundle,
    model_run,
) -> dict[str, Any]:
    """Assemble the canonical model_metadata.json payload."""
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "modeling_baselines",
        "status": "exploratory_completed",
        "model_type": selected_model,
        "label_definition": dataset_bundle.label_metadata["definition"],
        "label_settings": dataset_bundle.label_metadata,
        "split_scheme": config.splits.scheme,
        "split_windows": {
            "train": {
                "decision_start": config.splits.train.start_date,
                "decision_end": config.splits.train.end_date,
            },
            "validation": {
                "decision_start": config.splits.validation.start_date,
                "decision_end": config.splits.validation.end_date,
            },
            "test": {
                "decision_start": config.splits.test.start_date,
                "decision_end": config.splits.test.end_date,
            },
        },
        "feature_columns": list(config.dataset.feature_columns),
        "minimum_non_missing_features": config.dataset.minimum_non_missing_features,
        "preprocessing": model_run.metadata["preprocessing"],
        "model_hyperparameters": model_run.metadata["model_hyperparameters"],
        "classification_threshold": model_run.metadata["classification_threshold"],
        "row_counts_by_split": dataset_bundle.qc_summary["row_counts_by_split"],
        "dropped_rows_summary": dataset_bundle.dropped_rows_summary,
        "evaluation": model_run.metadata["metrics_by_split"],
        "deterministic_baseline_context": {
            "enabled": config.deterministic_baseline.enabled,
            "score_column": config.deterministic_baseline.score_column,
            "class_column": config.deterministic_baseline.class_column,
        },
        "qc": dataset_bundle.qc_summary,
        "artifacts_written": [
            str(config.outputs.train_predictions),
            str(config.outputs.test_predictions),
            str(config.outputs.model_metadata),
            str(config.outputs.feature_importance),
        ],
        "key_caveats": [
            "This stage predicts a future label aligned to the month-end t decision and future realized return window only; it does not itself create a tradable backtest.",
            "Preprocessing is fit on training rows only, but the current sample history is short and uses deterministic local fixture data.",
            "Fundamentals remain lagged heuristics rather than fully point-in-time-safe history, so revised-history bias risk still applies.",
            "Current metrics are descriptive classification diagnostics, not benchmark-quality evidence of alpha.",
        ],
        "next_step": "Feed model scores into a model-driven portfolio construction and backtest path under the same benchmark and cost controls.",
    }


def _append_model_registry_record(
    *,
    config: ModelPipelineConfig,
    selected_model: str,
    metadata: dict[str, Any],
) -> None:
    """Append a cautious modeling-stage record to the canonical experiment registry."""
    backtest_config = load_backtest_pipeline_config(config.root_dir)
    test_metrics = metadata["evaluation"].get("test", {}).get("model", {})
    deterministic_test_metrics = metadata["evaluation"].get("test", {}).get(
        "deterministic_baseline", {}
    )
    record: dict[str, Any] = {
        "experiment_id": f"modeling_baselines_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "run_timestamp": metadata["generated_at_utc"],
        "stage": "modeling_baselines",
        "purpose": "Fit a leakage-safe baseline classifier on the monthly feature panel and compare it to the deterministic signal context.",
        "date_range": {
            "train_decision_start": config.splits.train.start_date,
            "train_decision_end": config.splits.train.end_date,
            "validation_decision_start": config.splits.validation.start_date,
            "validation_decision_end": config.splits.validation.end_date,
            "test_decision_start": config.splits.test.start_date,
            "test_decision_end": config.splits.test.end_date,
        },
        "universe_preset": config.project.universe.preset_name,
        "benchmark_set": [config.label.benchmark],
        "feature_set": list(config.dataset.feature_columns),
        "signal_or_model": selected_model,
        "portfolio_rules": {
            "comparison_context": "deterministic_signal_top_n_selection",
            "holding_period_convention": "month_end_t_features_predict_realized_outcome_from_t_plus_1",
            "label_target_type": config.label.target_type,
        },
        "rebalance_frequency": config.project.backtest.frequency,
        "transaction_cost_bps": backtest_config.costs.transaction_cost_bps,
        "artifacts_written": metadata["artifacts_written"]
        + [str(config.outputs.experiment_registry)],
        "result_summary": {
            "test_accuracy": test_metrics.get("accuracy"),
            "test_roc_auc": test_metrics.get("roc_auc"),
            "test_average_precision": test_metrics.get("average_precision"),
            "deterministic_test_accuracy": deterministic_test_metrics.get("accuracy"),
            "deterministic_test_roc_auc": deterministic_test_metrics.get("roc_auc"),
        },
        "interpretation": (
            "This modeling run is exploratory and label-diagnostic only. It should not be treated "
            "as a benchmark-quality out-of-sample portfolio result until model scores are routed "
            "through the same portfolio construction and backtest controls as the deterministic baseline."
        ),
        "status": "exploratory_completed",
        "next_step": metadata["next_step"],
    }
    append_experiment_record(record, config.outputs.experiment_registry)


def run_modeling_stage(model_type: str | None = None) -> int:
    """Run the configured modeling-baselines stage and write canonical artifacts."""
    base_config = load_model_pipeline_config()
    config = _config_with_model_override(base_config, model_type)
    configure_model_logging(config)
    ensure_output_directories(config.project)

    logger = logging.getLogger(__name__)
    selected_model = config.execution.selected_model
    logger.info("Starting modeling-baselines stage with model=%s.", selected_model)

    feature_panel = read_parquet_required(config.outputs.feature_panel, "feature_panel")
    monthly_panel = read_parquet_required(config.outputs.monthly_panel, "monthly_panel")
    signal_rankings = (
        read_parquet_required(config.outputs.signal_rankings, "signal_rankings")
        if config.outputs.signal_rankings.exists()
        else None
    )

    dataset_bundle = build_modeling_dataset(
        feature_panel=feature_panel,
        monthly_panel=monthly_panel,
        config=config,
        signal_rankings=signal_rankings,
    )
    model_run = run_baseline_model(
        dataset_bundle.dataset,
        model_type=selected_model,
        config=config,
    )
    metadata = _build_model_metadata(
        config=config,
        selected_model=selected_model,
        dataset_bundle=dataset_bundle,
        model_run=model_run,
    )

    write_parquet(model_run.train_predictions, config.outputs.train_predictions)
    write_parquet(model_run.test_predictions, config.outputs.test_predictions)
    write_csv(model_run.feature_importance, config.outputs.feature_importance)
    write_json(metadata, config.outputs.model_metadata)

    if config.execution.append_experiment_registry:
        _append_model_registry_record(
            config=config,
            selected_model=selected_model,
            metadata=metadata,
        )

    logger.info("Wrote %s", config.outputs.model_metadata)
    print("Modeling baselines completed.")
    print(config.outputs.train_predictions)
    print(config.outputs.test_predictions)
    print(config.outputs.model_metadata)
    print(config.outputs.feature_importance)
    if config.execution.append_experiment_registry:
        print(config.outputs.experiment_registry)
    return 0
