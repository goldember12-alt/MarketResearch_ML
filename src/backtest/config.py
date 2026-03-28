"""Config loading for the deterministic monthly backtest stage."""

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
class BacktestPortfolioConfig:
    """Portfolio-construction settings for the deterministic backtest."""

    selection_method: str
    selected_top_n: int
    weighting_scheme: str
    max_weight: float
    cash_handling_policy: str
    sector_cap: float | None


@dataclass(frozen=True)
class BacktestRebalancingConfig:
    """Rebalance-timing assumptions for the backtest."""

    frequency: str
    decision_anchor: str
    trade_timing: str
    holding_period_convention: str


@dataclass(frozen=True)
class BacktestCostConfig:
    """Transaction cost assumptions for the backtest."""

    transaction_cost_bps: float
    slippage_bps: float

    @property
    def total_cost_bps(self) -> float:
        """Return the total one-way cost applied to turnover."""
        return self.transaction_cost_bps + self.slippage_bps

    @property
    def total_cost_rate(self) -> float:
        """Return the total one-way cost as a decimal rate."""
        return self.total_cost_bps / 10_000.0


@dataclass(frozen=True)
class BacktestBenchmarkConfig:
    """Benchmark identifiers compared against the portfolio."""

    identifiers: tuple[str, ...]


@dataclass(frozen=True)
class BacktestLoggingConfig:
    """Logging settings for the backtest stage."""

    level: str
    log_to_file: bool
    log_dir: Path
    message_format: str


@dataclass(frozen=True)
class BacktestPipelineConfig:
    """Resolved config bundle for deterministic monthly backtesting."""

    root_dir: Path
    project: ProjectConfig
    portfolio: BacktestPortfolioConfig
    rebalancing: BacktestRebalancingConfig
    costs: BacktestCostConfig
    benchmarks: BacktestBenchmarkConfig
    logging: BacktestLoggingConfig
    config_files: dict[str, Path]

    @property
    def outputs(self):  # noqa: ANN201
        """Expose shared artifact paths from the project config."""
        return self.project.outputs


def load_backtest_pipeline_config(root_dir: Path | None = None) -> BacktestPipelineConfig:
    """Load the deterministic backtest config bundle."""
    resolved_root = root_dir or repo_root()
    project = load_project_config(resolved_root)

    backtest_path = resolved_root / "config" / "backtest.yaml"
    logging_path = resolved_root / "config" / "logging.yaml"

    backtest_raw = _load_yaml_mapping(backtest_path)
    logging_raw = _load_yaml_mapping(logging_path)

    portfolio_raw = backtest_raw["portfolio"]
    rebalancing_raw = backtest_raw["rebalancing"]
    costs_raw = backtest_raw["costs"]
    benchmarks_raw = backtest_raw["benchmarks"]
    logging_section = logging_raw["logging"]

    config = BacktestPipelineConfig(
        root_dir=resolved_root,
        project=project,
        portfolio=BacktestPortfolioConfig(
            selection_method=str(portfolio_raw["selection_method"]),
            selected_top_n=int(portfolio_raw["top_n"]),
            weighting_scheme=str(portfolio_raw["weighting"]),
            max_weight=float(portfolio_raw["max_position_weight"]),
            cash_handling_policy=str(portfolio_raw.get("cash_handling_policy", "redistribute")),
            sector_cap=(
                None
                if portfolio_raw.get("sector_cap") is None
                else float(portfolio_raw["sector_cap"])
            ),
        ),
        rebalancing=BacktestRebalancingConfig(
            frequency=str(rebalancing_raw["frequency"]),
            decision_anchor=str(rebalancing_raw["decision_anchor"]),
            trade_timing=str(rebalancing_raw["trade_timing"]),
            holding_period_convention=(
                "month_end_t_signal_forms_holdings_for_month_end_t_plus_1_realized_return"
            ),
        ),
        costs=BacktestCostConfig(
            transaction_cost_bps=float(costs_raw["transaction_cost_bps"]),
            slippage_bps=float(costs_raw["slippage_bps"]),
        ),
        benchmarks=BacktestBenchmarkConfig(
            identifiers=_as_tuple(benchmarks_raw["compare_to"]),
        ),
        logging=BacktestLoggingConfig(
            level=str(logging_section["level"]).upper(),
            log_to_file=bool(logging_section["log_to_file"]),
            log_dir=resolved_root / Path(str(logging_section["log_dir"])),
            message_format=str(logging_section["format"]),
        ),
        config_files={
            "backtest": backtest_path,
            "logging": logging_path,
            "paths": resolved_root / "config" / "paths.yaml",
            "signals": resolved_root / "config" / "signals.yaml",
        },
    )

    if config.portfolio.selection_method != "top_n":
        raise ValueError("Only selection_method='top_n' is implemented for backtesting.")
    if config.portfolio.selected_top_n <= 0:
        raise ValueError("portfolio.top_n must be positive.")
    if config.portfolio.weighting_scheme not in {"equal_weight", "capped_weight"}:
        raise ValueError(
            "portfolio.weighting must be either 'equal_weight' or 'capped_weight'."
        )
    if not 0.0 < config.portfolio.max_weight <= 1.0:
        raise ValueError("portfolio.max_position_weight must fall inside (0, 1].")
    if config.portfolio.cash_handling_policy not in {"redistribute", "hold_cash"}:
        raise ValueError(
            "portfolio.cash_handling_policy must be 'redistribute' or 'hold_cash'."
        )
    if not config.benchmarks.identifiers:
        raise ValueError("At least one benchmark identifier must be configured.")

    return config


def configure_backtest_logging(config: BacktestPipelineConfig) -> None:
    """Configure process logging for the backtest CLI."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if config.logging.log_to_file:
        config.logging.log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(config.logging.log_dir / "backtest_pipeline.log"))

    logging.basicConfig(
        level=getattr(logging, config.logging.level, logging.INFO),
        format=config.logging.message_format,
        handlers=handlers,
        force=True,
    )
