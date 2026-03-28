"""Focused tests for evaluation and reporting outputs."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from src.backtest.config import load_backtest_pipeline_config
from src.evaluation.summary import build_evaluation_summary
from src.reporting.markdown import render_strategy_report
from src.reporting.registry import append_experiment_record, build_experiment_record
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
