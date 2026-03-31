"""Helpers for immutable remote raw-data snapshot writing and manifests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.io import ensure_parent_directory, write_json, write_parquet


@dataclass(frozen=True)
class DatasetOutputTargets:
    """Resolved write targets for one fetched dataset."""

    latest_path: Path | None
    snapshot_path: Path | None
    manifest_path: Path | None


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(tz=UTC)


def format_utc_timestamp(timestamp: datetime, fmt: str) -> str:
    """Format a UTC timestamp deterministically for file naming."""
    return timestamp.astimezone(UTC).strftime(fmt)


def resolve_dataset_output_targets(
    *,
    base_dir: Path,
    latest_filename: str | None,
    snapshot_subdir: Path | None,
    snapshot_filename_template: str | None,
    manifest_subdir: Path | None,
    latest_manifest_filename: str | None,
    timestamp_token: str,
) -> DatasetOutputTargets:
    """Build write targets for latest, snapshot, and manifest files."""
    latest_path = None if latest_filename is None else base_dir / latest_filename
    snapshot_path = None
    if snapshot_subdir is not None and snapshot_filename_template is not None:
        snapshot_path = snapshot_subdir / snapshot_filename_template.format(
            timestamp=timestamp_token
        )
    manifest_path = None
    if manifest_subdir is not None and latest_manifest_filename is not None:
        manifest_path = manifest_subdir / latest_manifest_filename
    return DatasetOutputTargets(
        latest_path=latest_path,
        snapshot_path=snapshot_path,
        manifest_path=manifest_path,
    )


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame to CSV using deterministic parent directories."""
    ensure_parent_directory(path)
    frame.to_csv(path, index=False)


def write_tabular_data(frame: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame to CSV or Parquet according to the path suffix."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        _write_csv(frame, path)
        return
    if suffix == ".parquet":
        write_parquet(frame, path)
        return
    raise ValueError(f"Unsupported tabular suffix for remote output: {path}")


def write_text_payload(text: str, path: Path) -> None:
    """Write a plain-text payload with deterministic parent directories."""
    ensure_parent_directory(path)
    path.write_text(text, encoding="utf-8")


def enforce_overwrite_policy(path: Path, overwrite_policy: str) -> None:
    """Validate whether a latest-path write is allowed under the configured policy."""
    if path.exists() and overwrite_policy == "fail":
        raise FileExistsError(
            f"Remote raw-data latest file already exists and overwrite policy is 'fail': {path}"
        )


def build_dataset_manifest(
    *,
    dataset_name: str,
    provider: str,
    endpoint: str,
    function: str | None,
    requested_symbols: list[str],
    completed_symbols: list[str],
    failed_symbols: list[str],
    throttle_detected: bool,
    partial_failure: bool,
    fetch_started_at_utc: str,
    fetch_completed_at_utc: str,
    output_files: list[str],
    row_count: int | None,
    min_date: str | None,
    max_date: str | None,
    notes: list[str] | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a machine-readable manifest for one fetched dataset."""
    payload: dict[str, Any] = {
        "dataset_name": dataset_name,
        "provider": provider,
        "endpoint": endpoint,
        "function": function,
        "requested_symbols": requested_symbols,
        "completed_symbols": completed_symbols,
        "failed_symbols": failed_symbols,
        "throttle_detected": throttle_detected,
        "partial_failure": partial_failure,
        "fetch_started_at_utc": fetch_started_at_utc,
        "fetch_completed_at_utc": fetch_completed_at_utc,
        "output_files": output_files,
        "row_count": row_count,
        "min_date": min_date,
        "max_date": max_date,
        "notes": notes or [],
    }
    if extra_metadata:
        payload["extra_metadata"] = extra_metadata
    return payload


def write_dataset_manifest(manifest: dict[str, Any], path: Path) -> None:
    """Persist one dataset manifest as JSON."""
    write_json(manifest, path)
