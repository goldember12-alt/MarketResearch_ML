"""Focused tests for leakage-safe feature generation."""

from __future__ import annotations

from dataclasses import replace
import math

import pandas as pd
import pytest

from src.features.config import load_feature_pipeline_config
from src.features.engineering import build_feature_panel
from src.features.qc import build_feature_missingness_summary


def _build_single_ticker_panel() -> pd.DataFrame:
    dates = pd.date_range("2023-01-31", periods=14, freq="ME")
    benchmark_returns = [
        math.nan,
        0.01,
        0.02,
        -0.01,
        0.03,
        0.015,
        -0.005,
        0.02,
        0.01,
        -0.015,
        0.025,
        0.005,
        0.03,
        0.01,
    ]
    security_returns = [math.nan] + [value * 2.0 for value in benchmark_returns[1:]]

    benchmark_close = [100.0]
    security_close = [50.0]
    for benchmark_return, security_return in zip(benchmark_returns[1:], security_returns[1:]):
        benchmark_close.append(benchmark_close[-1] * (1.0 + benchmark_return))
        security_close.append(security_close[-1] * (1.0 + security_return))

    return pd.DataFrame(
        {
            "ticker": ["AAA"] * len(dates),
            "date": dates,
            "benchmark_ticker": ["SPY"] * len(dates),
            "adjusted_close": security_close,
            "monthly_return": security_returns,
            "benchmark_return": benchmark_returns,
            "sector": ["Technology"] * len(dates),
            "industry": ["Software"] * len(dates),
            "market_cap": [100 + idx for idx in range(len(dates))],
            "pe_ratio": [20 + idx for idx in range(len(dates))],
            "price_to_sales": [3.0 + idx * 0.1 for idx in range(len(dates))],
            "price_to_book": [4.0 + idx * 0.1 for idx in range(len(dates))],
            "ev_to_ebitda": [10.0 + idx * 0.1 for idx in range(len(dates))],
            "gross_margin": [0.30 + idx * 0.001 for idx in range(len(dates))],
            "operating_margin": [0.20 + idx * 0.001 for idx in range(len(dates))],
            "roe": [0.15 + idx * 0.001 for idx in range(len(dates))],
            "roa": [0.06 + idx * 0.001 for idx in range(len(dates))],
            "revenue_growth": [0.05 + idx * 0.001 for idx in range(len(dates))],
            "eps_growth": [0.04 + idx * 0.001 for idx in range(len(dates))],
            "debt_to_equity": [0.40 + idx * 0.01 for idx in range(len(dates))],
            "current_ratio": [1.20 + idx * 0.01 for idx in range(len(dates))],
            "fundamentals_source_date": dates,
            "fundamentals_effective_date": dates,
        }
    )


def test_build_feature_panel_computes_lagged_and_rolling_price_features() -> None:
    """Price features should use only prior-month information."""
    panel = _build_single_ticker_panel()
    config = load_feature_pipeline_config()

    feature_panel, metadata = build_feature_panel(panel, config)

    last_row = feature_panel.iloc[-1]
    expected_ret_1m_lag1 = panel.iloc[-2]["monthly_return"]
    expected_mom_3m = (1.0 + panel.iloc[-4:-1]["monthly_return"]).prod() - 1.0
    expected_mom_6m = (1.0 + panel.iloc[-7:-1]["monthly_return"]).prod() - 1.0
    expected_drawdown = 0.0

    assert last_row["ret_1m_lag1"] == pytest.approx(expected_ret_1m_lag1)
    assert last_row["mom_3m"] == pytest.approx(expected_mom_3m)
    assert last_row["mom_6m"] == pytest.approx(expected_mom_6m)
    assert last_row["drawdown_12m"] == pytest.approx(expected_drawdown)
    assert last_row["beta_12m_spy"] == pytest.approx(2.0, rel=1e-6)
    assert "ret_1m_lag1" in metadata["feature_columns"]
    assert "price_based" in metadata["feature_groups"]


def test_build_feature_panel_lags_fundamental_features_one_period() -> None:
    """Fundamental features should shift by the configured lag period."""
    panel = _build_single_ticker_panel().iloc[:4].copy()
    config = load_feature_pipeline_config()

    feature_panel, _ = build_feature_panel(panel, config)

    assert pd.isna(feature_panel.loc[0, "pe_ratio_lag1"])
    assert feature_panel.loc[1, "pe_ratio_lag1"] == pytest.approx(panel.loc[0, "pe_ratio"])
    assert feature_panel.loc[3, "market_cap_lag1"] == pytest.approx(panel.loc[2, "market_cap"])
    assert feature_panel.loc[2, "gross_margin_lag1"] == pytest.approx(panel.loc[1, "gross_margin"])


def test_build_feature_panel_preserves_one_row_per_ticker_per_month() -> None:
    """Feature generation should preserve the canonical panel grid."""
    panel = pd.concat([_build_single_ticker_panel(), _build_single_ticker_panel().assign(ticker="BBB")])
    config = load_feature_pipeline_config()

    feature_panel, _ = build_feature_panel(panel, config)

    assert len(feature_panel) == len(panel)
    assert feature_panel[["ticker", "date"]].duplicated().sum() == 0


def test_missingness_summary_reports_feature_level_missing_rates() -> None:
    """Missingness summaries should expose per-feature coverage rates."""
    panel = _build_single_ticker_panel().iloc[:4].copy()
    config = load_feature_pipeline_config()
    reduced_config = replace(
        config,
        groups=replace(
            config.groups,
            price_based=False,
            quality_profitability=False,
            growth=False,
            balance_sheet=False,
            market_cap=False,
        ),
    )

    feature_panel, metadata = build_feature_panel(panel, reduced_config)
    missingness = build_feature_missingness_summary(
        feature_panel,
        feature_columns=metadata["feature_columns"],
        feature_groups=metadata["feature_groups"],
    )

    pe_row = missingness.loc[missingness["feature_name"] == "pe_ratio_lag1"].iloc[0]
    assert pe_row["missing_count"] == 1
    assert pe_row["missing_ratio"] == pytest.approx(0.25)
    assert pe_row["feature_group"] == "valuation_based"
