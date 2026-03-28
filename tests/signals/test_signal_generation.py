"""Focused tests for deterministic signal generation."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from src.signals.config import SignalFeatureConfig, load_signal_pipeline_config
from src.signals.qc import build_signal_selection_summary
from src.signals.scoring import build_signal_rankings


def _build_feature_panel_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC", "AAA", "BBB", "CCC"],
            "date": pd.to_datetime(
                [
                    "2024-05-31",
                    "2024-05-31",
                    "2024-05-31",
                    "2024-06-30",
                    "2024-06-30",
                    "2024-06-30",
                ]
            ),
            "benchmark_ticker": ["SPY"] * 6,
            "sector": ["Technology", "Technology", "Health", "Technology", "Technology", "Health"],
            "industry": ["Software", "Hardware", "Biotech", "Software", "Hardware", "Biotech"],
            "fundamentals_source_date": pd.to_datetime(["2024-03-31"] * 6),
            "fundamentals_effective_date": pd.to_datetime(["2024-05-31"] * 6),
            "market_cap_lag1": [300.0, 200.0, 100.0, 310.0, 210.0, 110.0],
            "ret_1m_lag1": [0.05, 0.03, 0.01, 0.04, 0.04, 0.02],
            "mom_3m": [0.10, 0.05, 0.02, 0.09, 0.09, 0.03],
            "mom_6m": [pd.NA, pd.NA, pd.NA, pd.NA, pd.NA, pd.NA],
            "mom_12m": [pd.NA, pd.NA, pd.NA, pd.NA, pd.NA, pd.NA],
            "drawdown_12m": [pd.NA, pd.NA, pd.NA, pd.NA, pd.NA, pd.NA],
            "gross_margin_lag1": [0.50, 0.30, 0.20, 0.51, 0.31, 0.21],
            "operating_margin_lag1": [0.35, 0.20, 0.10, 0.36, 0.19, 0.11],
            "roe_lag1": [0.18, 0.12, 0.06, 0.19, 0.11, 0.07],
            "roa_lag1": [0.09, 0.06, 0.03, 0.10, 0.05, 0.04],
            "revenue_growth_lag1": [0.12, 0.08, 0.03, 0.13, 0.08, 0.04],
            "eps_growth_lag1": [0.10, 0.06, 0.02, 0.11, 0.05, 0.03],
            "current_ratio_lag1": [1.8, 1.4, 1.1, 1.9, 1.3, 1.0],
            "pe_ratio_lag1": [18.0, 22.0, 30.0, 19.0, 19.0, 28.0],
            "price_to_sales_lag1": [4.0, 5.0, 7.0, 4.2, 4.2, 6.5],
            "price_to_book_lag1": [5.0, 5.5, 6.0, 5.1, 5.1, 5.9],
            "ev_to_ebitda_lag1": [10.0, 12.0, 16.0, 10.5, 10.5, 15.0],
            "debt_to_equity_lag1": [0.20, 0.40, 0.80, 0.22, 0.50, 0.70],
        }
    )


def test_build_signal_rankings_scores_features_with_expected_direction() -> None:
    """Higher-is-better and lower-is-better features should rank correctly."""
    feature_panel = _build_feature_panel_fixture()
    config = load_signal_pipeline_config()

    rankings, metadata = build_signal_rankings(feature_panel, config)
    may = rankings.loc[rankings["date"] == pd.Timestamp("2024-05-31")].sort_values("ticker")

    aaa = may.loc[may["ticker"] == "AAA"].iloc[0]
    ccc = may.loc[may["ticker"] == "CCC"].iloc[0]

    assert aaa["score__ret_1m_lag1"] > ccc["score__ret_1m_lag1"]
    assert aaa["score__pe_ratio_lag1"] > ccc["score__pe_ratio_lag1"]
    assert aaa["composite_score"] > ccc["composite_score"]
    assert "score__ret_1m_lag1" in metadata["score_columns"]


def test_build_signal_rankings_selects_top_n_with_deterministic_tie_breaks() -> None:
    """Ties should resolve through configured tie-break columns."""
    feature_panel = _build_feature_panel_fixture()
    config = load_signal_pipeline_config()
    reduced_config = replace(
        config,
        strategy=replace(
            config.strategy,
            selection_top_n=2,
            minimum_non_missing_features=1,
        ),
        features=SignalFeatureConfig(
            higher_is_better=("ret_1m_lag1",),
            lower_is_better=(),
        ),
        weights={"ret_1m_lag1": 1.0},
    )

    rankings, _ = build_signal_rankings(feature_panel, reduced_config)
    june = rankings.loc[rankings["date"] == pd.Timestamp("2024-06-30")]
    selected = june.loc[june["selected_top_n"]].sort_values("score_rank")

    assert selected["ticker"].tolist() == ["AAA", "BBB"]
    assert selected["score_rank"].tolist() == [1.0, 2.0]


def test_build_signal_rankings_requires_minimum_non_missing_features() -> None:
    """Rows with too few observed features should not receive a composite score."""
    feature_panel = _build_feature_panel_fixture()
    config = load_signal_pipeline_config()
    sparse = feature_panel.copy()
    sparse.loc[sparse["ticker"] == "CCC", [
        "gross_margin_lag1",
        "operating_margin_lag1",
        "roe_lag1",
        "roa_lag1",
        "revenue_growth_lag1",
        "eps_growth_lag1",
        "current_ratio_lag1",
        "pe_ratio_lag1",
        "price_to_sales_lag1",
        "price_to_book_lag1",
        "ev_to_ebitda_lag1",
        "debt_to_equity_lag1",
    ]] = pd.NA

    rankings, _ = build_signal_rankings(sparse, config)
    ccc = rankings.loc[
        (rankings["ticker"] == "CCC") & (rankings["date"] == pd.Timestamp("2024-05-31"))
    ].iloc[0]

    assert ccc["non_missing_feature_count"] < config.strategy.minimum_non_missing_features
    assert pd.isna(ccc["composite_score"])
    assert not ccc["selected_top_n"]


def test_signal_selection_summary_counts_selected_names_by_date() -> None:
    """Selection summaries should reflect per-date scored and selected counts."""
    feature_panel = _build_feature_panel_fixture()
    config = load_signal_pipeline_config()
    reduced_config = replace(config, strategy=replace(config.strategy, selection_top_n=1))

    rankings, _ = build_signal_rankings(feature_panel, reduced_config)
    summary = build_signal_selection_summary(rankings)

    assert summary["selected_count"].tolist() == [1, 1]
    assert summary["scored_row_count"].tolist() == [3, 3]
