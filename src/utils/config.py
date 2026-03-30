"""Typed config loading for the canonical project scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parents[2]


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Read a YAML file and validate that it contains a mapping."""
    parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected a mapping at {path}")
    return parsed


def _as_tuple(values: Any) -> tuple[str, ...]:
    """Normalize a YAML sequence into an immutable string tuple."""
    if values is None:
        return ()
    if not isinstance(values, list):
        raise ValueError(f"Expected a list of strings, received {type(values)!r}")
    return tuple(str(value) for value in values)


@dataclass(frozen=True)
class UniverseConfig:
    """Config describing the initial research universe and benchmarks."""

    preset_name: str
    description: str
    tech_tickers: tuple[str, ...]
    comparison_tickers: tuple[str, ...]
    explicit_benchmarks: tuple[str, ...]
    derived_benchmarks: tuple[str, ...]
    frequency: str
    start_date: str
    end_date: str | None

    @property
    def all_tickers(self) -> tuple[str, ...]:
        """Return the full seeded research universe."""
        return self.tech_tickers + self.comparison_tickers


@dataclass(frozen=True)
class ExecutionModeConfig:
    """Execution-mode settings shared across data, backtest, and reporting stages."""

    default_mode: str
    mode_name: str
    description: str
    raw_file_policy: str
    allow_sample_fallback: bool
    sample_file_token: str


@dataclass(frozen=True)
class EvaluationEvidenceConfig:
    """Thresholds used to classify segment-history sufficiency in reports."""

    minimum_months_for_descriptive_segment: int
    minimum_months_for_broader_coverage_segment: int


@dataclass(frozen=True)
class EvaluationSegmentationConfig:
    """Config controlling which subperiod and regime buckets are produced."""

    include_fold: bool
    include_calendar_month: bool
    include_calendar_quarter: bool
    include_calendar_half_year: bool
    include_calendar_year: bool
    include_benchmark_direction: bool
    include_drawdown_state: bool
    drawdown_flat_threshold: float
    include_volatility_state: bool
    volatility_lookback_months: int
    volatility_state_split: str


@dataclass(frozen=True)
class EvaluationConfig:
    """Cross-stage reporting and evaluation settings."""

    evidence: EvaluationEvidenceConfig
    segmentation: EvaluationSegmentationConfig


@dataclass(frozen=True)
class BacktestConfig:
    """Config describing baseline portfolio construction assumptions."""

    selection_method: str
    top_n: int
    weighting: str
    max_position_weight: float
    sector_cap: float | None
    frequency: str
    decision_anchor: str
    trade_timing: str
    transaction_cost_bps: float
    slippage_bps: float
    comparison_benchmarks: tuple[str, ...]


@dataclass(frozen=True)
class OutputPathsConfig:
    """Canonical directories and artifact paths produced by the pipeline."""

    root: Path
    data_dir: Path
    features_dir: Path
    signals_dir: Path
    backtests_dir: Path
    models_dir: Path
    reports_dir: Path
    paper_trading_dir: Path
    prices_monthly: Path
    fundamentals_monthly: Path
    benchmarks_monthly: Path
    monthly_panel: Path
    prices_qc_summary: Path
    fundamentals_qc_summary: Path
    benchmarks_qc_summary: Path
    panel_qc_summary: Path
    ticker_coverage_summary: Path
    date_coverage_summary: Path
    feature_panel: Path
    feature_qc_summary: Path
    feature_missingness_summary: Path
    signal_rankings: Path
    signal_qc_summary: Path
    signal_selection_summary: Path
    holdings_history: Path
    trade_log: Path
    portfolio_returns: Path
    benchmark_returns: Path
    backtest_summary: Path
    train_predictions: Path
    test_predictions: Path
    model_metadata: Path
    feature_importance: Path
    model_signal_rankings: Path
    strategy_report: Path
    model_strategy_report: Path
    run_summary: Path
    model_comparison_summary: Path
    model_subperiod_comparison: Path
    experiment_registry: Path
    performance_by_period: Path
    risk_metrics_summary: Path
    model_holdings_history: Path
    model_trade_log: Path
    model_portfolio_returns: Path
    model_benchmark_returns: Path
    model_backtest_summary: Path
    model_performance_by_period: Path
    model_risk_metrics_summary: Path

    @property
    def stage_directories(self) -> tuple[Path, ...]:
        """Return the top-level output directories that should always exist."""
        return (
            self.data_dir,
            self.features_dir,
            self.signals_dir,
            self.backtests_dir,
            self.models_dir,
            self.reports_dir,
            self.paper_trading_dir,
        )


@dataclass(frozen=True)
class ProjectConfig:
    """Resolved project configuration for the scaffolded research workflow."""

    root_dir: Path
    universe: UniverseConfig
    execution: ExecutionModeConfig
    evaluation: EvaluationConfig
    backtest: BacktestConfig
    outputs: OutputPathsConfig
    config_files: dict[str, Path]


