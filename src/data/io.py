"""I/O helpers for raw-data ingestion and artifact persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def ensure_parent_directory(path: Path) -> None:
    """Create the parent directory for a file path if it does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)


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


def read_tabular_files(directory: Path, patterns: tuple[str, ...]) -> pd.DataFrame:
    """Read and concatenate local CSV or Parquet inputs from a raw-data directory."""
    frames: list[pd.DataFrame] = []
    for path in discover_input_files(directory, patterns):
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
    return pd.concat(frames, ignore_index=True)


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
