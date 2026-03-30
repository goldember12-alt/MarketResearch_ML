"""Focused tests for evaluation and reporting outputs."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from src.backtest.config import load_backtest_pipeline_config
from src.evaluation.summary import build_evaluation_summary, build_model_evaluation_summary
from src.models.config import load_model_pipeline_config
from src.reporting.markdown import render_model_strategy_report, render_strategy_report
from src.reporting.registry import (
    append_experiment_record,
    build_experiment_record,
    build_model_experiment_record,
)
from src.signals.config import load_signal_pipeline_config
from src.utils.config import load_project_config


def _backtest_summary_fixture() -> dict[str, object]:
    return {
        "formation_start_date": "2024-01-31",
        "formation_end_date": "2024-03-31",
        "realized_start_date": "2024-02-29",
        "realized_end_date": "2024-04-30",
        "holding_period_convention": "Signals at t form holdings for realized returns at t+1.",
        "qc": {"benchmark_alignment_ok": True, "missing_realized_return_count": 0},
    }


def _portfolio_returns_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-02-29", "2024-03-31", "2024-04-30"]),
            "formation_date": pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"]),
            "portfolio_net_return": [0.02, -0.01, 0.03],
            "turnover": [1.0, 0.5, 0.2],
        }
    )


def _performance_by_period_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-02-29", "2024-03-31", "2024-04-30"]),
            "portfolio_net_return": [0.02, -0.01, 0.03],
            "benchmark_return__SPY": [0.01, -0.02, 0.015],
            "benchmark_return__QQQ": [0.015, -0.01, 0.01],
            "benchmark_return__equal_weight_universe": [0.02, -0.015, 0.02],
        }
    )


def _risk_metrics_summary_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "series_id": "portfolio_gross",
                "series_type": "portfolio",
                "period_count": 3,
                "cumulative_return": 0.041,
                "annualized_return": 0.17,
                "annualized_volatility": 0.11,
                "sharpe_ratio": 1.2,
                "sortino_ratio": None,
                "max_drawdown": -0.01,
                "hit_rate": 2 / 3,
                "average_turnover": None,
                "total_turnover": None,
            },
            {
                "series_id": "portfolio_net",
                "series_type": "portfolio",
                "period_count": 3,
                "cumulative_return": 0.039,
                "annualized_return": 0.16,
                "annualized_volatility": 0.10,
                "sharpe_ratio": 1.1,
                "sortino_ratio": None,
                "max_drawdown": -0.01,
                "hit_rate": 2 / 3,
                "average_turnover": 0.5667,
                "total_turnover": 1.7,
            },
            {
                "series_id": "SPY",
                "series_type": "benchmark",
                "period_count": 3,
                "cumulative_return": 0.004,
                "annualized_return": 0.02,
                "annualized_volatility": 0.09,
                "sharpe_ratio": 0.2,
                "sortino_ratio": None,
                "max_drawdown": -0.02,
                "hit_rate": 2 / 3,
                "average_turnover": None,
                "total_turnover": None,
            },
            {
                "series_id": "QQQ",
                "series_type": "benchmark",
                "period_count": 3,
                "cumulative_return": 0.015,
                "annualized_return": 0.06,
                "annualized_volatility": 0.10,
                "sharpe_ratio": 0.4,
                "sortino_ratio": None,
                "max_drawdown": -0.01,
                "hit_rate": 2 / 3,
                "average_turnover": None,
                "total_turnover": None,
            },
            {
                "series_id": "equal_weight_universe",
                "series_type": "benchmark",
                "period_count": 3,
                "cumulative_return": 0.025,
                "annualized_return": 0.09,
                "annualized_volatility": 0.08,
                "sharpe_ratio": 0.6,
                "sortino_ratio": None,
                "max_drawdown": -0.01,
                "hit_rate": 2 / 3,
                "average_turnover": None,
                "total_turnover": None,
            },
        ]
    )


def _model_metadata_fixture() -> dict[str, object]:
    return {
        "model_type": "logistic_regression",
        "label_definition": "forward_excess_return_top_n_binary",
        "split_scheme": "expanding_walk_forward",
        "fold_count": 2,
        "classification_threshold": 0.5,
        "out_of_sample_date_range": {
            "decision_start": "2024-04-30",
            "decision_end": "2024-05-31",
            "realized_start": "2024-05-31",
            "realized_end": "2024-06-30",
        },
        "out_of_sample_evaluation": {
            "row_count": 8,
            "accuracy": 0.75,
            "roc_auc": 0.8,
            "average_precision": 0.78,
        },
        "deterministic_baseline_context": {
            "enabled": True,
            "score_column": "composite_score",
            "class_column": "selected_top_n",
        },
    }


def _model_backtest_summary_fixture() -> dict[str, object]:
    return {
        "formation_start_date": "2024-04-30",
        "formation_end_date": "2024-05-31",
        "realized_start_date": "2024-05-31",
        "realized_end_date": "2024-06-30",
        "holding_period_convention": "Signals at t form holdings for realized returns at t+1.",
        "prediction_score_column": "predicted_probability",
        "prediction_splits_used": ["test"],
        "qc": {"benchmark_alignment_ok": True, "missing_realized_return_count": 0},
    }


def _deterministic_overlap_performance_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-04-30", "2024-05-31", "2024-06-30"]),
            "formation_date": pd.to_datetime(["2024-03-31", "2024-04-30", "2024-05-31"]),
            "portfolio_net_return": [0.005, 0.01, 0.02],
            "portfolio_gross_return": [0.006, 0.011, 0.021],
            "turnover": [0.0, 0.2, 0.1],
            "benchmark_return__SPY": [0.008, 0.018, 0.012],
            "benchmark_return__QQQ": [0.009, 0.017, 0.011],
            "benchmark_return__equal_weight_universe": [0.01, 0.02, 0.013],
        }
    )


def _model_performance_by_period_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-05-31", "2024-06-30"]),
            "formation_date": pd.to_datetime(["2024-04-30", "2024-05-31"]),
            "portfolio_net_return": [0.02, 0.01],
            "portfolio_gross_return": [0.021, 0.011],
            "turnover": [0.4, 0.1],
            "benchmark_return__SPY": [0.018, 0.012],
            "benchmark_return__QQQ": [0.017, 0.011],
            "benchmark_return__equal_weight_universe": [0.02, 0.013],
        }
    )


def _model_portfolio_returns_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-05-31", "2024-06-30"]),
            "formation_date": pd.to_datetime(["2024-04-30", "2024-05-31"]),
            "portfolio_net_return": [0.02, 0.01],
            "turnover": [0.4, 0.1],
        }
    )


def _model_test_predictions_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT", "AAPL", "MSFT"],
            "date": pd.to_datetime(["2024-04-30", "2024-04-30", "2024-05-31", "2024-05-31"]),
            "realized_label_date": pd.to_datetime(
                ["2024-05-31", "2024-05-31", "2024-06-30", "2024-06-30"]
            ),
            "fold_id": ["fold_001", "fold_001", "fold_002", "fold_002"],
            "fold_index": [1, 1, 2, 2],
            "ticker_score": [0.2, 0.8, 0.3, 0.7],
        }
    )


def test_build_evaluation_summary_includes_benchmark_comparison() -> None:
    """Evaluation summaries should include benchmark-aware comparisons and caveats."""
    project_config = load_project_config()
    signal_config = load_signal_pipeline_config()
    backtest_config = load_backtest_pipeline_config()

    summary = build_evaluation_summary(
        project_config=project_config,
        signal_config=signal_config,
        backtest_config=backtest_config,
        backtest_summary=_backtest_summary_fixture(),
        portfolio_returns=_portfolio_returns_fixture(),
        performance_by_period=_performance_by_period_fixture(),
        risk_metrics_summary=_risk_metrics_summary_fixture(),
    )

    assert summary["status"] == "exploratory_completed"
    assert summary["benchmark_set"] == ["SPY", "QQQ", "equal_weight_universe"]
    assert len(summary["feature_set"]) >= 1
    assert len(summary["benchmark_comparison"]) == 3
    assert len(summary["bias_caveats"]) >= 1


def test_render_strategy_report_outputs_key_sections() -> None:
    """Rendered reports should contain the main reporting sections."""
    project_config = load_project_config()
    signal_config = load_signal_pipeline_config()
    backtest_config = load_backtest_pipeline_config()
    summary = build_evaluation_summary(
        project_config=project_config,
        signal_config=signal_config,
        backtest_config=backtest_config,
        backtest_summary=_backtest_summary_fixture(),
        portfolio_returns=_portfolio_returns_fixture(),
        performance_by_period=_performance_by_period_fixture(),
        risk_metrics_summary=_risk_metrics_summary_fixture(),
    )

    report = render_strategy_report(
        summary,
        strategy_report_path="outputs/reports/strategy_report.md",
        registry_path="outputs/reports/experiment_registry.jsonl",
    )

    assert "# Strategy Report" in report
    assert "## Portfolio Summary" in report
    assert "## Benchmark Comparison" in report
    assert "## Bias Caveats" in report


def test_build_model_evaluation_summary_includes_model_diagnostics() -> None:
    """Model evaluation summaries should include both model and portfolio context."""
    project_config = load_project_config()
    model_config = load_model_pipeline_config()
    backtest_config = load_backtest_pipeline_config()

    summary = build_model_evaluation_summary(
        project_config=project_config,
        model_config=model_config,
        backtest_config=backtest_config,
        model_metadata=_model_metadata_fixture(),
        model_backtest_summary=_model_backtest_summary_fixture(),
        portfolio_returns=_model_portfolio_returns_fixture(),
        performance_by_period=_model_performance_by_period_fixture(),
        deterministic_performance_by_period=_deterministic_overlap_performance_fixture(),
        risk_metrics_summary=_risk_metrics_summary_fixture(),
        test_predictions=_model_test_predictions_fixture(),
    )

    assert summary["status"] == "exploratory_completed"
    assert summary["model_diagnostics"]["split_scheme"] == "expanding_walk_forward"
    assert summary["model_diagnostics"]["fold_count"] == 2
    assert summary["model_diagnostics"]["out_of_sample_evaluation"]["accuracy"] == 0.75
    assert summary["fold_diagnostics"]["heldout_decision_month_count"] == 2
    assert summary["deterministic_baseline_overlap_comparison"]["overlap_period_count"] == 2
    assert (
        summary["deterministic_baseline_overlap_comparison"]["comparison_metrics"][
            "cumulative_return_gap"
        ]
        == 0.0
    )


def test_render_model_strategy_report_outputs_key_sections() -> None:
    """Rendered model reports should contain diagnostics and portfolio sections."""
    project_config = load_project_config()
    model_config = load_model_pipeline_config()
    backtest_config = load_backtest_pipeline_config()
    summary = build_model_evaluation_summary(
        project_config=project_config,
        model_config=model_config,
        backtest_config=backtest_config,
        model_metadata=_model_metadata_fixture(),
        model_backtest_summary=_model_backtest_summary_fixture(),
        portfolio_returns=_model_portfolio_returns_fixture(),
        performance_by_period=_model_performance_by_period_fixture(),
        deterministic_performance_by_period=_deterministic_overlap_performance_fixture(),
        risk_metrics_summary=_risk_metrics_summary_fixture(),
        test_predictions=_model_test_predictions_fixture(),
    )

    report = render_model_strategy_report(
        summary,
        strategy_report_path="outputs/reports/model_strategy_report.md",
        registry_path="outputs/reports/experiment_registry.jsonl",
    )

    assert "# Model Strategy Report" in report
    assert "## Model Diagnostics" in report
    assert "## Fold Coverage" in report
    assert "## Portfolio Summary" in report
    assert "## Deterministic Baseline Overlap Comparison" in report
    assert "## Benchmark Comparison" in report


def test_build_experiment_record_and_append_jsonl() -> None:
    """Experiment registry records should append as valid JSONL rows."""
    project_config = load_project_config()
    signal_config = load_signal_pipeline_config()
    backtest_config = load_backtest_pipeline_config()
    summary = build_evaluation_summary(
        project_config=project_config,
        signal_config=signal_config,
        backtest_config=backtest_config,
        backtest_summary=_backtest_summary_fixture(),
        portfolio_returns=_portfolio_returns_fixture(),
        performance_by_period=_performance_by_period_fixture(),
        risk_metrics_summary=_risk_metrics_summary_fixture(),
    )

    record = build_experiment_record(
        summary,
        artifacts_written=[
            "outputs/reports/strategy_report.md",
            "outputs/reports/experiment_registry.jsonl",
        ],
    )
    registry_path = (
        Path("C:\\Users\\golde\\OneDrive - University of Virginia\\MarketResearch_ML")
        / ".tmp"
        / f"test_experiment_registry_{uuid4().hex}.jsonl"
    )
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    if registry_path.exists():
        registry_path.unlink()
    append_experiment_record(record, registry_path)

    stored = [json.loads(line) for line in registry_path.read_text(encoding="utf-8").splitlines()]

    assert len(stored) == 1
    assert stored[0]["stage"] == "evaluation_report"
    assert stored[0]["status"] == "exploratory_completed"
    assert "portfolio_net_cumulative_return" in stored[0]["result_summary"]
    registry_path.unlink()


def test_build_model_experiment_record_and_append_jsonl() -> None:
    """Model evaluation registry records should append as valid JSONL rows."""
    project_config = load_project_config()
    model_config = load_model_pipeline_config()
    backtest_config = load_backtest_pipeline_config()
    summary = build_model_evaluation_summary(
        project_config=project_config,
        model_config=model_config,
        backtest_config=backtest_config,
        model_metadata=_model_metadata_fixture(),
        model_backtest_summary=_model_backtest_summary_fixture(),
        portfolio_returns=_model_portfolio_returns_fixture(),
        performance_by_period=_model_performance_by_period_fixture(),
        deterministic_performance_by_period=_deterministic_overlap_performance_fixture(),
        risk_metrics_summary=_risk_metrics_summary_fixture(),
        test_predictions=_model_test_predictions_fixture(),
    )

    record = build_model_experiment_record(
        summary,
        artifacts_written=[
            "outputs/reports/model_strategy_report.md",
            "outputs/reports/model_comparison_summary.json",
            "outputs/reports/experiment_registry.jsonl",
        ],
    )
    registry_path = (
        Path("C:\\Users\\golde\\OneDrive - University of Virginia\\MarketResearch_ML")
        / ".tmp"
        / f"test_model_experiment_registry_{uuid4().hex}.jsonl"
    )
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    if registry_path.exists():
        registry_path.unlink()
    append_experiment_record(record, registry_path)

    stored = [json.loads(line) for line in registry_path.read_text(encoding="utf-8").splitlines()]

    assert len(stored) == 1
    assert stored[0]["stage"] == "model_evaluation_report"
    assert stored[0]["status"] == "exploratory_completed"
    assert "out_of_sample_evaluation" in stored[0]["result_summary"]
    assert "deterministic_baseline_overlap_comparison" in stored[0]["result_summary"]
    registry_path.unlink()
