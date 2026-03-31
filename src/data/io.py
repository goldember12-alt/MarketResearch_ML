"""I/O helpers for raw-data ingestion and artifact persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.config import ExecutionModeConfig


def ensure_parent_directory(path: Path) -> None:
    """Create the parent directory for a file path if it does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class RawFileSelectionManifest:
    """Audit-friendly description of how raw input files were selected."""

    requested_execution_mode: str
    execution_description: str
    directory: str
    selected_source_kind: str
    selected_file_count: int
    selected_files: tuple[str, ...]
    available_sample_file_count: int
    available_non_sample_file_count: int
    broader_raw_files_available: bool
    used_seeded_sample_fallback: bool
    selected_file_details: tuple[dict[str, Any], ...]


def _to_utc_iso(timestamp: float) -> str:
    """Convert a filesystem timestamp to a stable UTC ISO string."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _build_file_detail(path: Path, *, sample_file_token: str) -> dict[str, Any]:
    """Describe one selected raw file using deterministic filesystem metadata."""
    stat = path.stat()
    return {
        "file_path": str(path),
        "file_name": path.name,
        "source_kind": "sample"
        if _is_sample_file(path, sample_file_token)
        else "non_sample",
        "file_size_bytes": int(stat.st_size),
        "last_modified_utc": _to_utc_iso(stat.st_mtime),
    }


def _detect_date_column_observations(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Capture simple raw date-column coverage observations for one loaded file."""
    observations: list[dict[str, Any]] = []
    for column in frame.columns:
        column_name = str(column)
        if "date" not in column_name.lower():
            continue
        parsed = pd.to_datetime(frame[column], errors="coerce")
        non_null_count = int(parsed.notna().sum())
        if non_null_count == 0:
            continue
        observations.append(
            {
                "column": column_name,
                "non_null_count": non_null_count,
                "min_date": parsed.min().date().isoformat(),
                "max_date": parsed.max().date().isoformat(),
            }
        )
    return observations


def _build_observed_file_detail(base_detail: dict[str, Any], frame: pd.DataFrame) -> dict[str, Any]:
    """Augment one selected-file detail with observed raw-frame coverage metadata."""
    observed_detail = dict(base_detail)
    observed_detail["observed_row_count"] = int(len(frame))
    observed_detail["observed_column_count"] = int(len(frame.columns))
    observed_detail["observed_columns"] = [str(column) for column in frame.columns]
    observed_detail["observed_date_columns"] = _detect_date_column_observations(frame)
    return observed_detail


