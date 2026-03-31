"""Config loading for the feature-generation pipeline."""

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


@dataclass(frozen=True)
class FeatureGroupsConfig:
    """Feature-group toggles for the initial leakage-safe feature set."""

    price_based: bool
    valuation_based: bool
    quality_profitability: bool
    growth: bool
    balance_sheet: bool
    revisions: bool
    market_cap: bool


@dataclass(frozen=True)
class FeatureLookbacksConfig:
    """Configured rolling windows for time-series features."""

    momentum_3m: int
    momentum_6m: int
    momentum_12m: int
    volatility_12m: int
    beta_12m: int
    drawdown_12m: int


@dataclass(frozen=True)
class FeatureLagConfig:
    """Lag rules that enforce feature availability before the decision date."""

    default_periods: int
    fundamentals_periods: int


@dataclass(frozen=True)
class FeatureMissingnessConfig:
    """Missingness-handling settings for the feature stage."""

    numeric_fill: str
    categorical_fill: str
    drop_threshold: float


@dataclass(frozen=True)
class FeatureBenchmarkConfig:
    """Benchmark settings used for feature calculations."""

    beta_benchmark: str


@dataclass(frozen=True)
class FeatureLoggingConfig:
    """Logging settings for the feature stage."""

    level: str
    log_to_file: bool
    log_dir: Path
    message_format: str


@dataclass(frozen=True)
class FeaturePipelineConfig:
    """Resolved feature-stage configuration bundle."""

    root_dir: Path
    project: ProjectConfig
    groups: FeatureGroupsConfig
    lookbacks: FeatureLookbacksConfig
    lags: FeatureLagConfig
    missingness: FeatureMissingnessConfig
    benchmarks: FeatureBenchmarkConfig
    logging: FeatureLoggingConfig
    config_files: dict[str, Path]

    @property
    def outputs(self):  # noqa: ANN201
        """Expose shared artifact paths from the project-level config."""
        return self.project.outputs


def load_feature_pipeline_config(
    root_dir: Path | None = None,
    execution_mode: str | None = None,
) -> FeaturePipelineConfig:
    """Load the feature-stage contract from repo config files."""
    resolved_root = root_dir or repo_root()
    project = load_project_config(resolved_root, execution_mode=execution_mode)
    features_path = resolved_root / "config" / "features.yaml"
    logging_path = resolved_root / "config" / "logging.yaml"
    features_raw = _load_yaml_mapping(features_path)
    logging_raw = _load_yaml_mapping(logging_path)

    groups_raw = features_raw["feature_groups"]
    lookbacks_raw = features_raw["lookbacks"]
    lags_raw = features_raw["lags"]
    missingness_raw = features_raw["missingness"]
    benchmark_raw = features_raw["benchmarks"]

    return FeaturePipelineConfig(
        root_dir=resolved_root,
        project=project,
        groups=FeatureGroupsConfig(
            price_based=bool(groups_raw["price_based"]),
            valuation_based=bool(groups_raw["valuation_based"]),
            quality_profitability=bool(groups_raw["quality_profitability"]),
            growth=bool(groups_raw["growth"]),
            balance_sheet=bool(groups_raw["balance_sheet"]),
            revisions=bool(groups_raw["revisions"]),
            market_cap=bool(groups_raw["market_cap"]),
        ),
        lookbacks=FeatureLookbacksConfig(
            momentum_3m=int(lookbacks_raw["momentum_3m"]),
            momentum_6m=int(lookbacks_raw["momentum_6m"]),
            momentum_12m=int(lookbacks_raw["momentum_12m"]),
            volatility_12m=int(lookbacks_raw["volatility_12m"]),
            beta_12m=int(lookbacks_raw["beta_12m"]),
            drawdown_12m=int(lookbacks_raw["drawdown_12m"]),
        ),
        lags=FeatureLagConfig(
            default_periods=int(lags_raw["default_periods"]),
            fundamentals_periods=int(lags_raw["fundamentals_periods"]),
        ),
        missingness=FeatureMissingnessConfig(
            numeric_fill=str(missingness_raw["numeric_fill"]),
            categorical_fill=str(missingness_raw["categorical_fill"]),
            drop_threshold=float(missingness_raw["drop_threshold"]),
        ),
        benchmarks=FeatureBenchmarkConfig(
            beta_benchmark=str(benchmark_raw["beta_benchmark"]).upper()
        ),
        logging=FeatureLoggingConfig(
            level=str(logging_raw["logging"]["level"]).upper(),
            log_to_file=bool(logging_raw["logging"]["log_to_file"]),
            log_dir=resolved_root / Path(str(logging_raw["logging"]["log_dir"])),
            message_format=str(logging_raw["logging"]["format"]),
        ),
        config_files={
            "features": features_path,
            "execution": resolved_root / "config" / "execution.yaml",
            "evaluation": resolved_root / "config" / "evaluation.yaml",
            "logging": logging_path,
            "paths": resolved_root / "config" / "paths.yaml",
            "universe": resolved_root / "config" / "universe.yaml",
        },
    )


def configure_feature_logging(config: FeaturePipelineConfig) -> None:
    """Configure process logging for the feature-generation CLI."""
    handlers: list[logging.Handler] = [build_stdout_stream_handler()]
    if config.logging.log_to_file:
        config.logging.log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(config.logging.log_dir / "feature_pipeline.log"))

    logging.basicConfig(
        level=getattr(logging, config.logging.level, logging.INFO),
        format=config.logging.message_format,
        handlers=handlers,
        force=True,
    )
