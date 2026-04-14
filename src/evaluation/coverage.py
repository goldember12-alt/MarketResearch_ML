"""Cross-stage coverage summaries used by reporting and registry outputs."""

from __future__ import annotations

from typing import Any

from src.utils.config import ProjectConfig


_SEEDED_SELECTION_KINDS = {"seeded_sample", "seeded_sample_fallback"}


def _stage_entry_from_qc(
    qc_summary: dict[str, Any],
    *,
    identifier_key: str,
) -> dict[str, Any]:
    """Build a compact stage-coverage entry from one QC-style summary payload."""
    return {
        "row_count": int(qc_summary.get("row_count", 0) or 0),
        "unique_identifier_count": int(qc_summary.get(identifier_key, 0) or 0),
        "unique_date_count": int(qc_summary.get("unique_date_count", 0) or 0),
        "min_date": qc_summary.get("min_date"),
        "max_date": qc_summary.get("max_date"),
    }


def _aggregate_raw_data_selection(
    *summaries: dict[str, Any],
) -> dict[str, Any]:
    """Aggregate raw-file selection metadata across the ingestion-stage datasets."""
    raw_selection = {
        summary.get("dataset_name"): summary.get("raw_file_selection")
        for summary in summaries
        if summary.get("raw_file_selection") is not None
    }
    dataset_overview = {
        dataset_name: _build_raw_dataset_overview(selection)
        for dataset_name, selection in raw_selection.items()
    }
    broader_local_raw_available = any(
        bool(selection.get("broader_raw_files_available"))
        for selection in raw_selection.values()
    )
    seeded_sample_fallback_used = any(
        bool(selection.get("used_seeded_sample_fallback")) for selection in raw_selection.values()
    )
    datasets_using_seeded_sample_inputs = sorted(
        dataset_name
        for dataset_name, selection in raw_selection.items()
        if selection.get("selected_source_kind") in _SEEDED_SELECTION_KINDS
    )
    datasets_using_broader_local_raw_inputs = sorted(
        dataset_name
        for dataset_name, selection in raw_selection.items()
        if selection.get("selected_source_kind") == "broader_local_raw"
    )
    datasets_with_broader_local_raw_available = sorted(
        dataset_name
        for dataset_name, selection in raw_selection.items()
        if bool(selection.get("broader_raw_files_available"))
    )
    datasets_using_seeded_sample_fallback = sorted(
        dataset_name
        for dataset_name, selection in raw_selection.items()
        if bool(selection.get("used_seeded_sample_fallback"))
    )
    selected_input_profile = _classify_selected_input_profile(
        dataset_overview=dataset_overview,
    )
    return {
        "datasets": raw_selection,
        "dataset_overview": dataset_overview,
        "selected_input_profile": selected_input_profile,
        "uses_only_seeded_sample_inputs": bool(dataset_overview)
        and not datasets_using_broader_local_raw_inputs,
        "uses_any_broader_local_raw_inputs": bool(datasets_using_broader_local_raw_inputs),
        "datasets_using_seeded_sample_inputs": datasets_using_seeded_sample_inputs,
        "datasets_using_broader_local_raw_inputs": datasets_using_broader_local_raw_inputs,
        "datasets_with_broader_local_raw_available": datasets_with_broader_local_raw_available,
        "datasets_using_seeded_sample_fallback": datasets_using_seeded_sample_fallback,
        "broader_local_raw_available": broader_local_raw_available,
        "broader_local_raw_available_on_disk": broader_local_raw_available,
        "seeded_sample_fallback_used": seeded_sample_fallback_used,
        "seeded_sample_fallback_used_in_run": seeded_sample_fallback_used,
    }


def _classify_selected_input_profile(
    *,
    dataset_overview: dict[str, dict[str, Any]],
) -> str:
    """Describe the raw-input mix actually selected for the current run."""
    if not dataset_overview:
        return "no_selection_recorded"

    uses_seeded_inputs = any(
        bool(overview.get("selected_seeded_sample_input"))
        for overview in dataset_overview.values()
    )
    uses_broader_inputs = any(
        bool(overview.get("selected_broader_local_raw_input"))
        for overview in dataset_overview.values()
    )
    if uses_seeded_inputs and uses_broader_inputs:
        return "mixed_selected_inputs"
    if uses_broader_inputs:
        return "broader_local_raw_only"
    return "seeded_sample_only"


