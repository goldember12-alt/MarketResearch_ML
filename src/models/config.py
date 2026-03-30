"""Config loading for the leakage-safe modeling baseline stage."""

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
class ModelLabelConfig:
    """Settings controlling forward-return label generation."""

    target_type: str
    horizon_months: int
    benchmark: str
    positive_threshold: float
    cross_sectional_top_n: int | None


@dataclass(frozen=True)
class ModelDatasetConfig:
    """Feature selection and row-filtering rules for the modeling dataset."""

    feature_columns: tuple[str, ...]
    minimum_non_missing_features: int


@dataclass(frozen=True)
class ModelDateWindow:
    """Configured inclusive date window for one chronological split."""

    start_date: str
    end_date: str


@dataclass(frozen=True)
class ModelFixedDateWindowsConfig:
    """Explicit train/validation/test windows for the fixed split path."""

    train: ModelDateWindow
    validation: ModelDateWindow
    test: ModelDateWindow


@dataclass(frozen=True)
class ModelWalkForwardConfig:
    """Expanding walk-forward settings for repeated out-of-sample evaluation."""

    min_train_periods: int
    validation_window_periods: int
    test_window_periods: int
    step_periods: int


@dataclass(frozen=True)
class ModelSplitConfig:
    """Chronological split settings for fixed or multi-window evaluation."""

    scheme: str
    fixed_date_windows: ModelFixedDateWindowsConfig
    walk_forward: ModelWalkForwardConfig

    @property
    def train(self) -> ModelDateWindow:
        """Backwards-compatible access to the fixed training window."""
        return self.fixed_date_windows.train

    @property
    def validation(self) -> ModelDateWindow:
        """Backwards-compatible access to the fixed validation window."""
        return self.fixed_date_windows.validation

    @property
    def test(self) -> ModelDateWindow:
        """Backwards-compatible access to the fixed test window."""
        return self.fixed_date_windows.test


@dataclass(frozen=True)
class ModelPreprocessingConfig:
    """Preprocessing rules that must be fit on training rows only."""

    numeric_imputation_strategy: str
    scale_numeric: bool


@dataclass(frozen=True)
class ModelClassificationConfig:
    """Classification threshold used to map probabilities into classes."""

    class_threshold: float


@dataclass(frozen=True)
class ModelExecutionConfig:
    """Run-selection and reproducibility settings for the modeling stage."""

    selected_model: str
    random_state: int
    append_experiment_registry: bool


@dataclass(frozen=True)
class DeterministicBaselineConfig:
    """Existing deterministic baseline context reused for model comparison."""

    enabled: bool
    score_column: str
    class_column: str


@dataclass(frozen=True)
class ModelBacktestConfig:
    """Settings for turning held-out model scores into portfolio rankings."""

    score_column: str
    prediction_splits: tuple[str, ...]


@dataclass(frozen=True)
class LogisticRegressionBaselineConfig:
    """Hyperparameters for the regularized logistic-regression baseline."""

    enabled: bool
    penalty: str
    c: float
    solver: str
    max_iter: int


@dataclass(frozen=True)
class RandomForestBaselineConfig:
    """Hyperparameters for the tree-based random-forest baseline."""

    enabled: bool
    n_estimators: int
    max_depth: int | None
    min_samples_leaf: int
    max_features: str | int | float


@dataclass(frozen=True)
class ModelLoggingConfig:
    """Logging settings for the modeling stage."""

    level: str
    log_to_file: bool
    log_dir: Path
    message_format: str


@dataclass(frozen=True)
class ModelPipelineConfig:
    """Resolved config bundle for the modeling-baselines stage."""

    root_dir: Path
    project: ProjectConfig
    label: ModelLabelConfig
    dataset: ModelDatasetConfig
    splits: ModelSplitConfig
    preprocessing: ModelPreprocessingConfig
    classification: ModelClassificationConfig
    execution: ModelExecutionConfig
    deterministic_baseline: DeterministicBaselineConfig
    backtest: ModelBacktestConfig
    logistic_regression: LogisticRegressionBaselineConfig
    random_forest: RandomForestBaselineConfig
    logging: ModelLoggingConfig
    config_files: dict[str, Path]

    @property
    def outputs(self):  # noqa: ANN201
        """Expose shared artifact paths from the project config."""
        return self.project.outputs


