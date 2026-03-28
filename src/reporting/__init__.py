"""Reporting helpers for the market research system."""

from src.reporting.markdown import render_strategy_report
from src.reporting.registry import append_experiment_record, build_experiment_record

__all__ = [
    "append_experiment_record",
    "build_experiment_record",
    "render_strategy_report",
]
