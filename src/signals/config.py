"""Config loading for deterministic signal generation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

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
        raise ValueError(f"Expected a list, received {type(values)!r}")
    return tuple(str(value) for value in values)


@dataclass(frozen=True)
class SignalStrategyConfig:
    """Strategy-level settings for deterministic composite signals."""

    name: str
    method: str
    minimum_non_missing_features: int
    selection_top_n: int
    score_missing_policy: str


@dataclass(frozen=True)
class SignalFeatureConfig:
    """Feature direction settings used by the cross-sectional rank model."""

    higher_is_better: tuple[str, ...]
    lower_is_better: tuple[str, ...]

    @property
    def all_features(self) -> tuple[str, ...]:
        """Return the ordered union of configured features."""
        return self.higher_is_better + self.lower_is_better


@dataclass(frozen=True)
class SignalTieBreaker:
    """Single deterministic tie-break rule for rank ordering."""

    column: str
    ascending: bool


@dataclass(frozen=True)
class SignalLoggingConfig:
    """Logging settings for the signal stage."""

    level: str
    log_to_file: bool
    log_dir: Path
    message_format: str


@dataclass(frozen=True)
class SignalPipelineConfig:
    """Resolved config bundle for deterministic signal generation."""

    root_dir: Path
    project: ProjectConfig
    strategy: SignalStrategyConfig
    features: SignalFeatureConfig
    weights: dict[str, float]
    tie_breakers: tuple[SignalTieBreaker, ...]
    logging: SignalLoggingConfig
    config_files: dict[str, Path]

    @property
    def outputs(self):  # noqa: ANN201
        """Expose shared artifact paths from the project config."""
        return self.project.outputs


def load_signal_pipeline_config(root_dir: Path | None = None) -> SignalPipelineConfig:
    """Load the deterministic signal-generation config bundle."""
    resolved_root = root_dir or repo_root()
    project = load_project_config(resolved_root)

    signals_path = resolved_root / "config" / "signals.yaml"
    logging_path = resolved_root / "config" / "logging.yaml"

    signals_raw = _load_yaml_mapping(signals_path)
    logging_raw = _load_yaml_mapping(logging_path)

    strategy_raw = signals_raw["strategy"]
    features_raw = signals_raw["features"]
    weights_raw = signals_raw["weights"]
    tie_breakers_raw = signals_raw["tie_breakers"]
    logging_section = logging_raw["logging"]

    weights = {str(key): float(value) for key, value in weights_raw.items()}

    config = SignalPipelineConfig(
        root_dir=resolved_root,
        project=project,
        strategy=SignalStrategyConfig(
            name=str(strategy_raw["name"]),
            method=str(strategy_raw["method"]),
            minimum_non_missing_features=int(strategy_raw["minimum_non_missing_features"]),
            selection_top_n=int(strategy_raw["selection_top_n"]),
            score_missing_policy=str(strategy_raw["score_missing_policy"]),
        ),
        features=SignalFeatureConfig(
            higher_is_better=_as_tuple(features_raw["higher_is_better"]),
            lower_is_better=_as_tuple(features_raw["lower_is_better"]),
        ),
        weights=weights,
        tie_breakers=tuple(
            SignalTieBreaker(column=str(item["column"]), ascending=bool(item["ascending"]))
            for item in tie_breakers_raw
        ),
        logging=SignalLoggingConfig(
            level=str(logging_section["level"]).upper(),
            log_to_file=bool(logging_section["log_to_file"]),
            log_dir=resolved_root / Path(str(logging_section["log_dir"])),
            message_format=str(logging_section["format"]),
        ),
        config_files={
            "signals": signals_path,
            "logging": logging_path,
            "paths": resolved_root / "config" / "paths.yaml",
            "features": resolved_root / "config" / "features.yaml",
        },
    )

    missing_weight_features = [
        feature_name for feature_name in config.features.all_features if feature_name not in config.weights
    ]
    if missing_weight_features:
        raise ValueError(
            "Every configured signal feature must have a configured weight. "
            f"Missing weights for: {missing_weight_features}"
        )

    return config


def configure_signal_logging(config: SignalPipelineConfig) -> None:
    """Configure process logging for the signal-generation CLI."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if config.logging.log_to_file:
        config.logging.log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(config.logging.log_dir / "signal_pipeline.log"))

    logging.basicConfig(
        level=getattr(logging, config.logging.level, logging.INFO),
        format=config.logging.message_format,
        handlers=handlers,
        force=True,
    )
