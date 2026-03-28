"""Leakage-safe monthly feature engineering from the canonical panel."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.data.standardize import assert_unique_keys
from src.features.config import FeaturePipelineConfig


VALUATION_COLUMNS = ("pe_ratio", "price_to_sales", "price_to_book", "ev_to_ebitda")
QUALITY_COLUMNS = ("gross_margin", "operating_margin", "roe", "roa")
GROWTH_COLUMNS = ("revenue_growth", "eps_growth")
BALANCE_SHEET_COLUMNS = ("debt_to_equity", "current_ratio")
MARKET_CAP_COLUMNS = ("market_cap",)


def _rolling_compounded_return(series: pd.Series, window: int) -> pd.Series:
    return (
        (1.0 + series).rolling(window=window, min_periods=window).apply(np.prod, raw=True) - 1.0
    )


def _group_rolling_std(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).std()


def _group_drawdown(series: pd.Series, window: int) -> pd.Series:
    rolling_high = series.rolling(window=window, min_periods=window).max()
    return series / rolling_high - 1.0


def _rolling_beta(security_returns: pd.Series, benchmark_returns: pd.Series, window: int) -> pd.Series:
    covariance = security_returns.rolling(window=window, min_periods=window).cov(benchmark_returns)
    benchmark_variance = benchmark_returns.rolling(window=window, min_periods=window).var()
    return covariance / benchmark_variance


def _add_group_lag_features(
    feature_panel: pd.DataFrame,
    panel: pd.DataFrame,
    *,
    source_columns: tuple[str, ...],
    lag_periods: int,
) -> tuple[pd.DataFrame, list[str]]:
    feature_columns: list[str] = []
    for column in source_columns:
        if column not in panel.columns:
            continue
        feature_name = f"{column}_lag{lag_periods}"
        feature_panel[feature_name] = panel.groupby("ticker", sort=False)[column].shift(lag_periods)
        feature_columns.append(feature_name)
    return feature_panel, feature_columns


def _build_price_features(panel: pd.DataFrame, config: FeaturePipelineConfig) -> tuple[pd.DataFrame, list[str]]:
    feature_panel = panel[["ticker", "date", "benchmark_ticker"]].copy()

    lagged_security_return = panel.groupby("ticker", sort=False)["monthly_return"].shift(
        config.lags.default_periods
    )
    lagged_adjusted_close = panel.groupby("ticker", sort=False)["adjusted_close"].shift(
        config.lags.default_periods
    )
    lagged_benchmark_return = panel.groupby("ticker", sort=False)["benchmark_return"].shift(
        config.lags.default_periods
    )

    feature_panel["ret_1m_lag1"] = lagged_security_return
    feature_panel["mom_3m"] = panel.groupby("ticker", sort=False)["monthly_return"].transform(
        lambda series: _rolling_compounded_return(series.shift(config.lags.default_periods), config.lookbacks.momentum_3m)
    )
    feature_panel["mom_6m"] = panel.groupby("ticker", sort=False)["monthly_return"].transform(
        lambda series: _rolling_compounded_return(series.shift(config.lags.default_periods), config.lookbacks.momentum_6m)
    )
    feature_panel["mom_12m"] = panel.groupby("ticker", sort=False)["monthly_return"].transform(
        lambda series: _rolling_compounded_return(series.shift(config.lags.default_periods), config.lookbacks.momentum_12m)
    )
    feature_panel["drawdown_12m"] = panel.groupby("ticker", sort=False)["adjusted_close"].transform(
        lambda series: _group_drawdown(series.shift(config.lags.default_periods), config.lookbacks.drawdown_12m)
    )
    feature_panel["vol_12m"] = panel.groupby("ticker", sort=False)["monthly_return"].transform(
        lambda series: _group_rolling_std(series.shift(config.lags.default_periods), config.lookbacks.volatility_12m)
    )
    beta_parts: list[pd.Series] = []
    for _, frame in panel.groupby("ticker", sort=False):
        beta_parts.append(
            pd.Series(
                _rolling_beta(
                    frame["monthly_return"].shift(config.lags.default_periods),
                    frame["benchmark_return"].shift(config.lags.default_periods),
                    config.lookbacks.beta_12m,
                ).to_numpy(),
                index=frame.index,
            )
        )
    feature_panel["beta_12m_spy"] = pd.concat(beta_parts).sort_index().to_numpy()
    feature_panel["adjusted_close_lag1"] = lagged_adjusted_close
    feature_panel["benchmark_return_lag1"] = lagged_benchmark_return

    return feature_panel, [
        "ret_1m_lag1",
        "mom_3m",
        "mom_6m",
        "mom_12m",
        "drawdown_12m",
        "vol_12m",
        "beta_12m_spy",
        "adjusted_close_lag1",
        "benchmark_return_lag1",
    ]


def build_feature_panel(panel: pd.DataFrame, config: FeaturePipelineConfig) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build the configured feature panel from the canonical monthly panel."""
    assert_unique_keys(panel, ["ticker", "date"], "monthly_panel")
    sorted_panel = panel.sort_values(["ticker", "date"]).reset_index(drop=True)

    feature_panel = sorted_panel[
        [
            "ticker",
            "date",
            "benchmark_ticker",
            "sector",
            "industry",
            "fundamentals_source_date",
            "fundamentals_effective_date",
        ]
    ].copy()

    if config.missingness.categorical_fill == "missing":
        for column in ("sector", "industry"):
            feature_panel[column] = feature_panel[column].fillna("missing")

    feature_columns: list[str] = []
    feature_groups: dict[str, list[str]] = {}

    if config.groups.price_based:
        price_features, price_feature_names = _build_price_features(sorted_panel, config)
        for column in price_feature_names:
            feature_panel[column] = price_features[column]
        feature_columns.extend(price_feature_names)
        feature_groups["price_based"] = price_feature_names

    if config.groups.market_cap:
        feature_panel, market_cap_feature_names = _add_group_lag_features(
            feature_panel,
            sorted_panel,
            source_columns=MARKET_CAP_COLUMNS,
            lag_periods=config.lags.fundamentals_periods,
        )
        feature_columns.extend(market_cap_feature_names)
        feature_groups["market_cap"] = market_cap_feature_names

    if config.groups.valuation_based:
        feature_panel, valuation_feature_names = _add_group_lag_features(
            feature_panel,
            sorted_panel,
            source_columns=VALUATION_COLUMNS,
            lag_periods=config.lags.fundamentals_periods,
        )
        feature_columns.extend(valuation_feature_names)
        feature_groups["valuation_based"] = valuation_feature_names

    if config.groups.quality_profitability:
        feature_panel, quality_feature_names = _add_group_lag_features(
            feature_panel,
            sorted_panel,
            source_columns=QUALITY_COLUMNS,
            lag_periods=config.lags.fundamentals_periods,
        )
        feature_columns.extend(quality_feature_names)
        feature_groups["quality_profitability"] = quality_feature_names

    if config.groups.growth:
        feature_panel, growth_feature_names = _add_group_lag_features(
            feature_panel,
            sorted_panel,
            source_columns=GROWTH_COLUMNS,
            lag_periods=config.lags.fundamentals_periods,
        )
        feature_columns.extend(growth_feature_names)
        feature_groups["growth"] = growth_feature_names

    if config.groups.balance_sheet:
        feature_panel, balance_sheet_feature_names = _add_group_lag_features(
            feature_panel,
            sorted_panel,
            source_columns=BALANCE_SHEET_COLUMNS,
            lag_periods=config.lags.fundamentals_periods,
        )
        feature_columns.extend(balance_sheet_feature_names)
        feature_groups["balance_sheet"] = balance_sheet_feature_names

    if config.missingness.numeric_fill != "none":
        raise ValueError(
            "Only numeric_fill='none' is implemented currently to avoid masking missingness."
        )

    feature_panel = feature_panel.sort_values(["ticker", "date"]).reset_index(drop=True)
    assert_unique_keys(feature_panel, ["ticker", "date"], "feature_panel")

    metadata: dict[str, Any] = {
        "feature_columns": feature_columns,
        "feature_groups": feature_groups,
        "lookbacks": {
            "momentum_3m": config.lookbacks.momentum_3m,
            "momentum_6m": config.lookbacks.momentum_6m,
            "momentum_12m": config.lookbacks.momentum_12m,
            "drawdown_12m": config.lookbacks.drawdown_12m,
            "volatility_12m": config.lookbacks.volatility_12m,
            "beta_12m": config.lookbacks.beta_12m,
        },
        "lags": {
            "default_periods": config.lags.default_periods,
            "fundamentals_periods": config.lags.fundamentals_periods,
        },
    }
    return feature_panel, metadata