def _build_raw_dataset_overview(selection: dict[str, Any]) -> dict[str, Any]:
    """Build a compact raw-source overview for one ingestion-stage dataset."""
    selected_file_details = selection.get("selected_file_details", [])
    selected_source_kind = selection.get("selected_source_kind")
    return {
        "selected_source_kind": selected_source_kind,
        "selected_seeded_sample_input": selected_source_kind in _SEEDED_SELECTION_KINDS,
        "selected_broader_local_raw_input": selected_source_kind == "broader_local_raw",
        "selected_file_count": int(selection.get("selected_file_count", 0) or 0),
        "selected_file_names": [
            str(detail.get("file_name"))
            for detail in selected_file_details
            if detail.get("file_name") is not None
        ],
        "available_sample_file_count": int(
            selection.get("available_sample_file_count", 0) or 0
        ),
        "available_non_sample_file_count": int(
            selection.get("available_non_sample_file_count", 0) or 0
        ),
        "broader_raw_files_available": bool(selection.get("broader_raw_files_available")),
        "broader_local_raw_available_on_disk": bool(
            selection.get("broader_raw_files_available")
        ),
        "used_seeded_sample_fallback": bool(selection.get("used_seeded_sample_fallback")),
        "seeded_sample_fallback_used_in_run": bool(
            selection.get("used_seeded_sample_fallback")
        ),
        "observed_total_row_count": int(selection.get("observed_total_row_count", 0) or 0),
        "observed_date_columns": [
            str(column) for column in selection.get("observed_date_columns", [])
        ],
        "observed_min_date": selection.get("observed_min_date"),
        "observed_max_date": selection.get("observed_max_date"),
    }


