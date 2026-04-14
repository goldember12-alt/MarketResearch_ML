"""CLI entrypoint for upstream Alpha Vantage + SEC remote raw-data acquisition."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.alphavantage import fetch_monthly_adjusted_series, fetch_overview_metadata
from src.data.config import configure_logging
from src.data.remote_config import (
    DatasetOutputConfig,
    RemoteRawFetchConfig,
    load_remote_raw_fetch_config,
)
from src.data.remote_io import (
    build_dataset_manifest,
    enforce_overwrite_policy,
    format_utc_timestamp,
    resolve_dataset_output_targets,
    utc_now,
    write_dataset_manifest,
    write_tabular_data,
    write_text_payload,
)
from src.data.sec_companyfacts import fetch_sec_companyfacts, resolve_sec_user_agent


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the remote raw-data acquisition CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch immutable remote raw snapshots upstream of src.run_data_ingestion.",
    )
    parser.add_argument(
        "--provider",
        choices=("alphavantage_sec",),
        default="alphavantage_sec",
        help="Configured remote raw-data provider bundle to fetch.",
    )
    parser.add_argument(
        "--execution-mode",
        choices=("seeded", "research_scale"),
        default=None,
        help=(
            "Execution context to record in manifests. "
            "'research_scale' is the intended mode for broader non-sample raw refreshes."
        ),
    )
    return parser.parse_args(argv)


def _frame_date_span(frame: pd.DataFrame, date_column: str) -> tuple[str | None, str | None]:
    """Return an ISO min/max date span for one fetched frame."""
    if frame.empty or date_column not in frame.columns:
        return None, None
    parsed = pd.to_datetime(frame[date_column], errors="coerce").dropna()
    if parsed.empty:
        return None, None
    return parsed.min().date().isoformat(), parsed.max().date().isoformat()


def _summarize_frame(frame: pd.DataFrame, date_column: str) -> dict[str, Any]:
    """Return row-count and date-span diagnostics for one frame."""
    min_date, max_date = _frame_date_span(frame, date_column)
    return {
        "row_count": int(len(frame)),
        "min_date": min_date,
        "max_date": max_date,
    }


def _aggregate_symbol_outcomes(dataset_manifests: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Aggregate unique completed and failed symbols across dataset manifests."""
    completed_symbols = sorted(
        {
            symbol
            for manifest in dataset_manifests
            for symbol in manifest.get("completed_symbols", [])
        }
    )
    failed_symbols = sorted(
        {symbol for manifest in dataset_manifests for symbol in manifest.get("failed_symbols", [])}
    )
    return {
        "completed_symbols": completed_symbols,
        "failed_symbols": failed_symbols,
    }


def _resolve_manifest_path(output_config: DatasetOutputConfig, timestamp_token: str) -> Path | None:
    """Resolve the manifest path for one dataset without writing data files yet."""
    return resolve_dataset_output_targets(
        base_dir=output_config.base_dir,
        latest_filename=output_config.latest_filename,
        snapshot_subdir=None,
        snapshot_filename_template=None,
        manifest_subdir=output_config.manifest_subdir,
        latest_manifest_filename=output_config.latest_manifest_filename,
        timestamp_token=timestamp_token,
    ).manifest_path


def _write_dataset_outputs(
    *,
    frame: pd.DataFrame,
    output_config: DatasetOutputConfig,
    config: RemoteRawFetchConfig,
    timestamp_token: str,
) -> list[str]:
    """Write latest, snapshot, and manifest outputs for one tabular dataset."""
    written_paths: list[str] = []
    if frame.empty:
        return written_paths
    targets = resolve_dataset_output_targets(
        base_dir=output_config.base_dir,
        latest_filename=output_config.latest_filename
        if config.acquisition.write_latest_files
        else None,
        snapshot_subdir=output_config.snapshot_subdir
        if config.acquisition.write_snapshot_copies
        else None,
        snapshot_filename_template=output_config.snapshot_filename_template,
        manifest_subdir=output_config.manifest_subdir
        if config.acquisition.write_dataset_manifests
        else None,
        latest_manifest_filename=output_config.latest_manifest_filename,
        timestamp_token=timestamp_token,
    )
    if targets.latest_path is not None:
        enforce_overwrite_policy(
            targets.latest_path,
            overwrite_policy=config.acquisition.latest_file_overwrite_policy,
        )
        write_tabular_data(frame, targets.latest_path)
        written_paths.append(str(targets.latest_path))
    if targets.snapshot_path is not None:
        enforce_overwrite_policy(targets.snapshot_path, overwrite_policy="fail")
        write_tabular_data(frame, targets.snapshot_path)
        written_paths.append(str(targets.snapshot_path))
    return written_paths


