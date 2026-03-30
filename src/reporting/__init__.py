"""Reporting helpers for the market research system."""

from src.reporting.markdown import render_model_strategy_report, render_strategy_report
from src.reporting.registry import (
    append_experiment_record,
    build_experiment_record,
    build_model_experiment_record,
)

__all__ = [
    "append_experiment_record",
    "build_experiment_record",
    "build_model_experiment_record",
    "render_model_strategy_report",
    "render_strategy_report",
]