def _resolve_paths(root_dir: Path, path_values: dict[str, str]) -> dict[str, Path]:
    """Resolve configured relative paths from the repository root."""
    return {key: root_dir / Path(value) for key, value in path_values.items()}


def load_project_config(
    root_dir: Path | None = None,
    execution_mode: str | None = None,
) -> ProjectConfig:
    """Load the minimal cross-stage project contract used by all CLI entrypoints."""
    resolved_root = root_dir or repo_root()

    universe_path = resolved_root / "config" / "universe.yaml"
    execution_path = resolved_root / "config" / "execution.yaml"
    evaluation_path = resolved_root / "config" / "evaluation.yaml"
    backtest_path = resolved_root / "config" / "backtest.yaml"
    paths_path = resolved_root / "config" / "paths.yaml"

    universe_raw = _load_yaml_file(universe_path)
    execution_raw = _load_yaml_file(execution_path)
    evaluation_raw = _load_yaml_file(evaluation_path)
    backtest_raw = _load_yaml_file(backtest_path)
    paths_raw = _load_yaml_file(paths_path)

    preset = universe_raw["preset"]
    universe_section = universe_raw["universe"]
    benchmarks_section = universe_raw["benchmarks"]
    calendar = universe_raw["calendar"]

    universe = UniverseConfig(
        preset_name=str(preset["name"]),
        description=str(preset["description"]),
        tech_tickers=_as_tuple(universe_section["tech_large_cap"]),
        comparison_tickers=_as_tuple(universe_section["comparison_large_cap_non_tech"]),
        explicit_benchmarks=_as_tuple(benchmarks_section["explicit"]),
        derived_benchmarks=_as_tuple(benchmarks_section["derived"]),
        frequency=str(calendar["frequency"]),
        start_date=str(calendar["start_date"]),
        end_date=(
            None if calendar.get("end_date") is None else str(calendar["end_date"])
        ),
    )

    default_mode = str(execution_raw["default_mode"])
    selected_mode = execution_mode or default_mode
    modes_raw = execution_raw["modes"]
    if selected_mode not in modes_raw:
        raise ValueError(
            f"Unsupported execution mode {selected_mode!r}. Supported modes: {sorted(modes_raw)}"
        )
    sample_file_token = str(execution_raw["raw_data_selection"]["sample_file_token"])
    selected_mode_raw = modes_raw[selected_mode]
    execution = ExecutionModeConfig(
        default_mode=default_mode,
        mode_name=selected_mode,
        description=str(selected_mode_raw["description"]),
        raw_file_policy=str(selected_mode_raw["raw_file_policy"]),
        allow_sample_fallback=bool(selected_mode_raw["allow_sample_fallback"]),
        sample_file_token=sample_file_token,
    )
    if execution.raw_file_policy not in {"sample_only", "prefer_non_sample"}:
        raise ValueError(
            "execution.raw_file_policy must be 'sample_only' or 'prefer_non_sample'."
        )

    evidence_raw = evaluation_raw["evidence_thresholds"]
    segmentation_raw = evaluation_raw["segmentation"]
    evaluation = EvaluationConfig(
        evidence=EvaluationEvidenceConfig(
            minimum_months_for_descriptive_segment=int(
                evidence_raw["minimum_months_for_descriptive_segment"]
            ),
            minimum_months_for_broader_coverage_segment=int(
                evidence_raw["minimum_months_for_broader_coverage_segment"]
            ),
        ),
        segmentation=EvaluationSegmentationConfig(
            include_fold=bool(segmentation_raw["include_fold"]),
            include_calendar_month=bool(segmentation_raw["include_calendar_month"]),
            include_calendar_quarter=bool(segmentation_raw["include_calendar_quarter"]),
            include_calendar_half_year=bool(segmentation_raw["include_calendar_half_year"]),
            include_calendar_year=bool(segmentation_raw["include_calendar_year"]),
            include_benchmark_direction=bool(segmentation_raw["include_benchmark_direction"]),
            include_drawdown_state=bool(segmentation_raw["include_drawdown_state"]),
            drawdown_flat_threshold=float(segmentation_raw["drawdown_flat_threshold"]),
            include_volatility_state=bool(segmentation_raw["include_volatility_state"]),
            volatility_lookback_months=int(segmentation_raw["volatility_lookback_months"]),
            volatility_state_split=str(segmentation_raw["volatility_state_split"]),
        ),
    )
    if evaluation.evidence.minimum_months_for_descriptive_segment <= 0:
        raise ValueError(
            "evaluation minimum_months_for_descriptive_segment must be positive."
        )
    if (
        evaluation.evidence.minimum_months_for_broader_coverage_segment
        < evaluation.evidence.minimum_months_for_descriptive_segment
    ):
        raise ValueError(
            "evaluation minimum_months_for_broader_coverage_segment must be greater than "
            "or equal to minimum_months_for_descriptive_segment."
        )
    if evaluation.segmentation.volatility_lookback_months <= 0:
        raise ValueError("evaluation volatility_lookback_months must be positive.")
    if evaluation.segmentation.volatility_state_split != "median":
        raise ValueError("evaluation volatility_state_split currently supports only 'median'.")

    portfolio = backtest_raw["portfolio"]
    rebalancing = backtest_raw["rebalancing"]
    costs = backtest_raw["costs"]
    backtest_benchmarks = backtest_raw["benchmarks"]

    backtest = BacktestConfig(
        selection_method=str(portfolio["selection_method"]),
        top_n=int(portfolio["top_n"]),
        weighting=str(portfolio["weighting"]),
        max_position_weight=float(portfolio["max_position_weight"]),
        sector_cap=(
            None if portfolio.get("sector_cap") is None else float(portfolio["sector_cap"])
        ),
        frequency=str(rebalancing["frequency"]),
        decision_anchor=str(rebalancing["decision_anchor"]),
        trade_timing=str(rebalancing["trade_timing"]),
        transaction_cost_bps=float(costs["transaction_cost_bps"]),
        slippage_bps=float(costs["slippage_bps"]),
        comparison_benchmarks=_as_tuple(backtest_benchmarks["compare_to"]),
    )

    output_dirs = _resolve_paths(resolved_root, paths_raw["outputs"])
    artifact_paths = _resolve_paths(resolved_root, paths_raw["artifacts"])

    outputs = OutputPathsConfig(
        root=output_dirs["root"],
        data_dir=output_dirs["data_dir"],
        features_dir=output_dirs["features_dir"],
        signals_dir=output_dirs["signals_dir"],
        backtests_dir=output_dirs["backtests_dir"],
        models_dir=output_dirs["models_dir"],
        reports_dir=output_dirs["reports_dir"],
        paper_trading_dir=output_dirs["paper_trading_dir"],
        prices_monthly=artifact_paths["prices_monthly"],
        fundamentals_monthly=artifact_paths["fundamentals_monthly"],
        benchmarks_monthly=artifact_paths["benchmarks_monthly"],
        monthly_panel=artifact_paths["monthly_panel"],
        prices_qc_summary=artifact_paths["prices_qc_summary"],
        fundamentals_qc_summary=artifact_paths["fundamentals_qc_summary"],
        benchmarks_qc_summary=artifact_paths["benchmarks_qc_summary"],
        panel_qc_summary=artifact_paths["panel_qc_summary"],
        ticker_coverage_summary=artifact_paths["ticker_coverage_summary"],
        date_coverage_summary=artifact_paths["date_coverage_summary"],
        feature_panel=artifact_paths["feature_panel"],
        feature_qc_summary=artifact_paths["feature_qc_summary"],
        feature_missingness_summary=artifact_paths["feature_missingness_summary"],
        signal_rankings=artifact_paths["signal_rankings"],
        signal_qc_summary=artifact_paths["signal_qc_summary"],
        signal_selection_summary=artifact_paths["signal_selection_summary"],
        holdings_history=artifact_paths["holdings_history"],
        trade_log=artifact_paths["trade_log"],
        portfolio_returns=artifact_paths["portfolio_returns"],
        benchmark_returns=artifact_paths["benchmark_returns"],
        backtest_summary=artifact_paths["backtest_summary"],
        train_predictions=artifact_paths["train_predictions"],
        test_predictions=artifact_paths["test_predictions"],
        model_metadata=artifact_paths["model_metadata"],
        feature_importance=artifact_paths["feature_importance"],
        model_signal_rankings=artifact_paths["model_signal_rankings"],
        strategy_report=artifact_paths["strategy_report"],
        model_strategy_report=artifact_paths["model_strategy_report"],
        run_summary=artifact_paths["run_summary"],
        model_comparison_summary=artifact_paths["model_comparison_summary"],
        model_subperiod_comparison=artifact_paths["model_subperiod_comparison"],
        experiment_registry=artifact_paths["experiment_registry"],
        performance_by_period=artifact_paths["performance_by_period"],
        risk_metrics_summary=artifact_paths["risk_metrics_summary"],
        model_holdings_history=artifact_paths["model_holdings_history"],
        model_trade_log=artifact_paths["model_trade_log"],
        model_portfolio_returns=artifact_paths["model_portfolio_returns"],
        model_benchmark_returns=artifact_paths["model_benchmark_returns"],
        model_backtest_summary=artifact_paths["model_backtest_summary"],
        model_performance_by_period=artifact_paths["model_performance_by_period"],
        model_risk_metrics_summary=artifact_paths["model_risk_metrics_summary"],
    )

    return ProjectConfig(
        root_dir=resolved_root,
        universe=universe,
        execution=execution,
        evaluation=evaluation,
        backtest=backtest,
        outputs=outputs,
        config_files={
            "universe": universe_path,
            "execution": execution_path,
            "evaluation": evaluation_path,
            "backtest": backtest_path,
            "paths": paths_path,
        },
    )


def ensure_output_directories(config: ProjectConfig) -> tuple[Path, ...]:
    """Create the canonical stage output directories if they do not exist."""
    created: list[Path] = []
    for directory in config.outputs.stage_directories:
        directory.mkdir(parents=True, exist_ok=True)
        created.append(directory)
    return tuple(created)