def load_model_pipeline_config(
    root_dir: Path | None = None,
    execution_mode: str | None = None,
) -> ModelPipelineConfig:
    """Load the config bundle for the modeling-baselines stage."""
    resolved_root = root_dir or repo_root()
    project = load_project_config(resolved_root, execution_mode=execution_mode)

    model_path = resolved_root / "config" / "model.yaml"
    logging_path = resolved_root / "config" / "logging.yaml"

    model_raw = _load_yaml_mapping(model_path)
    logging_raw = _load_yaml_mapping(logging_path)

    label_raw = model_raw["label"]
    dataset_raw = model_raw["dataset"]
    splits_raw = model_raw["splits"]
    fixed_splits_raw = splits_raw.get("fixed_date_windows")
    if fixed_splits_raw is None:
        fixed_splits_raw = {
            "train": splits_raw["train"],
            "validation": splits_raw["validation"],
            "test": splits_raw["test"],
        }
    walk_forward_raw = splits_raw.get("walk_forward", {})
    preprocessing_raw = model_raw["preprocessing"]
    classification_raw = model_raw["classification"]
    execution_raw = model_raw["execution"]
    deterministic_raw = model_raw["deterministic_baseline"]
    backtest_raw = model_raw["backtest"]
    models_raw = model_raw["models"]
    logging_section = logging_raw["logging"]

    config = ModelPipelineConfig(
        root_dir=resolved_root,
        project=project,
        label=ModelLabelConfig(
            target_type=str(label_raw["target_type"]),
            horizon_months=int(label_raw["horizon_months"]),
            benchmark=str(label_raw["benchmark"]).upper(),
            positive_threshold=float(label_raw.get("positive_threshold", 0.0)),
            cross_sectional_top_n=(
                None
                if label_raw.get("cross_sectional_top_n") is None
                else int(label_raw["cross_sectional_top_n"])
            ),
        ),
        dataset=ModelDatasetConfig(
            feature_columns=_as_tuple(dataset_raw["feature_columns"]),
            minimum_non_missing_features=int(dataset_raw["minimum_non_missing_features"]),
        ),
        splits=ModelSplitConfig(
            scheme=str(splits_raw["scheme"]),
            fixed_date_windows=ModelFixedDateWindowsConfig(
                train=ModelDateWindow(
                    start_date=str(fixed_splits_raw["train"]["start_date"]),
                    end_date=str(fixed_splits_raw["train"]["end_date"]),
                ),
                validation=ModelDateWindow(
                    start_date=str(fixed_splits_raw["validation"]["start_date"]),
                    end_date=str(fixed_splits_raw["validation"]["end_date"]),
                ),
                test=ModelDateWindow(
                    start_date=str(fixed_splits_raw["test"]["start_date"]),
                    end_date=str(fixed_splits_raw["test"]["end_date"]),
                ),
            ),
            walk_forward=ModelWalkForwardConfig(
                min_train_periods=int(walk_forward_raw.get("min_train_periods", 0)),
                validation_window_periods=int(
                    walk_forward_raw.get("validation_window_periods", 0)
                ),
                test_window_periods=int(walk_forward_raw.get("test_window_periods", 0)),
                step_periods=int(walk_forward_raw.get("step_periods", 0)),
            ),
        ),
        preprocessing=ModelPreprocessingConfig(
            numeric_imputation_strategy=str(preprocessing_raw["numeric_imputation_strategy"]),
            scale_numeric=bool(preprocessing_raw["scale_numeric"]),
        ),
        classification=ModelClassificationConfig(
            class_threshold=float(classification_raw["class_threshold"])
        ),
        execution=ModelExecutionConfig(
            selected_model=str(execution_raw["selected_model"]),
            random_state=int(execution_raw["random_state"]),
            append_experiment_registry=bool(execution_raw["append_experiment_registry"]),
        ),
        deterministic_baseline=DeterministicBaselineConfig(
            enabled=bool(deterministic_raw["enabled"]),
            score_column=str(deterministic_raw["score_column"]),
            class_column=str(deterministic_raw["class_column"]),
        ),
        backtest=ModelBacktestConfig(
            score_column=str(backtest_raw["score_column"]),
            prediction_splits=_as_tuple(backtest_raw["prediction_splits"]),
        ),
        logistic_regression=LogisticRegressionBaselineConfig(
            enabled=bool(models_raw["logistic_regression"]["enabled"]),
            penalty=str(models_raw["logistic_regression"]["penalty"]),
            c=float(models_raw["logistic_regression"]["c"]),
            solver=str(models_raw["logistic_regression"]["solver"]),
            max_iter=int(models_raw["logistic_regression"]["max_iter"]),
        ),
        random_forest=RandomForestBaselineConfig(
            enabled=bool(models_raw["random_forest"]["enabled"]),
            n_estimators=int(models_raw["random_forest"]["n_estimators"]),
            max_depth=(
                None
                if models_raw["random_forest"].get("max_depth") is None
                else int(models_raw["random_forest"]["max_depth"])
            ),
            min_samples_leaf=int(models_raw["random_forest"]["min_samples_leaf"]),
            max_features=models_raw["random_forest"]["max_features"],
        ),
        logging=ModelLoggingConfig(
            level=str(logging_section["level"]).upper(),
            log_to_file=bool(logging_section["log_to_file"]),
            log_dir=resolved_root / Path(str(logging_section["log_dir"])),
            message_format=str(logging_section["format"]),
        ),
        config_files={
            "model": model_path,
            "execution": resolved_root / "config" / "execution.yaml",
            "evaluation": resolved_root / "config" / "evaluation.yaml",
            "logging": logging_path,
            "paths": resolved_root / "config" / "paths.yaml",
            "backtest": resolved_root / "config" / "backtest.yaml",
            "signals": resolved_root / "config" / "signals.yaml",
        },
    )

    supported_labels = {
        "forward_excess_return_top_n_binary",
        "forward_excess_return_positive_binary",
        "forward_raw_return_positive_binary",
    }
    if config.label.target_type not in supported_labels:
        raise ValueError(
            f"Unsupported label.target_type={config.label.target_type!r}. "
            f"Supported values: {sorted(supported_labels)}"
        )
    if config.label.horizon_months <= 0:
        raise ValueError("label.horizon_months must be positive.")
    if not config.dataset.feature_columns:
        raise ValueError("dataset.feature_columns must not be empty.")
    if config.dataset.minimum_non_missing_features < 0:
        raise ValueError("dataset.minimum_non_missing_features must be non-negative.")
    if config.splits.scheme not in {"fixed_date_windows", "expanding_walk_forward"}:
        raise ValueError(
            "splits.scheme must be 'fixed_date_windows' or 'expanding_walk_forward'."
        )
    if config.splits.scheme == "expanding_walk_forward":
        if config.splits.walk_forward.min_train_periods <= 0:
            raise ValueError("walk_forward.min_train_periods must be positive.")
        if config.splits.walk_forward.validation_window_periods < 0:
            raise ValueError("walk_forward.validation_window_periods must be non-negative.")
        if config.splits.walk_forward.test_window_periods <= 0:
            raise ValueError("walk_forward.test_window_periods must be positive.")
        if config.splits.walk_forward.step_periods <= 0:
            raise ValueError("walk_forward.step_periods must be positive.")
        if config.splits.walk_forward.step_periods < (
            config.splits.walk_forward.validation_window_periods
            + config.splits.walk_forward.test_window_periods
        ):
            raise ValueError(
                "walk_forward.step_periods must be at least as large as the combined "
                "validation and test window lengths to avoid duplicate held-out dates."
            )
    if not 0.0 < config.classification.class_threshold < 1.0:
        raise ValueError("classification.class_threshold must fall inside (0, 1).")
    if config.execution.selected_model not in {"logistic_regression", "random_forest"}:
        raise ValueError(
            "execution.selected_model must be 'logistic_regression' or 'random_forest'."
        )
    if config.execution.selected_model == "logistic_regression" and not config.logistic_regression.enabled:
        raise ValueError("execution.selected_model='logistic_regression' but the model is disabled.")
    if config.execution.selected_model == "random_forest" and not config.random_forest.enabled:
        raise ValueError("execution.selected_model='random_forest' but the model is disabled.")
    if not config.backtest.prediction_splits:
        raise ValueError("backtest.prediction_splits must not be empty.")
    unsupported_splits = sorted(
        set(config.backtest.prediction_splits) - {"train", "validation", "test"}
    )
    if unsupported_splits:
        raise ValueError(
            f"Unsupported backtest.prediction_splits values: {unsupported_splits}"
        )
    if (
        config.label.target_type == "forward_excess_return_top_n_binary"
        and config.label.cross_sectional_top_n is None
    ):
        raise ValueError(
            "label.cross_sectional_top_n is required for forward_excess_return_top_n_binary."
        )
    if config.label.cross_sectional_top_n is not None and config.label.cross_sectional_top_n <= 0:
        raise ValueError("label.cross_sectional_top_n must be positive when provided.")

    return config


def configure_model_logging(config: ModelPipelineConfig) -> None:
    """Configure process logging for the modeling CLI entrypoints."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if config.logging.log_to_file:
        config.logging.log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(config.logging.log_dir / "model_pipeline.log"))

    logging.basicConfig(
        level=getattr(logging, config.logging.level, logging.INFO),
        format=config.logging.message_format,
        handlers=handlers,
        force=True,
    )
