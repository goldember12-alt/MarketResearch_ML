"""Focused tests for deterministic monthly backtesting."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from src.backtest.config import load_backtest_pipeline_config
from src.backtest.holdings import build_holdings_history
from src.backtest.metrics import compute_max_drawdown
from src.backtest.returns import build_benchmark_returns, build_portfolio_returns
from src.backtest.trades import build_trade_log


def _signal_rankings_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [
                "AAA",
                "BBB",
                "CCC",
                "AAA",
                "BBB",
                "CCC",
                "AAA",
                "BBB",
                "CCC",
                "AAA",
                "BBB",
                "CCC",
            ],
            "date": pd.to_datetime(
                [
                    "2024-01-31",
                    "2024-01-31",
                    "2024-01-31",
                    "2024-02-29",
                    "2024-02-29",
                    "2024-02-29",
                    "2024-03-31",
                    "2024-03-31",
                    "2024-03-31",
                    "2024-04-30",
                    "2024-04-30",
                    "2024-04-30",
                ]
            ),
            "sector": ["Technology"] * 12,
            "industry": ["Software"] * 12,
            "composite_score": [0.9, 0.8, 0.1, 0.1, 0.95, 0.85, None, None, None, 0.7, 0.2, 0.1],
            "score_rank": [1.0, 2.0, 3.0, 3.0, 1.0, 2.0, None, None, None, 1.0, 2.0, 3.0],
            "selected_top_n": [
                True,
                True,
                False,
                False,
                True,
                True,
                False,
                False,
                False,
                True,
                True,
                False,
            ],
        }
    )


def _monthly_panel_fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    returns_by_date = {
        "2024-02-29": {"AAA": 0.10, "BBB": 0.00, "CCC": -0.05},
        "2024-03-31": {"AAA": 0.02, "BBB": 0.03, "CCC": 0.06},
        "2024-04-30": {"AAA": -0.10, "BBB": 0.01, "CCC": 0.02},
        "2024-05-31": {"AAA": 0.04, "BBB": 0.05, "CCC": 0.03},
    }
    for date, mapping in returns_by_date.items():
        for ticker, monthly_return in mapping.items():
            rows.append({"ticker": ticker, "date": date, "monthly_return": monthly_return})
    return pd.DataFrame(rows).assign(date=lambda frame: pd.to_datetime(frame["date"]))


def _benchmarks_fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    values = {
        "SPY": {
            "2024-02-29": 0.03,
            "2024-03-31": 0.02,
            "2024-04-30": -0.01,
            "2024-05-31": 0.04,
        },
        "QQQ": {
            "2024-02-29": 0.04,
            "2024-03-31": 0.03,
            "2024-04-30": -0.02,
            "2024-05-31": 0.05,
        },
        "equal_weight_universe": {
            "2024-02-29": 0.015,
            "2024-03-31": 0.025,
            "2024-04-30": 0.00,
            "2024-05-31": 0.035,
        },
    }
    for benchmark_ticker, mapping in values.items():
        for date, monthly_return in mapping.items():
            rows.append(
                {
                    "benchmark_ticker": benchmark_ticker,
                    "date": date,
                    "monthly_return": monthly_return,
                }
            )
    return pd.DataFrame(rows).assign(date=lambda frame: pd.to_datetime(frame["date"]))


def _build_config(**portfolio_overrides):
    config = load_backtest_pipeline_config()
    return replace(config, portfolio=replace(config.portfolio, selected_top_n=2, **portfolio_overrides))


def _build_pipeline_outputs(config=None):
    resolved_config = config or _build_config()
    holdings_history, rebalance_summary = build_holdings_history(
        _signal_rankings_fixture(), resolved_config
    )
    trade_log, turnover_summary = build_trade_log(holdings_history, rebalance_summary)
    portfolio_returns, holding_return_details = build_portfolio_returns(
        holdings_history,
        rebalance_summary,
        _monthly_panel_fixture(),
        turnover_summary,
        resolved_config,
    )
    benchmark_returns = build_benchmark_returns(
        _benchmarks_fixture(),
        portfolio_returns,
        resolved_config,
    )
    return (
        holdings_history,
        rebalance_summary,
        trade_log,
        turnover_summary,
        portfolio_returns,
        holding_return_details,
        benchmark_returns,
    )


def test_build_holdings_history_allocates_equal_weight_selected_names() -> None:
    """Selected names should receive equal weights when fully invested."""
    holdings_history, rebalance_summary = build_holdings_history(
        _signal_rankings_fixture(),
        _build_config(),
    )

    january = holdings_history.loc[holdings_history["date"] == pd.Timestamp("2024-01-31")]

    assert january["ticker"].tolist() == ["AAA", "BBB"]
    assert january["portfolio_weight"].tolist() == [0.5, 0.5]
    assert january["holding_period_end"].unique().tolist() == [pd.Timestamp("2024-02-29")]
    assert rebalance_summary.loc[
        rebalance_summary["rebalance_date"] == pd.Timestamp("2024-01-31"), "cash_weight"
    ].iloc[0] == pytest.approx(0.0)


def test_build_holdings_history_supports_capped_weight_with_cash_residual() -> None:
    """Capped weights can leave explicit residual cash when configured."""
    config = _build_config(weighting_scheme="capped_weight", max_weight=0.40, cash_handling_policy="hold_cash")
    holdings_history, rebalance_summary = build_holdings_history(_signal_rankings_fixture(), config)

    january = holdings_history.loc[holdings_history["date"] == pd.Timestamp("2024-01-31")]

    assert january["portfolio_weight"].tolist() == [pytest.approx(0.4), pytest.approx(0.4)]
    assert rebalance_summary.loc[
        rebalance_summary["rebalance_date"] == pd.Timestamp("2024-01-31"), "cash_weight"
    ].iloc[0] == pytest.approx(0.2)


def test_build_portfolio_returns_uses_next_period_return_alignment() -> None:
    """Holdings formed on t should earn realized returns observed on t+1."""
    _, _, _, _, portfolio_returns, _, _ = _build_pipeline_outputs()

    first_period = portfolio_returns.iloc[0]

    assert first_period["formation_date"] == pd.Timestamp("2024-01-31")
    assert first_period["date"] == pd.Timestamp("2024-02-29")
    assert first_period["portfolio_gross_return"] == pytest.approx(0.05)


def test_build_trade_log_and_turnover_capture_entries_and_exits() -> None:
    """Trade log should show exits and entries with turnover on rebalance."""
    _, _, trade_log, turnover_summary, portfolio_returns, _, _ = _build_pipeline_outputs()

    february_trades = trade_log.loc[trade_log["rebalance_date"] == pd.Timestamp("2024-02-29")]
    march_realized = portfolio_returns.loc[portfolio_returns["date"] == pd.Timestamp("2024-03-31")].iloc[0]

    assert february_trades["ticker"].tolist() == ["AAA", "CCC"]
    assert february_trades["trade_type"].tolist() == ["exit", "entry"]
    assert turnover_summary.loc[
        turnover_summary["rebalance_date"] == pd.Timestamp("2024-02-29"), "turnover"
    ].iloc[0] == pytest.approx(0.5)
    assert march_realized["turnover"] == pytest.approx(0.5)


def test_transaction_cost_application_reduces_net_return() -> None:
    """Configured transaction costs should reduce realized net returns."""
    config = replace(
        _build_config(),
        costs=replace(load_backtest_pipeline_config().costs, transaction_cost_bps=100.0, slippage_bps=0.0),
    )
    _, _, _, _, portfolio_returns, _, _ = _build_pipeline_outputs(config)

    first_period = portfolio_returns.iloc[0]

    assert first_period["transaction_cost"] == pytest.approx(0.01)
    assert first_period["portfolio_net_return"] == pytest.approx(0.04)


def test_build_benchmark_returns_aligns_to_portfolio_dates() -> None:
    """Configured benchmarks should align to the same realized portfolio dates."""
    _, _, _, _, portfolio_returns, _, benchmark_returns = _build_pipeline_outputs()

    expected_dates = portfolio_returns["date"].tolist()
    for benchmark_ticker, frame in benchmark_returns.groupby("benchmark_ticker", sort=True):
        assert frame["date"].tolist() == expected_dates
        assert benchmark_ticker in {"SPY", "QQQ", "equal_weight_universe"}


def test_compute_max_drawdown_returns_peak_to_trough_loss() -> None:
    """Max drawdown should reflect the worst peak-to-trough decline."""
    returns = pd.Series([0.10, -0.20, 0.05])
    assert compute_max_drawdown(returns) == pytest.approx(-0.20)


def test_duplicate_signal_keys_raise_clear_error() -> None:
    """Duplicate ticker-date keys should fail before holdings are constructed."""
    rankings = pd.concat([_signal_rankings_fixture(), _signal_rankings_fixture().iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicate keys"):
        build_holdings_history(rankings, _build_config())


def test_empty_selected_month_becomes_cash_only_period() -> None:
    """A month with no selected holdings should still produce a valid cash-only period."""
    _, rebalance_summary, _, _, portfolio_returns, _, _ = _build_pipeline_outputs()

    march_snapshot = rebalance_summary.loc[
        rebalance_summary["rebalance_date"] == pd.Timestamp("2024-03-31")
    ].iloc[0]
    april_period = portfolio_returns.loc[portfolio_returns["date"] == pd.Timestamp("2024-04-30")].iloc[0]

    assert march_snapshot["selected_count"] == 0
    assert march_snapshot["cash_weight"] == pytest.approx(1.0)
    assert april_period["holding_count"] == 0
    assert april_period["portfolio_gross_return"] == pytest.approx(0.0)