def _summarize_observed_selection(
    selected_file_details: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build compact observed-coverage metadata across all selected raw files."""
    observed_total_row_count = sum(
        int(detail.get("observed_row_count", 0) or 0) for detail in selected_file_details
    )
    observed_date_columns = sorted(
        {
            str(observation["column"])
            for detail in selected_file_details
            for observation in detail.get("observed_date_columns", [])
        }
    )
    observed_min_dates = [
        observation.get("min_date")
        for detail in selected_file_details
        for observation in detail.get("observed_date_columns", [])
        if observation.get("min_date") is not None
    ]
    observed_max_dates = [
        observation.get("max_date")
        for detail in selected_file_details
        for observation in detail.get("observed_date_columns", [])
        if observation.get("max_date") is not None
    ]
    return {
        "observed_total_row_count": int(observed_total_row_count),
        "observed_date_columns": observed_date_columns,
        "observed_min_date": min(observed_min_dates) if observed_min_dates else None,
        "observed_max_date": max(observed_max_dates) if observed_max_dates else None,
    }


def discover_input_files(directory: Path, patterns: tuple[str, ...]) -> tuple[Path, ...]:
    """Discover supported local raw-data files in a directory."""
    if not directory.exists():
        raise FileNotFoundError(f"Raw-data directory does not exist: {directory}")

    files: list[Path] = []
    for pattern in patterns:
        files.extend(path for path in directory.glob(pattern) if path.is_file())

    unique_files = tuple(sorted(set(files)))
    if not unique_files:
        raise FileNotFoundError(
            f"No raw-data files found in {directory} for patterns {patterns!r}."
        )
    return unique_files


def _is_sample_file(path: Path, sample_file_token: str) -> bool:
    """Return True when a raw file name is tagged as a seeded sample input."""
    return sample_file_token.lower() in path.stem.lower()


def select_input_files(
    directory: Path,
    patterns: tuple[str, ...],
    *,
    execution: ExecutionModeConfig,
) -> tuple[Path, ...]:
    """Select raw files according to the configured execution profile."""
    available_files = discover_input_files(directory, patterns)
    sample_files = tuple(
        path for path in available_files if _is_sample_file(path, execution.sample_file_token)
    )
    non_sample_files = tuple(path for path in available_files if path not in sample_files)

    if execution.raw_file_policy == "sample_only":
        if not sample_files:
            raise FileNotFoundError(
                "Execution mode 'seeded' expects sample-tagged raw files, but none were found "
                f"in {directory}."
            )
        return sample_files

    if execution.raw_file_policy == "prefer_non_sample":
        if non_sample_files:
            return non_sample_files
        if sample_files and execution.allow_sample_fallback:
            return sample_files
        raise FileNotFoundError(
            "Execution mode 'research_scale' did not find broader local raw files and fallback "
            f"to sample files is disabled for {directory}."
        )

    raise ValueError(f"Unsupported raw_file_policy={execution.raw_file_policy!r}.")


def build_raw_file_selection_manifest(
    directory: Path,
    patterns: tuple[str, ...],
    *,
    execution: ExecutionModeConfig,
) -> RawFileSelectionManifest:
    """Build an explicit manifest for the raw files chosen under one execution mode."""
    available_files = discover_input_files(directory, patterns)
    sample_files = tuple(
        path for path in available_files if _is_sample_file(path, execution.sample_file_token)
    )
    non_sample_files = tuple(path for path in available_files if path not in sample_files)
    selected_files = select_input_files(directory, patterns, execution=execution)
    broader_raw_files_available = bool(non_sample_files)
    used_seeded_sample_fallback = (
        execution.raw_file_policy == "prefer_non_sample"
        and not broader_raw_files_available
        and bool(sample_files)
    )
    selected_source_kind = (
        "seeded_sample"
        if all(path in sample_files for path in selected_files)
        else "broader_local_raw"
    )
    if used_seeded_sample_fallback:
        selected_source_kind = "seeded_sample_fallback"

    return RawFileSelectionManifest(
        requested_execution_mode=execution.mode_name,
        execution_description=execution.description,
        directory=str(directory),
        selected_source_kind=selected_source_kind,
        selected_file_count=len(selected_files),
        selected_files=tuple(str(path) for path in selected_files),
        available_sample_file_count=len(sample_files),
        available_non_sample_file_count=len(non_sample_files),
        broader_raw_files_available=broader_raw_files_available,
        used_seeded_sample_fallback=used_seeded_sample_fallback,
        selected_file_details=tuple(
            _build_file_detail(path, sample_file_token=execution.sample_file_token)
            for path in selected_files
        ),
    )


def read_tabular_files(
    directory: Path,
    patterns: tuple[str, ...],
    *,
    execution: ExecutionModeConfig,
) -> pd.DataFrame:
    """Read and concatenate local CSV or Parquet inputs from a raw-data directory."""
    manifest = build_raw_file_selection_manifest(directory, patterns, execution=execution)
    manifest_payload = asdict(manifest)
    frames: list[pd.DataFrame] = []
    selected_file_details: list[dict[str, Any]] = []
    for path_string, base_detail in zip(
        manifest.selected_files, manifest.selected_file_details, strict=True
    ):
        path = Path(path_string)
        if path.suffix.lower() == ".csv":
            frame = pd.read_csv(path, low_memory=False)
        elif path.suffix.lower() == ".parquet":
            frame = pd.read_parquet(path)
        else:
            continue
        selected_file_details.append(_build_observed_file_detail(base_detail, frame))
        frame["source_file"] = path.name
        frames.append(frame)

    if not frames:
        raise FileNotFoundError(f"No supported raw-data files found in {directory}.")
    combined = pd.concat(frames, ignore_index=True)
    manifest_payload["selected_file_details"] = selected_file_details
    manifest_payload.update(_summarize_observed_selection(selected_file_details))
    combined.attrs["raw_file_selection_manifest"] = manifest_payload
    return combined


def read_parquet_required(path: Path, dataset_name: str) -> pd.DataFrame:
    """Read a required parquet artifact or raise a clear error."""
    if not path.exists():
        raise FileNotFoundError(f"Required {dataset_name} artifact is missing: {path}")
    return pd.read_parquet(path)


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame to Parquet using deterministic parent directories."""
    ensure_parent_directory(path)
    df.to_parquet(path, index=False)


def write_json(payload: dict[str, Any], path: Path) -> None:
    """Write a JSON artifact with stable formatting."""
    ensure_parent_directory(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write a CSV artifact with deterministic parent directories."""
    ensure_parent_directory(path)
    df.to_csv(path, index=False)