def build_stage_coverage_summary(
    *,
    project_config: ProjectConfig,
    prices_qc_summary: dict[str, Any],
    fundamentals_qc_summary: dict[str, Any],
    benchmarks_qc_summary: dict[str, Any],
    panel_qc_summary: dict[str, Any],
    feature_qc_summary: dict[str, Any],
    signal_qc_summary: dict[str, Any] | None,
    backtest_summary: dict[str, Any] | None,
    model_metadata: dict[str, Any] | None = None,
    fold_diagnostics: dict[str, Any] | None = None,
    model_backtest_summary: dict[str, Any] | None = None,
    overlap_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic cross-stage coverage summary for the current run context."""
    stage_entries: dict[str, Any] = {
        "prices_monthly": _stage_entry_from_qc(
            prices_qc_summary,
            identifier_key="unique_identifier_count",
        ),
        "fundamentals_monthly": _stage_entry_from_qc(
            fundamentals_qc_summary,
            identifier_key="unique_identifier_count",
        ),
        "benchmarks_monthly": _stage_entry_from_qc(
            benchmarks_qc_summary,
            identifier_key="unique_identifier_count",
        ),
        "monthly_panel": {
            "row_count": int(panel_qc_summary.get("row_count", 0) or 0),
            "unique_ticker_count": int(panel_qc_summary.get("unique_ticker_count", 0) or 0),
            "unique_date_count": int(panel_qc_summary.get("unique_date_count", 0) or 0),
            "min_date": panel_qc_summary.get("min_date"),
            "max_date": panel_qc_summary.get("max_date"),
        },
        "feature_panel": {
            "row_count": int(feature_qc_summary.get("row_count", 0) or 0),
            "unique_ticker_count": int(feature_qc_summary.get("unique_ticker_count", 0) or 0),
            "unique_date_count": int(feature_qc_summary.get("unique_date_count", 0) or 0),
            "min_date": feature_qc_summary.get("min_date"),
            "max_date": feature_qc_summary.get("max_date"),
        },
    }
    if signal_qc_summary is not None:
        stage_entries["signal_rankings"] = {
            "row_count": int(signal_qc_summary.get("row_count", 0) or 0),
            "unique_ticker_count": int(signal_qc_summary.get("unique_ticker_count", 0) or 0),
            "unique_date_count": int(signal_qc_summary.get("unique_date_count", 0) or 0),
            "fully_scored_row_count": int(signal_qc_summary.get("fully_scored_row_count", 0) or 0),
            "min_date": signal_qc_summary.get("min_date"),
            "max_date": signal_qc_summary.get("max_date"),
        }
    if backtest_summary is not None:
        stage_entries["deterministic_backtest"] = {
            "formation_month_count": int(
                backtest_summary.get("coverage", {}).get("formation_month_count", 0) or 0
            ),
            "realized_month_count": int(
                backtest_summary.get("coverage", {}).get("realized_month_count", 0) or 0
            ),
            "unique_held_ticker_count": int(
                backtest_summary.get("coverage", {}).get("unique_held_ticker_count", 0) or 0
            ),
            "realized_start": backtest_summary.get("realized_start_date"),
            "realized_end": backtest_summary.get("realized_end_date"),
        }
    if model_metadata is not None:
        eligible_dataset_summary = model_metadata.get("eligible_dataset_summary", {})
        stage_entries["model_dataset_eligible"] = {
            "eligible_row_count": int(eligible_dataset_summary.get("eligible_row_count", 0) or 0),
            "eligible_decision_month_count": int(
                eligible_dataset_summary.get("eligible_decision_month_count", 0) or 0
            ),
            "eligible_realized_month_count": int(
                eligible_dataset_summary.get("eligible_realized_month_count", 0) or 0
            ),
            "eligible_unique_ticker_count": int(
                eligible_dataset_summary.get("eligible_unique_ticker_count", 0) or 0
            ),
            "decision_start": eligible_dataset_summary.get("eligible_decision_date_range", {}).get(
                "decision_start"
            ),
            "decision_end": eligible_dataset_summary.get("eligible_decision_date_range", {}).get(
                "decision_end"
            ),
            "realized_start": eligible_dataset_summary.get("eligible_decision_date_range", {}).get(
                "realized_start"
            ),
            "realized_end": eligible_dataset_summary.get("eligible_decision_date_range", {}).get(
                "realized_end"
            ),
        }
    if fold_diagnostics is not None:
        stage_entries["model_out_of_sample_predictions"] = {
            "heldout_row_count": int(fold_diagnostics.get("heldout_row_count", 0) or 0),
            "heldout_decision_month_count": int(
                fold_diagnostics.get("heldout_decision_month_count", 0) or 0
            ),
            "heldout_realized_month_count": int(
                fold_diagnostics.get("heldout_realized_month_count", 0) or 0
            ),
            "heldout_unique_ticker_count": int(
                fold_diagnostics.get("heldout_unique_ticker_count", 0) or 0
            ),
            "decision_start": fold_diagnostics.get("decision_start"),
            "decision_end": fold_diagnostics.get("decision_end"),
            "realized_start": fold_diagnostics.get("realized_start"),
            "realized_end": fold_diagnostics.get("realized_end"),
        }
    if model_backtest_summary is not None:
        stage_entries["model_backtest"] = {
            "formation_month_count": int(
                model_backtest_summary.get("coverage", {}).get("formation_month_count", 0) or 0
            ),
            "realized_month_count": int(
                model_backtest_summary.get("coverage", {}).get("realized_month_count", 0) or 0
            ),
            "unique_held_ticker_count": int(
                model_backtest_summary.get("coverage", {}).get("unique_held_ticker_count", 0) or 0
            ),
            "realized_start": model_backtest_summary.get("realized_start_date"),
            "realized_end": model_backtest_summary.get("realized_end_date"),
        }
    if overlap_summary is not None:
        stage_entries["deterministic_model_overlap"] = {
            "realized_overlap_month_count": int(
                overlap_summary.get("overlap_period_count", 0) or 0
            ),
            "realized_start": overlap_summary.get("realized_start"),
            "realized_end": overlap_summary.get("realized_end"),
        }

    return {
        "execution_mode": project_config.execution.mode_name,
        "execution_description": project_config.execution.description,
        "raw_data_selection": _aggregate_raw_data_selection(
            prices_qc_summary,
            fundamentals_qc_summary,
            benchmarks_qc_summary,
        ),
        "stages": stage_entries,
    }


def build_run_summary_artifact(
    *,
    summary: dict[str, Any],
    stage: str,
    artifacts_written: list[str],
) -> dict[str, Any]:
    """Build the machine-readable top-level run summary artifact."""
    return {
        "generated_at_utc": summary["generated_at_utc"],
        "stage": stage,
        "status": summary["status"],
        "execution_mode": summary["execution_mode"],
        "universe_preset": summary["universe_preset"],
        "signal_or_model": summary["signal_or_model"],
        "date_range": summary["date_range"],
        "coverage_summary": summary["coverage_summary"],
        "evidence_context": summary["evidence_context"],
        "artifacts_written": artifacts_written,
        "next_step": summary["next_step"],
    }
