"""CLI entrypoint for upstream Alpha Vantage + SEC remote raw-data acquisition."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
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


def _resolve_manifest_path(output_config: DatasetOutputConfig, timestamp_token: str) -> Path | None:
    """Resolve the manifest path for one dataset without writing data files yet."""
    return resolve_dataset_output_targets(
        base_dir=output_config.base_dir,
        latest_filename=output_config.latest_filename,
        snapshot_subdir=output_config.snapshot_subdir,
        snapshot_filename_template=output_config.snapshot_filename_template,
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


def _build_run_manifest(
    *,
    config: RemoteRawFetchConfig,
    provider_name: str,
    fetch_started_at_utc: str,
    fetch_completed_at_utc: str,
    dataset_manifests: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the top-level remote fetch run manifest."""
    return {
        "provider_bundle": provider_name,
        "requested_execution_mode": config.project.execution.mode_name,
        "execution_description": config.project.execution.description,
        "fetch_started_at_utc": fetch_started_at_utc,
        "fetch_completed_at_utc": fetch_completed_at_utc,
        "requested_universe_symbols": list(config.project.universe.all_tickers),
        "requested_benchmark_symbols": list(config.project.universe.explicit_benchmarks),
        "dataset_manifests": dataset_manifests,
        "partial_failure": any(manifest["partial_failure"] for manifest in dataset_manifests),
        "throttle_detected": any(manifest["throttle_detected"] for manifest in dataset_manifests),
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
    dataset_manifests: list[dict[str, Any]] = []
    all_written_paths: list[str] = []

    logger.info("Starting remote raw-data fetch for provider bundle %s", provider_name)

    overview_frame = pd.DataFrame()
    if config.toggles.overview_metadata:
        api_key = _require_alphavantage_api_key(config)
        overview_started = utc_now().isoformat()
        overview_result = fetch_overview_metadata(
            symbols=list(config.project.universe.all_tickers),
            provider=config.alphavantage,
            api_key=api_key,
        )
        overview_frame = overview_result.frame.copy()
        if not overview_frame.empty:
            overview_frame["fetched_at_utc"] = fetch_started_at_utc
        min_date, max_date = _frame_date_span(overview_frame, "latest_quarter")
        overview_notes = overview_result.notes + [
            "Alpha Vantage overview metadata are point-in-time-unsafe snapshots and are only "
            "used here for classification enrichment such as sector and industry."
        ]
        overview_manifest = build_dataset_manifest(
            dataset_name="overview_metadata",
            provider="alphavantage",
            endpoint=config.alphavantage.base_url,
            function=config.alphavantage.overview_function,
            requested_symbols=list(config.project.universe.all_tickers),
            completed_symbols=overview_result.completed_symbols,
            failed_symbols=overview_result.failed_symbols,
            throttle_detected=overview_result.throttle_detected,
            partial_failure=bool(overview_result.failed_symbols),
            fetch_started_at_utc=overview_started,
            fetch_completed_at_utc=utc_now().isoformat(),
            output_files=[],
            row_count=int(len(overview_frame)),
            min_date=min_date,
            max_date=max_date,
            notes=overview_notes,
        )
        overview_written = _write_dataset_outputs(
            frame=overview_frame,
            output_config=config.outputs.overview,
            config=config,
            timestamp_token=timestamp_token,
        )
        overview_manifest["output_files"] = overview_written
        if config.acquisition.write_dataset_manifests:
            manifest_path = _resolve_manifest_path(config.outputs.overview, timestamp_token)
            if manifest_path is not None:
                write_dataset_manifest(overview_manifest, manifest_path)
                overview_manifest["output_files"].append(str(manifest_path))
        dataset_manifests.append(overview_manifest)
        all_written_paths.extend(overview_manifest["output_files"])

    if config.toggles.market_prices:
        api_key = _require_alphavantage_api_key(config)
        market_started = utc_now().isoformat()
        market_result = fetch_monthly_adjusted_series(
            symbols=list(config.project.universe.all_tickers),
            identifier_column="ticker",
            provider=config.alphavantage,
            api_key=api_key,
        )
        market_frame = market_result.frame.copy()
        if not market_frame.empty:
            market_frame["fetched_at_utc"] = fetch_started_at_utc
        min_date, max_date = _frame_date_span(market_frame, "date")
        market_manifest = build_dataset_manifest(
            dataset_name="market_prices",
            provider="alphavantage",
            endpoint=config.alphavantage.base_url,
            function=config.alphavantage.monthly_adjusted_function,
            requested_symbols=list(config.project.universe.all_tickers),
            completed_symbols=market_result.completed_symbols,
            failed_symbols=market_result.failed_symbols,
            throttle_detected=market_result.throttle_detected,
            partial_failure=bool(market_result.failed_symbols),
            fetch_started_at_utc=market_started,
            fetch_completed_at_utc=utc_now().isoformat(),
            output_files=[],
            row_count=int(len(market_frame)),
            min_date=min_date,
            max_date=max_date,
            notes=market_result.notes
            + [
                "Monthly adjusted Alpha Vantage history is used because it aligns to the "
                "repo's monthly decision frequency and is more feasible on the free tier "
                "than full-history daily adjusted endpoints."
            ],
        )
        market_written = _write_dataset_outputs(
            frame=market_frame,
            output_config=config.outputs.market,
            config=config,
            timestamp_token=timestamp_token,
        )
        market_manifest["output_files"] = market_written
        if config.acquisition.write_dataset_manifests:
            manifest_path = _resolve_manifest_path(config.outputs.market, timestamp_token)
            if manifest_path is not None:
                write_dataset_manifest(market_manifest, manifest_path)
                market_manifest["output_files"].append(str(manifest_path))
        dataset_manifests.append(market_manifest)
        all_written_paths.extend(market_manifest["output_files"])

    if config.toggles.benchmark_prices:
        api_key = _require_alphavantage_api_key(config)
        benchmarks_started = utc_now().isoformat()
        benchmark_result = fetch_monthly_adjusted_series(
            symbols=list(config.project.universe.explicit_benchmarks),
            identifier_column="benchmark_ticker",
            provider=config.alphavantage,
            api_key=api_key,
        )
        benchmarks_frame = benchmark_result.frame.copy()
        if not benchmarks_frame.empty:
            benchmarks_frame["fetched_at_utc"] = fetch_started_at_utc
        min_date, max_date = _frame_date_span(benchmarks_frame, "date")
        benchmarks_manifest = build_dataset_manifest(
            dataset_name="benchmark_prices",
            provider="alphavantage",
            endpoint=config.alphavantage.base_url,
            function=config.alphavantage.monthly_adjusted_function,
            requested_symbols=list(config.project.universe.explicit_benchmarks),
            completed_symbols=benchmark_result.completed_symbols,
            failed_symbols=benchmark_result.failed_symbols,
            throttle_detected=benchmark_result.throttle_detected,
            partial_failure=bool(benchmark_result.failed_symbols),
            fetch_started_at_utc=benchmarks_started,
            fetch_completed_at_utc=utc_now().isoformat(),
            output_files=[],
            row_count=int(len(benchmarks_frame)),
            min_date=min_date,
            max_date=max_date,
            notes=benchmark_result.notes,
        )
        benchmarks_written = _write_dataset_outputs(
            frame=benchmarks_frame,
            output_config=config.outputs.benchmarks,
            config=config,
            timestamp_token=timestamp_token,
        )
        benchmarks_manifest["output_files"] = benchmarks_written
        if config.acquisition.write_dataset_manifests:
            manifest_path = _resolve_manifest_path(config.outputs.benchmarks, timestamp_token)
            if manifest_path is not None:
                write_dataset_manifest(benchmarks_manifest, manifest_path)
                benchmarks_manifest["output_files"].append(str(manifest_path))
        dataset_manifests.append(benchmarks_manifest)
        all_written_paths.extend(benchmarks_manifest["output_files"])

    if config.toggles.sec_companyfacts:
        sec_started = utc_now().isoformat()
        user_agent = resolve_sec_user_agent(provider=config.sec, environment=os.environ)
        sec_result = fetch_sec_companyfacts(
            tickers=list(config.project.universe.all_tickers),
            provider=config.sec,
            user_agent=user_agent,
            metadata=overview_frame if not overview_frame.empty else None,
        )
        fundamentals_frame = sec_result.mapped_fundamentals.copy()
        if not fundamentals_frame.empty:
            fundamentals_frame["fetched_at_utc"] = fetch_started_at_utc
        min_date, max_date = _frame_date_span(fundamentals_frame, "report_date")
        fundamentals_manifest = build_dataset_manifest(
            dataset_name="fundamentals_sec_companyfacts",
            provider="sec",
            endpoint=config.sec.company_facts_base_url,
            function="companyfacts",
            requested_symbols=list(config.project.universe.all_tickers),
            completed_symbols=sec_result.completed_symbols,
            failed_symbols=sec_result.failed_symbols,
            throttle_detected=False,
            partial_failure=bool(sec_result.failed_symbols),
            fetch_started_at_utc=sec_started,
            fetch_completed_at_utc=utc_now().isoformat(),
            output_files=[],
            row_count=int(len(fundamentals_frame)),
            min_date=min_date,
            max_date=max_date,
            notes=sec_result.notes
            + [
                "The first SEC mapping is intentionally conservative. Sector and industry "
                "may come from Alpha Vantage overview snapshots, while many canonical "
                "valuation fields remain unmapped rather than imputed."
            ],
        )
        fundamentals_written = _write_dataset_outputs(
            frame=fundamentals_frame,
            output_config=config.outputs.fundamentals,
            config=config,
            timestamp_token=timestamp_token,
        )
        raw_payload_written = _write_raw_payload_snapshots(
            raw_payloads=sec_result.raw_payloads,
            output_config=config.outputs.sec_companyfacts_raw,
            config=config,
            timestamp_token=timestamp_token,
        )
        fundamentals_manifest["output_files"] = fundamentals_written + raw_payload_written
        if config.acquisition.write_dataset_manifests:
            manifest_path = _resolve_manifest_path(config.outputs.fundamentals, timestamp_token)
            if manifest_path is not None:
                write_dataset_manifest(fundamentals_manifest, manifest_path)
            raw_manifest_path = _resolve_manifest_path(
                config.outputs.sec_companyfacts_raw, timestamp_token
            )
            if raw_manifest_path is not None:
                write_dataset_manifest(fundamentals_manifest, raw_manifest_path)
                fundamentals_manifest["output_files"].append(str(raw_manifest_path))
        dataset_manifests.append(fundamentals_manifest)
        all_written_paths.extend(fundamentals_manifest["output_files"])

    fetch_completed = utc_now()
    run_manifest = _build_run_manifest(
        config=config,
        provider_name=provider_name,
        fetch_started_at_utc=fetch_started_at_utc,
        fetch_completed_at_utc=fetch_completed.isoformat(),
        dataset_manifests=dataset_manifests,
    )
    run_manifest_path = (
        config.outputs.run_manifest.base_dir
        / config.outputs.run_manifest.filename_template.format(timestamp=timestamp_token)
    )
    write_dataset_manifest(run_manifest, run_manifest_path)
    all_written_paths.append(str(run_manifest_path))

    logger.info("Remote raw-data fetch completed with %s written files.", len(all_written_paths))
    print("Remote raw-data fetch completed.")
    for path in all_written_paths:
        print(path)

    if not dataset_manifests:
        logger.warning("No dataset toggles were enabled; nothing was fetched.")
        return 1
    if any(
        manifest["partial_failure"] and not manifest["completed_symbols"]
        for manifest in dataset_manifests
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