def _build_skipped_dataset_manifest(
    *,
    dataset_name: str,
    provider: str,
    endpoint: str,
    function: str | None,
    requested_symbols: list[str],
    skip_reason: str,
    fetch_started_at_utc: str,
    fetch_completed_at_utc: str,
    extra_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Build a manifest for one dataset stage skipped before provider calls."""
    return build_dataset_manifest(
        dataset_name=dataset_name,
        provider=provider,
        endpoint=endpoint,
        function=function,
        requested_symbols=requested_symbols,
        completed_symbols=[],
        failed_symbols=[],
        throttle_detected=True,
        partial_failure=True,
        fetch_started_at_utc=fetch_started_at_utc,
        fetch_completed_at_utc=fetch_completed_at_utc,
        output_files=[],
        row_count=0,
        min_date=None,
        max_date=None,
        notes=[skip_reason],
        extra_metadata=extra_metadata,
    )


def _write_raw_payload_snapshots(
    *,
    raw_payloads: dict[str, dict[str, Any]],
    output_config: DatasetOutputConfig,
    config: RemoteRawFetchConfig,
    timestamp_token: str,
) -> list[str]:
    """Write immutable raw SEC Company Facts JSON payload snapshots."""
    written_paths: list[str] = []
    if not config.acquisition.write_snapshot_copies:
        return written_paths
    if output_config.snapshot_subdir is None or output_config.snapshot_filename_template is None:
        return written_paths
    for symbol, payload in raw_payloads.items():
        relative_filename = output_config.snapshot_filename_template.format(
            symbol=symbol,
            timestamp=timestamp_token,
        )
        path = output_config.snapshot_subdir / relative_filename
        enforce_overwrite_policy(path, overwrite_policy="fail")
        write_text_payload(json.dumps(payload, indent=2, sort_keys=True), path)
        written_paths.append(str(path))
    return written_paths


def _require_alphavantage_api_key(config: RemoteRawFetchConfig) -> str:
    """Resolve the Alpha Vantage API key from the configured environment variable."""
    api_key = os.getenv(config.alphavantage.api_key_env_var, "").strip()
    if not api_key:
        raise ValueError(
            "Alpha Vantage remote fetch requires the environment variable "
            f"{config.alphavantage.api_key_env_var}."
        )
    return api_key


def _log_stage_start(
    logger: logging.Logger,
    *,
    fetch_run_id: str,
    stage_name: str,
    provider_name: str,
    symbols: list[str],
) -> None:
    """Log the start of one dataset stage with its requested scope."""
    logger.info(
        "fetch_stage_start run_id=%s stage=%s provider=%s requested_symbol_count=%s requested_symbols=%s",
        fetch_run_id,
        stage_name,
        provider_name,
        len(symbols),
        symbols,
    )


def _log_stage_summary(
    logger: logging.Logger,
    *,
    fetch_run_id: str,
    stage_name: str,
    provider_name: str,
    summary: dict[str, Any],
) -> None:
    """Log row-count and date-span diagnostics for one dataset stage."""
    logger.info(
        "fetch_stage_frame_summary run_id=%s stage=%s provider=%s row_count=%s min_date=%s max_date=%s",
        fetch_run_id,
        stage_name,
        provider_name,
        summary["row_count"],
        summary["min_date"],
        summary["max_date"],
    )
    if summary["row_count"] == 0:
        logger.warning(
            "fetch_stage_no_rows run_id=%s stage=%s provider=%s",
            fetch_run_id,
            stage_name,
            provider_name,
        )


def _log_written_paths(
    logger: logging.Logger,
    *,
    fetch_run_id: str,
    stage_name: str,
    paths: list[str],
) -> None:
    """Log every output path written for one dataset stage."""
    for path in paths:
        logger.info(
            "fetch_stage_wrote_path run_id=%s stage=%s path=%s",
            fetch_run_id,
            stage_name,
            path,
        )


def _log_stage_end(
    logger: logging.Logger,
    *,
    fetch_run_id: str,
    stage_name: str,
    provider_name: str,
    manifest: dict[str, Any],
    elapsed_seconds: float,
) -> None:
    """Log the end-of-stage result summary."""
    logger.info(
        "fetch_stage_complete run_id=%s stage=%s provider=%s completed_symbols=%s failed_symbols=%s throttle_detected=%s partial_failure=%s elapsed_seconds=%.3f",
        fetch_run_id,
        stage_name,
        provider_name,
        manifest["completed_symbols"],
        manifest["failed_symbols"],
        manifest["throttle_detected"],
        manifest["partial_failure"],
        elapsed_seconds,
    )
    if not manifest["completed_symbols"]:
        logger.warning(
            "fetch_stage_completed_no_symbols run_id=%s stage=%s provider=%s failed_symbols=%s",
            fetch_run_id,
            stage_name,
            provider_name,
            manifest["failed_symbols"],
        )


def _log_stage_skipped(
    logger: logging.Logger,
    *,
    fetch_run_id: str,
    stage_name: str,
    provider_name: str,
    skip_reason: str,
) -> None:
    """Log when one dataset stage is skipped before provider calls."""
    logger.warning(
        "fetch_stage_skipped run_id=%s stage=%s provider=%s reason=%s",
        fetch_run_id,
        stage_name,
        provider_name,
        skip_reason,
    )


def _build_dataset_extra_metadata(
    *,
    fetch_run_id: str,
    stage_elapsed_seconds: float,
    config: RemoteRawFetchConfig,
    requested_symbols: list[str],
    completed_symbols: list[str],
    failed_symbols: list[str],
) -> dict[str, Any]:
    """Build concise extra metadata for one dataset manifest."""
    return {
        "fetch_run_id": fetch_run_id,
        "requested_execution_mode": config.project.execution.mode_name,
        "requested_symbol_count": len(requested_symbols),
        "completed_symbol_count": len(completed_symbols),
        "failed_symbol_count": len(failed_symbols),
        "stage_elapsed_seconds": round(stage_elapsed_seconds, 3),
        "write_latest_files": config.acquisition.write_latest_files,
        "write_snapshot_copies": config.acquisition.write_snapshot_copies,
        "write_dataset_manifests": config.acquisition.write_dataset_manifests,
        "latest_file_overwrite_policy": config.acquisition.latest_file_overwrite_policy,
    }


def _build_run_manifest(
    *,
    config: RemoteRawFetchConfig,
    provider_name: str,
    fetch_run_id: str,
    fetch_started_at_utc: str,
    fetch_completed_at_utc: str,
    dataset_manifests: list[dict[str, Any]],
    environment_presence: dict[str, bool],
) -> dict[str, Any]:
    """Build the top-level remote fetch run manifest."""
    symbol_outcomes = _aggregate_symbol_outcomes(dataset_manifests)
    return {
        "fetch_run_id": fetch_run_id,
        "provider_bundle": provider_name,
        "requested_execution_mode": config.project.execution.mode_name,
        "execution_description": config.project.execution.description,
        "fetch_started_at_utc": fetch_started_at_utc,
        "fetch_completed_at_utc": fetch_completed_at_utc,
        "requested_universe_symbols": list(config.project.universe.all_tickers),
        "requested_benchmark_symbols": list(config.project.universe.explicit_benchmarks),
        "completed_symbols": symbol_outcomes["completed_symbols"],
        "failed_symbols": symbol_outcomes["failed_symbols"],
        "dataset_manifests": dataset_manifests,
        "partial_failure": any(manifest["partial_failure"] for manifest in dataset_manifests),
        "throttle_detected": any(manifest["throttle_detected"] for manifest in dataset_manifests),
        "write_latest_files": config.acquisition.write_latest_files,
        "write_snapshot_copies": config.acquisition.write_snapshot_copies,
        "write_dataset_manifests": config.acquisition.write_dataset_manifests,
        "latest_file_overwrite_policy": config.acquisition.latest_file_overwrite_policy,
        "environment_presence": environment_presence,
    }


def main(argv: list[str] | None = None) -> int:
    """Fetch remote raw-data snapshots without changing downstream live-API behavior."""
    args = parse_args(argv)
    config = load_remote_raw_fetch_config(execution_mode=args.execution_mode)
    configure_logging(config.data_pipeline)
    logger = logging.getLogger(__name__)
    provider_name = args.provider or config.acquisition.default_provider
    if provider_name != "alphavantage_sec":
        raise ValueError(f"Unsupported provider bundle: {provider_name}")

    fetch_started = utc_now()
    fetch_started_at_utc = fetch_started.isoformat()
    timestamp_token = format_utc_timestamp(
        fetch_started, config.acquisition.snapshot_timestamp_format
    )
    fetch_run_id = f"{provider_name}_{timestamp_token}"
    run_started_perf = time.perf_counter()
    dataset_manifests: list[dict[str, Any]] = []
    all_written_paths: list[str] = []
    alphavantage_daily_quota_detected = False

    environment_presence = {
        "alphavantage_api_key_present": bool(
            os.getenv(config.alphavantage.api_key_env_var, "").strip()
        ),
        "sec_user_agent_present": bool(os.getenv(config.sec.user_agent_env_var, "").strip()),
        "sec_contact_email_present": bool(
            os.getenv(config.sec.contact_email_env_var, "").strip()
        ),
    }

    logger.info(
        "fetch_run_start run_id=%s provider_bundle=%s execution_mode=%s",
        fetch_run_id,
        provider_name,
        config.project.execution.mode_name,
    )
    logger.info(
        "fetch_run_environment run_id=%s alphavantage_api_key_env_var=%s present=%s sec_user_agent_env_var=%s present=%s sec_contact_email_env_var=%s present=%s",
        fetch_run_id,
        config.alphavantage.api_key_env_var,
        environment_presence["alphavantage_api_key_present"],
        config.sec.user_agent_env_var,
        environment_presence["sec_user_agent_present"],
        config.sec.contact_email_env_var,
        environment_presence["sec_contact_email_present"],
    )
    logger.info(
        "fetch_run_output_policy run_id=%s write_latest_files=%s write_snapshot_copies=%s write_dataset_manifests=%s latest_file_overwrite_policy=%s",
        fetch_run_id,
        config.acquisition.write_latest_files,
        config.acquisition.write_snapshot_copies,
        config.acquisition.write_dataset_manifests,
        config.acquisition.latest_file_overwrite_policy,
    )
    logger.info(
        "fetch_run_toggles run_id=%s overview_metadata=%s market_prices=%s benchmark_prices=%s sec_companyfacts=%s",
        fetch_run_id,
        config.toggles.overview_metadata,
        config.toggles.market_prices,
        config.toggles.benchmark_prices,
        config.toggles.sec_companyfacts,
    )

    overview_frame = pd.DataFrame()
    if config.toggles.overview_metadata:
        stage_name = "overview_metadata"
        requested_symbols = list(config.project.universe.all_tickers)
        stage_started_perf = time.perf_counter()
        _log_stage_start(
            logger,
            fetch_run_id=fetch_run_id,
            stage_name=stage_name,
            provider_name="alphavantage",
            symbols=requested_symbols,
        )
        api_key = _require_alphavantage_api_key(config)
        overview_started = utc_now().isoformat()
        overview_result = fetch_overview_metadata(
            symbols=requested_symbols,
            provider=config.alphavantage,
            api_key=api_key,
            logger=logger,
            dataset_name=stage_name,
            fetch_run_id=fetch_run_id,
        )
        alphavantage_daily_quota_detected = (
            alphavantage_daily_quota_detected or overview_result.daily_quota_detected
        )
        overview_frame = overview_result.frame.copy()
        if not overview_frame.empty:
            overview_frame["fetched_at_utc"] = fetch_started_at_utc
        overview_summary = _summarize_frame(overview_frame, "latest_quarter")
        _log_stage_summary(
            logger,
            fetch_run_id=fetch_run_id,
            stage_name=stage_name,
            provider_name="alphavantage",
            summary=overview_summary,
        )
        logger.info(
            "fetch_stage_write_plan run_id=%s stage=%s provider=%s latest_enabled=%s snapshot_enabled=%s manifest_enabled=%s base_dir=%s",
            fetch_run_id,
            stage_name,
            "alphavantage",
            config.acquisition.write_latest_files,
            config.acquisition.write_snapshot_copies,
            config.acquisition.write_dataset_manifests,
            config.outputs.overview.base_dir,
        )
        if overview_summary["row_count"] == 0:
            logger.warning(
                "fetch_stage_write_skipped_empty run_id=%s stage=%s provider=%s base_dir=%s",
                fetch_run_id,
                stage_name,
                "alphavantage",
                config.outputs.overview.base_dir,
            )
        overview_notes = overview_result.notes + [
            "Alpha Vantage overview metadata are point-in-time-unsafe snapshots and are only "
            "used here for classification enrichment such as sector and industry."
        ]
        overview_manifest = build_dataset_manifest(
            dataset_name=stage_name,
            provider="alphavantage",
            endpoint=config.alphavantage.base_url,
            function=config.alphavantage.overview_function,
            requested_symbols=requested_symbols,
            completed_symbols=overview_result.completed_symbols,
            failed_symbols=overview_result.failed_symbols,
            throttle_detected=overview_result.throttle_detected,
            partial_failure=bool(overview_result.failed_symbols),
            fetch_started_at_utc=overview_started,
            fetch_completed_at_utc=utc_now().isoformat(),
            output_files=[],
            row_count=overview_summary["row_count"],
            min_date=overview_summary["min_date"],
            max_date=overview_summary["max_date"],
            notes=overview_notes,
            extra_metadata=_build_dataset_extra_metadata(
                fetch_run_id=fetch_run_id,
                stage_elapsed_seconds=time.perf_counter() - stage_started_perf,
                config=config,
                requested_symbols=requested_symbols,
                completed_symbols=overview_result.completed_symbols,
                failed_symbols=overview_result.failed_symbols,
            ),
        )
        overview_written = _write_dataset_outputs(
            frame=overview_frame,
            output_config=config.outputs.overview,
            config=config,
            timestamp_token=timestamp_token,
        )
        overview_manifest["output_files"] = overview_written
        _log_written_paths(
            logger,
            fetch_run_id=fetch_run_id,
            stage_name=stage_name,
            paths=overview_written,
        )
        if config.acquisition.write_dataset_manifests:
            manifest_path = _resolve_manifest_path(config.outputs.overview, timestamp_token)
            if manifest_path is not None:
                write_dataset_manifest(overview_manifest, manifest_path)
                overview_manifest["output_files"].append(str(manifest_path))
                _log_written_paths(
                    logger,
                    fetch_run_id=fetch_run_id,
                    stage_name=stage_name,
                    paths=[str(manifest_path)],
                )
        dataset_manifests.append(overview_manifest)
        all_written_paths.extend(overview_manifest["output_files"])
        _log_stage_end(
            logger,
            fetch_run_id=fetch_run_id,
            stage_name=stage_name,
            provider_name="alphavantage",
            manifest=overview_manifest,
            elapsed_seconds=time.perf_counter() - stage_started_perf,
        )

    if config.toggles.market_prices:
        stage_name = "market_prices"
        requested_symbols = list(config.project.universe.all_tickers)
        stage_started_perf = time.perf_counter()
        _log_stage_start(
            logger,
            fetch_run_id=fetch_run_id,
            stage_name=stage_name,
            provider_name="alphavantage",
            symbols=requested_symbols,
        )
        if alphavantage_daily_quota_detected:
            skip_reason = (
                "Skipped because Alpha Vantage daily quota was already detected in an earlier "
                "stage of this fetch run."
            )
            _log_stage_skipped(
                logger,
                fetch_run_id=fetch_run_id,
                stage_name=stage_name,
                provider_name="alphavantage",
                skip_reason=skip_reason,
            )
            market_manifest = _build_skipped_dataset_manifest(
                dataset_name=stage_name,
                provider="alphavantage",
                endpoint=config.alphavantage.base_url,
                function=config.alphavantage.monthly_adjusted_function,
                requested_symbols=requested_symbols,
                skip_reason=skip_reason,
                fetch_started_at_utc=utc_now().isoformat(),
                fetch_completed_at_utc=utc_now().isoformat(),
                extra_metadata=_build_dataset_extra_metadata(
                    fetch_run_id=fetch_run_id,
                    stage_elapsed_seconds=time.perf_counter() - stage_started_perf,
                    config=config,
                    requested_symbols=requested_symbols,
                    completed_symbols=[],
                    failed_symbols=[],
                ),
            )
            if config.acquisition.write_dataset_manifests:
                manifest_path = _resolve_manifest_path(config.outputs.market, timestamp_token)
                if manifest_path is not None:
                    write_dataset_manifest(market_manifest, manifest_path)
                    market_manifest["output_files"].append(str(manifest_path))
                    _log_written_paths(
                        logger,
                        fetch_run_id=fetch_run_id,
                        stage_name=stage_name,
                        paths=[str(manifest_path)],
                    )
            dataset_manifests.append(market_manifest)
            all_written_paths.extend(market_manifest["output_files"])
            _log_stage_end(
                logger,
                fetch_run_id=fetch_run_id,
                stage_name=stage_name,
                provider_name="alphavantage",
                manifest=market_manifest,
                elapsed_seconds=time.perf_counter() - stage_started_perf,
            )
        else:
            api_key = _require_alphavantage_api_key(config)
            market_started = utc_now().isoformat()
            market_result = fetch_monthly_adjusted_series(
                symbols=requested_symbols,
                identifier_column="ticker",
                provider=config.alphavantage,
                api_key=api_key,
                logger=logger,
                dataset_name=stage_name,
                fetch_run_id=fetch_run_id,
            )
            alphavantage_daily_quota_detected = (
                alphavantage_daily_quota_detected or market_result.daily_quota_detected
            )
            market_frame = market_result.frame.copy()
            if not market_frame.empty:
                market_frame["fetched_at_utc"] = fetch_started_at_utc
            market_summary = _summarize_frame(market_frame, "date")
            _log_stage_summary(
                logger,
                fetch_run_id=fetch_run_id,
                stage_name=stage_name,
                provider_name="alphavantage",
                summary=market_summary,
            )
            logger.info(
                "fetch_stage_write_plan run_id=%s stage=%s provider=%s latest_enabled=%s snapshot_enabled=%s manifest_enabled=%s base_dir=%s",
                fetch_run_id,
                stage_name,
                "alphavantage",
                config.acquisition.write_latest_files,
                config.acquisition.write_snapshot_copies,
                config.acquisition.write_dataset_manifests,
                config.outputs.market.base_dir,
            )
            if market_summary["row_count"] == 0:
                logger.warning(
                    "fetch_stage_write_skipped_empty run_id=%s stage=%s provider=%s base_dir=%s",
                    fetch_run_id,
                    stage_name,
                    "alphavantage",
                    config.outputs.market.base_dir,
                )
            market_manifest = build_dataset_manifest(
                dataset_name=stage_name,
                provider="alphavantage",
                endpoint=config.alphavantage.base_url,
                function=config.alphavantage.monthly_adjusted_function,
                requested_symbols=requested_symbols,
                completed_symbols=market_result.completed_symbols,
                failed_symbols=market_result.failed_symbols,
                throttle_detected=market_result.throttle_detected,
                partial_failure=bool(market_result.failed_symbols),
                fetch_started_at_utc=market_started,
                fetch_completed_at_utc=utc_now().isoformat(),
                output_files=[],
                row_count=market_summary["row_count"],
                min_date=market_summary["min_date"],
                max_date=market_summary["max_date"],
                notes=market_result.notes
                + [
                    "Monthly adjusted Alpha Vantage history is used because it aligns to the "
                    "repo's monthly decision frequency and is more feasible on the free tier "
                    "than full-history daily adjusted endpoints."
                ],
                extra_metadata=_build_dataset_extra_metadata(
                    fetch_run_id=fetch_run_id,
                    stage_elapsed_seconds=time.perf_counter() - stage_started_perf,
                    config=config,
                    requested_symbols=requested_symbols,
                    completed_symbols=market_result.completed_symbols,
                    failed_symbols=market_result.failed_symbols,
                ),
            )
            market_written = _write_dataset_outputs(
                frame=market_frame,
                output_config=config.outputs.market,
                config=config,
                timestamp_token=timestamp_token,
            )
            market_manifest["output_files"] = market_written
            _log_written_paths(
                logger,
                fetch_run_id=fetch_run_id,
                stage_name=stage_name,
                paths=market_written,
            )
            if config.acquisition.write_dataset_manifests:
                manifest_path = _resolve_manifest_path(config.outputs.market, timestamp_token)
                if manifest_path is not None:
                    write_dataset_manifest(market_manifest, manifest_path)
                    market_manifest["output_files"].append(str(manifest_path))
                    _log_written_paths(
                        logger,
                        fetch_run_id=fetch_run_id,
                        stage_name=stage_name,
                        paths=[str(manifest_path)],
                    )
            dataset_manifests.append(market_manifest)
            all_written_paths.extend(market_manifest["output_files"])
            _log_stage_end(
                logger,
                fetch_run_id=fetch_run_id,
                stage_name=stage_name,
                provider_name="alphavantage",
                manifest=market_manifest,
                elapsed_seconds=time.perf_counter() - stage_started_perf,
            )

    if config.toggles.benchmark_prices:
        stage_name = "benchmark_prices"
        requested_symbols = list(config.project.universe.explicit_benchmarks)
        stage_started_perf = time.perf_counter()
        _log_stage_start(
            logger,
            fetch_run_id=fetch_run_id,
            stage_name=stage_name,
            provider_name="alphavantage",
            symbols=requested_symbols,
        )
        if alphavantage_daily_quota_detected:
            skip_reason = (
                "Skipped because Alpha Vantage daily quota was already detected in an earlier "
                "stage of this fetch run."
            )
            _log_stage_skipped(
                logger,
                fetch_run_id=fetch_run_id,
                stage_name=stage_name,
                provider_name="alphavantage",
                skip_reason=skip_reason,
            )
            benchmarks_manifest = _build_skipped_dataset_manifest(
                dataset_name=stage_name,
                provider="alphavantage",
                endpoint=config.alphavantage.base_url,
                function=config.alphavantage.monthly_adjusted_function,
                requested_symbols=requested_symbols,
                skip_reason=skip_reason,
                fetch_started_at_utc=utc_now().isoformat(),
                fetch_completed_at_utc=utc_now().isoformat(),
                extra_metadata=_build_dataset_extra_metadata(
                    fetch_run_id=fetch_run_id,
                    stage_elapsed_seconds=time.perf_counter() - stage_started_perf,
                    config=config,
                    requested_symbols=requested_symbols,
                    completed_symbols=[],
                    failed_symbols=[],
                ),
            )
            if config.acquisition.write_dataset_manifests:
                manifest_path = _resolve_manifest_path(config.outputs.benchmarks, timestamp_token)
                if manifest_path is not None:
                    write_dataset_manifest(benchmarks_manifest, manifest_path)
                    benchmarks_manifest["output_files"].append(str(manifest_path))
                    _log_written_paths(
                        logger,
                        fetch_run_id=fetch_run_id,
                        stage_name=stage_name,
                        paths=[str(manifest_path)],
                    )
            dataset_manifests.append(benchmarks_manifest)
            all_written_paths.extend(benchmarks_manifest["output_files"])
            _log_stage_end(
                logger,
                fetch_run_id=fetch_run_id,
                stage_name=stage_name,
                provider_name="alphavantage",
                manifest=benchmarks_manifest,
                elapsed_seconds=time.perf_counter() - stage_started_perf,
            )
        else:
            api_key = _require_alphavantage_api_key(config)
            benchmarks_started = utc_now().isoformat()
            benchmark_result = fetch_monthly_adjusted_series(
                symbols=requested_symbols,
                identifier_column="benchmark_ticker",
                provider=config.alphavantage,
                api_key=api_key,
                logger=logger,
                dataset_name=stage_name,
                fetch_run_id=fetch_run_id,
            )
            alphavantage_daily_quota_detected = (
                alphavantage_daily_quota_detected or benchmark_result.daily_quota_detected
            )
            benchmarks_frame = benchmark_result.frame.copy()
            if not benchmarks_frame.empty:
                benchmarks_frame["fetched_at_utc"] = fetch_started_at_utc
            benchmark_summary = _summarize_frame(benchmarks_frame, "date")
            _log_stage_summary(
                logger,
                fetch_run_id=fetch_run_id,
                stage_name=stage_name,
                provider_name="alphavantage",
                summary=benchmark_summary,
            )
            logger.info(
                "fetch_stage_write_plan run_id=%s stage=%s provider=%s latest_enabled=%s snapshot_enabled=%s manifest_enabled=%s base_dir=%s",
                fetch_run_id,
                stage_name,
                "alphavantage",
                config.acquisition.write_latest_files,
                config.acquisition.write_snapshot_copies,
                config.acquisition.write_dataset_manifests,
                config.outputs.benchmarks.base_dir,
            )
            if benchmark_summary["row_count"] == 0:
                logger.warning(
                    "fetch_stage_write_skipped_empty run_id=%s stage=%s provider=%s base_dir=%s",
                    fetch_run_id,
                    stage_name,
                    "alphavantage",
                    config.outputs.benchmarks.base_dir,
                )
            benchmarks_manifest = build_dataset_manifest(
                dataset_name=stage_name,
                provider="alphavantage",
                endpoint=config.alphavantage.base_url,
                function=config.alphavantage.monthly_adjusted_function,
                requested_symbols=requested_symbols,
                completed_symbols=benchmark_result.completed_symbols,
                failed_symbols=benchmark_result.failed_symbols,
                throttle_detected=benchmark_result.throttle_detected,
                partial_failure=bool(benchmark_result.failed_symbols),
                fetch_started_at_utc=benchmarks_started,
                fetch_completed_at_utc=utc_now().isoformat(),
                output_files=[],
                row_count=benchmark_summary["row_count"],
                min_date=benchmark_summary["min_date"],
                max_date=benchmark_summary["max_date"],
                notes=benchmark_result.notes,
                extra_metadata=_build_dataset_extra_metadata(
                    fetch_run_id=fetch_run_id,
                    stage_elapsed_seconds=time.perf_counter() - stage_started_perf,
                    config=config,
                    requested_symbols=requested_symbols,
                    completed_symbols=benchmark_result.completed_symbols,
                    failed_symbols=benchmark_result.failed_symbols,
                ),
            )
            benchmarks_written = _write_dataset_outputs(
                frame=benchmarks_frame,
                output_config=config.outputs.benchmarks,
                config=config,
                timestamp_token=timestamp_token,
            )
            benchmarks_manifest["output_files"] = benchmarks_written
            _log_written_paths(
                logger,
                fetch_run_id=fetch_run_id,
                stage_name=stage_name,
                paths=benchmarks_written,
            )
            if config.acquisition.write_dataset_manifests:
                manifest_path = _resolve_manifest_path(config.outputs.benchmarks, timestamp_token)
                if manifest_path is not None:
                    write_dataset_manifest(benchmarks_manifest, manifest_path)
                    benchmarks_manifest["output_files"].append(str(manifest_path))
                    _log_written_paths(
                        logger,
                        fetch_run_id=fetch_run_id,
                        stage_name=stage_name,
                        paths=[str(manifest_path)],
                    )
            dataset_manifests.append(benchmarks_manifest)
            all_written_paths.extend(benchmarks_manifest["output_files"])
            _log_stage_end(
                logger,
                fetch_run_id=fetch_run_id,
                stage_name=stage_name,
                provider_name="alphavantage",
                manifest=benchmarks_manifest,
                elapsed_seconds=time.perf_counter() - stage_started_perf,
            )

    if config.toggles.sec_companyfacts:
        stage_name = "fundamentals_sec_companyfacts"
        requested_symbols = list(config.project.universe.all_tickers)
        stage_started_perf = time.perf_counter()
        _log_stage_start(
            logger,
            fetch_run_id=fetch_run_id,
            stage_name=stage_name,
            provider_name="sec",
            symbols=requested_symbols,
        )
        sec_started = utc_now().isoformat()
        user_agent = resolve_sec_user_agent(provider=config.sec, environment=os.environ)
        sec_result = fetch_sec_companyfacts(
            tickers=requested_symbols,
            provider=config.sec,
            user_agent=user_agent,
            metadata=overview_frame if not overview_frame.empty else None,
            logger=logger,
            dataset_name=stage_name,
            fetch_run_id=fetch_run_id,
        )
        fundamentals_frame = sec_result.mapped_fundamentals.copy()
        if not fundamentals_frame.empty:
            fundamentals_frame["fetched_at_utc"] = fetch_started_at_utc
        fundamentals_summary = _summarize_frame(fundamentals_frame, "report_date")
        _log_stage_summary(
            logger,
            fetch_run_id=fetch_run_id,
            stage_name=stage_name,
            provider_name="sec",
            summary=fundamentals_summary,
        )
        logger.info(
            "fetch_stage_write_plan run_id=%s stage=%s provider=%s latest_enabled=%s snapshot_enabled=%s manifest_enabled=%s base_dir=%s raw_payload_snapshot_base_dir=%s raw_payload_count=%s",
            fetch_run_id,
            stage_name,
            "sec",
            config.acquisition.write_latest_files,
            config.acquisition.write_snapshot_copies,
            config.acquisition.write_dataset_manifests,
            config.outputs.fundamentals.base_dir,
            config.outputs.sec_companyfacts_raw.base_dir,
            len(sec_result.raw_payloads),
        )
        fundamentals_manifest = build_dataset_manifest(
            dataset_name=stage_name,
            provider="sec",
            endpoint=config.sec.company_facts_base_url,
            function="companyfacts",
            requested_symbols=requested_symbols,
            completed_symbols=sec_result.completed_symbols,
            failed_symbols=sec_result.failed_symbols,
            throttle_detected=False,
            partial_failure=bool(sec_result.failed_symbols),
            fetch_started_at_utc=sec_started,
            fetch_completed_at_utc=utc_now().isoformat(),
            output_files=[],
            row_count=fundamentals_summary["row_count"],
            min_date=fundamentals_summary["min_date"],
            max_date=fundamentals_summary["max_date"],
            notes=sec_result.notes
            + [
                "The first SEC mapping is intentionally conservative. Sector and industry "
                "may come from Alpha Vantage overview snapshots, while many canonical "
                "valuation fields remain unmapped rather than imputed."
            ],
            extra_metadata=_build_dataset_extra_metadata(
                fetch_run_id=fetch_run_id,
                stage_elapsed_seconds=time.perf_counter() - stage_started_perf,
                config=config,
                requested_symbols=requested_symbols,
                completed_symbols=sec_result.completed_symbols,
                failed_symbols=sec_result.failed_symbols,
            ),
        )
        fundamentals_written = _write_dataset_outputs(
            frame=fundamentals_frame,
            output_config=config.outputs.fundamentals,
            config=config,
            timestamp_token=timestamp_token,
        )
        _log_written_paths(
            logger,
            fetch_run_id=fetch_run_id,
            stage_name=stage_name,
            paths=fundamentals_written,
        )
        raw_payload_written = _write_raw_payload_snapshots(
            raw_payloads=sec_result.raw_payloads,
            output_config=config.outputs.sec_companyfacts_raw,
            config=config,
            timestamp_token=timestamp_token,
        )
        _log_written_paths(
            logger,
            fetch_run_id=fetch_run_id,
            stage_name=stage_name,
            paths=raw_payload_written,
        )
        fundamentals_manifest["output_files"] = fundamentals_written + raw_payload_written
        if config.acquisition.write_dataset_manifests:
            manifest_path = _resolve_manifest_path(config.outputs.fundamentals, timestamp_token)
            if manifest_path is not None:
                write_dataset_manifest(fundamentals_manifest, manifest_path)
                fundamentals_manifest["output_files"].append(str(manifest_path))
                _log_written_paths(
                    logger,
                    fetch_run_id=fetch_run_id,
                    stage_name=stage_name,
                    paths=[str(manifest_path)],
                )
            raw_manifest_path = _resolve_manifest_path(
                config.outputs.sec_companyfacts_raw, timestamp_token
            )
            if raw_manifest_path is not None:
                write_dataset_manifest(fundamentals_manifest, raw_manifest_path)
                fundamentals_manifest["output_files"].append(str(raw_manifest_path))
                _log_written_paths(
                    logger,
                    fetch_run_id=fetch_run_id,
                    stage_name=stage_name,
                    paths=[str(raw_manifest_path)],
                )
        dataset_manifests.append(fundamentals_manifest)
        all_written_paths.extend(fundamentals_manifest["output_files"])
        _log_stage_end(
            logger,
            fetch_run_id=fetch_run_id,
            stage_name=stage_name,
            provider_name="sec",
            manifest=fundamentals_manifest,
            elapsed_seconds=time.perf_counter() - stage_started_perf,
        )

    fetch_completed = utc_now()
    total_elapsed_seconds = time.perf_counter() - run_started_perf
    run_manifest = _build_run_manifest(
        config=config,
        provider_name=provider_name,
        fetch_run_id=fetch_run_id,
        fetch_started_at_utc=fetch_started_at_utc,
        fetch_completed_at_utc=fetch_completed.isoformat(),
        dataset_manifests=dataset_manifests,
        environment_presence=environment_presence,
    )
    run_manifest_path = (
        config.outputs.run_manifest.base_dir
        / config.outputs.run_manifest.filename_template.format(timestamp=timestamp_token)
    )
    write_dataset_manifest(run_manifest, run_manifest_path)
    all_written_paths.append(str(run_manifest_path))
    _log_written_paths(
        logger,
        fetch_run_id=fetch_run_id,
        stage_name="fetch_run",
        paths=[str(run_manifest_path)],
    )

    symbol_outcomes = _aggregate_symbol_outcomes(dataset_manifests)
    logger.info(
        "fetch_run_complete run_id=%s completed_symbols=%s failed_symbols=%s throttle_detected=%s partial_failure=%s total_elapsed_seconds=%.3f written_file_count=%s",
        fetch_run_id,
        symbol_outcomes["completed_symbols"],
        symbol_outcomes["failed_symbols"],
        run_manifest["throttle_detected"],
        run_manifest["partial_failure"],
        total_elapsed_seconds,
        len(all_written_paths),
    )
    print(f"Remote raw-data fetch completed. run_id={fetch_run_id}", flush=True)
    for path in all_written_paths:
        print(path, flush=True)

    if not dataset_manifests:
        logger.warning(
            "fetch_run_no_datasets_enabled run_id=%s provider_bundle=%s",
            fetch_run_id,
            provider_name,
        )
        return 1
    if any(
        manifest["partial_failure"] and not manifest["completed_symbols"]
        for manifest in dataset_manifests
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
