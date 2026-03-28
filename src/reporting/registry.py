"""Experiment-registry record creation and append helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from src.data.io import ensure_parent_directory


def _json_safe(value: Any) -> Any:
    """Recursively convert data into JSON-serializable Python objects."""
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if pd.isna(value):
        return None
    return value


def build_experiment_record(
    summary: dict[str, Any],
    *,
    artifacts_written: list[str],
) -> dict[str, Any]:
    """Build the canonical experiment-registry record for a reporting run."""
    portfolio_net = summary["portfolio_metrics"]["net"]
    return _json_safe(
        {
            "experiment_id": f"evaluation_report_{uuid4().hex[:12]}",
            "run_timestamp": summary["generated_at_utc"],
            "stage": "evaluation_report",
            "purpose": summary["purpose"],
            "date_range": summary["date_range"],
            "universe_preset": summary["universe_preset"],
            "benchmark_set": summary["benchmark_set"],
            "feature_set": summary["feature_set"],
            "signal_or_model": summary["signal_or_model"],
            "portfolio_rules": summary["portfolio_rules"],
            "rebalance_frequency": summary["rebalance_frequency"],
            "transaction_cost_bps": summary["transaction_cost_bps"],
            "artifacts_written": artifacts_written,
            "result_summary": {
                "portfolio_net_cumulative_return": portfolio_net.get("cumulative_return"),
                "portfolio_net_annualized_return": portfolio_net.get("annualized_return"),
                "portfolio_net_sharpe_ratio": portfolio_net.get("sharpe_ratio"),
                "realized_period_count": summary["sample_characteristics"]["realized_period_count"],
                "benchmark_comparison": summary["benchmark_comparison"],
            },
            "interpretation": summary["interpretation"],
            "status": summary["status"],
            "next_step": summary["next_step"],
        }
    )


def append_experiment_record(record: dict[str, Any], path: Path) -> None:
    """Append one experiment record to the canonical JSONL registry."""
    ensure_parent_directory(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True))
        handle.write("\n")
