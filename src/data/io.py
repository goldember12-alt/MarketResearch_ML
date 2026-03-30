"""I/O helpers for raw-data ingestion and artifact persistence."""

from __future__ import annotations

import json
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
    )


def read_tabular_files(
    directory: Path,
    patterns: tuple[str, ...],
    *,
    execution: ExecutionModeConfig,
) -> pd.DataFrame:
    """Read and concatenate local CSV or Parquet inputs from a raw-data directory."""
    manifest = build_raw_file_selection_manifest(directory, patterns, execution=execution)
    frames: list[pd.DataFrame] = []
    for path_string in manifest.selected_files:
        path = Path(path_string)
        if path.suffix.lower() == ".csv":
            frame = pd.read_csv(path, low_memory=False)
        elif path.suffix.lower() == ".parquet":
            frame = pd.read_parquet(path)
        else:
            continue
        frame["source_file"] = path.name
        frames.append(frame)

    if not frames:
        raise FileNotFoundError(f"No supported raw-data files found in {directory}.")
    combined = pd.concat(frames, ignore_index=True)
    combined.attrs["raw_file_selection_manifest"] = asdict(manifest)
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
