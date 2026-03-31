"""Config loading for the data-ingestion and panel-assembly pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.utils.logging_utils import build_stdout_stream_handler
from src.utils.config import ProjectConfig, load_project_config, repo_root


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Read a YAML file and ensure it contains a mapping."""
    parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return parsed


def _as_tuple(values: Any) -> tuple[str, ...]:
    """Normalize a YAML list-like value to an immutable tuple."""
    if values is None:
        return ()
    if not isinstance(values, list):
        raise ValueError(f"Expected list-like values, received {type(values)!r}")
    return tuple(str(value) for value in values)


@dataclass(frozen=True)
class RawDataPaths:
    """Raw-data locations for the local-file-first ingestion contract."""

    root_dir: Path
    market_dir: Path
    fundamentals_dir: Path
    benchmarks_dir: Path
    file_patterns: tuple[str, ...]


@dataclass(frozen=True)
class DataProcessingConfig:
    """Data-stage processing rules and temporal alignment assumptions."""

    frequency: str
    month_end_convention: str
    adjusted_close_priority: tuple[str, ...]
    ticker_column_priority: tuple[str, ...]
    date_column_priority: tuple[str, ...]
    fundamentals_date_column_priority: tuple[str, ...]
    monthly_return_method: str
    benchmark_return_method: str
    primary_benchmark: str
    equal_weight_benchmark_id: str
    equal_weight_start_value: float
    fundamentals_effective_lag_months: int
    fundamentals_max_staleness_months: int
    strict_universe_filter: bool


@dataclass(frozen=True)
class LoggingConfig:
    """Logging settings for runnable CLI entrypoints."""

    level: str
    log_to_file: bool
    log_dir: Path
    message_format: str


@dataclass(frozen=True)
class DataPipelineConfig:
    """Resolved config bundle for the ingestion and panel-assembly stages."""

    root_dir: Path
    project: ProjectConfig
    raw: RawDataPaths
    processing: DataProcessingConfig
    logging: LoggingConfig
    config_files: dict[str, Path]

    @property
    def outputs(self):  # noqa: ANN201
        """Expose shared artifact paths from the project-level config."""
        return self.project.outputs

    @property
    def universe_tickers(self) -> tuple[str, ...]:
        """Return the configured research-universe tickers."""
        return self.project.universe.all_tickers

    @property
    def explicit_benchmarks(self) -> tuple[str, ...]:
        """Return explicit benchmark tickers configured for ingestion."""
        return self.project.universe.explicit_benchmarks


def load_data_pipeline_config(
    root_dir: Path | None = None,
    execution_mode: str | None = None,
) -> DataPipelineConfig:
    """Load the data-stage contract from repo config files."""
    resolved_root = root_dir or repo_root()
    project = load_project_config(resolved_root, execution_mode=execution_mode)

    data_path = resolved_root / "config" / "data.yaml"
    logging_path = resolved_root / "config" / "logging.yaml"

    data_raw = _load_yaml_mapping(data_path)
    logging_raw = _load_yaml_mapping(logging_path)

    raw_data = data_raw["raw_data"]
    processing_raw = data_raw["processing"]
    logging_section = logging_raw["logging"]

    raw = RawDataPaths(
        root_dir=resolved_root / Path(str(raw_data["root_dir"])),
        market_dir=resolved_root / Path(str(raw_data["market_dir"])),
        fundamentals_dir=resolved_root / Path(str(raw_data["fundamentals_dir"])),
        benchmarks_dir=resolved_root / Path(str(raw_data["benchmarks_dir"])),
        file_patterns=_as_tuple(raw_data["file_patterns"]),
    )

    processing = DataProcessingConfig(
        frequency=str(processing_raw["frequency"]),
        month_end_convention=str(processing_raw["month_end_convention"]),
        adjusted_close_priority=_as_tuple(processing_raw["adjusted_close_priority"]),
        ticker_column_priority=_as_tuple(processing_raw["ticker_column_priority"]),
        date_column_priority=_as_tuple(processing_raw["date_column_priority"]),
        fundamentals_date_column_priority=_as_tuple(
            processing_raw["fundamentals_date_column_priority"]
        ),
        monthly_return_method=str(processing_raw["monthly_return_method"]),
        benchmark_return_method=str(processing_raw["benchmark_return_method"]),
        primary_benchmark=str(processing_raw["primary_benchmark"]).upper(),
        equal_weight_benchmark_id=str(processing_raw["equal_weight_benchmark_id"]),
        equal_weight_start_value=float(processing_raw["equal_weight_start_value"]),
        fundamentals_effective_lag_months=int(
            processing_raw["fundamentals_effective_lag_months"]
        ),
        fundamentals_max_staleness_months=int(
            processing_raw["fundamentals_max_staleness_months"]
        ),
        strict_universe_filter=bool(processing_raw["strict_universe_filter"]),
    )

    logging_config = LoggingConfig(
        level=str(logging_section["level"]).upper(),
        log_to_file=bool(logging_section["log_to_file"]),
        log_dir=resolved_root / Path(str(logging_section["log_dir"])),
        message_format=str(logging_section["format"]),
    )

    return DataPipelineConfig(
        root_dir=resolved_root,
        project=project,
        raw=raw,
        processing=processing,
        logging=logging_config,
        config_files={
            "universe": resolved_root / "config" / "universe.yaml",
            "execution": resolved_root / "config" / "execution.yaml",
            "backtest": resolved_root / "config" / "backtest.yaml",
            "evaluation": resolved_root / "config" / "evaluation.yaml",
            "paths": resolved_root / "config" / "paths.yaml",
            "data": data_path,
            "logging": logging_path,
        },
    )


def configure_logging(config: DataPipelineConfig) -> None:
    """Configure process logging for the runnable data-stage CLIs."""
    handlers: list[logging.Handler] = [build_stdout_stream_handler()]
    if config.logging.log_to_file:
        config.logging.log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(config.logging.log_dir / "data_pipeline.log"))

    logging.basicConfig(
        level=getattr(logging, config.logging.level, logging.INFO),
        format=config.logging.message_format,
        handlers=handlers,
        force=True,
    )
