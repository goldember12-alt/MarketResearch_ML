"""Focused tests for remote raw-data acquisition config and pure transforms."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from src.data.alphavantage import parse_monthly_adjusted_response, parse_overview_response
from src.data.remote_config import load_remote_raw_fetch_config
from src.data.remote_io import (
    build_dataset_manifest,
    resolve_dataset_output_targets,
    write_dataset_manifest,
)
from src.data.sec_companyfacts import (
    build_ticker_cik_map,
    map_companyfacts_to_quarterly_fundamentals,
    resolve_sec_user_agent,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_remote_raw_fetch_config_loads_default_provider_and_output_targets() -> None:
    """Remote fetch config should resolve provider defaults and raw-data output roots."""
    config = load_remote_raw_fetch_config(execution_mode="research_scale")

    assert config.acquisition.default_provider == "alphavantage_sec"
    assert config.acquisition.latest_file_overwrite_policy == "overwrite"
    assert config.project.execution.mode_name == "research_scale"
    assert config.outputs.market.latest_filename == "prices_monthly_alphavantage.csv"
    assert config.outputs.market.base_dir == REPO_ROOT / "data" / "raw" / "market"
    assert (
        config.outputs.overview.base_dir == REPO_ROOT / "data" / "raw" / "fundamentals" / "metadata"
    )
    assert config.outputs.fundamentals.base_dir == REPO_ROOT / "data" / "raw" / "fundamentals"


def test_resolve_dataset_output_targets_builds_latest_snapshot_and_manifest_paths() -> None:
    """Output targets should place manifests and immutable snapshots in deterministic locations."""
    base_dir = REPO_ROOT / ".tmp" / f"remote_targets_{uuid4().hex}"
    targets = resolve_dataset_output_targets(
        base_dir=base_dir,
        latest_filename="prices_monthly_alphavantage.csv",
        snapshot_subdir=base_dir / "snapshots",
        snapshot_filename_template="prices_monthly_alphavantage_{timestamp}.csv",
        manifest_subdir=base_dir / "manifests",
        latest_manifest_filename="prices_monthly_alphavantage_manifest.json",
        timestamp_token="20260330T120000Z",
    )

    assert targets.latest_path == base_dir / "prices_monthly_alphavantage.csv"
    assert targets.snapshot_path == (
        base_dir / "snapshots" / "prices_monthly_alphavantage_20260330T120000Z.csv"
    )
    assert (
        targets.manifest_path
        == base_dir / "manifests" / "prices_monthly_alphavantage_manifest.json"
    )


def test_build_dataset_manifest_and_write_json_roundtrip() -> None:
    """Dataset manifests should persist the required provenance fields as JSON."""
    manifest_dir = REPO_ROOT / ".tmp" / f"remote_manifest_{uuid4().hex}"
    manifest_path = manifest_dir / "prices_manifest.json"
    try:
        manifest = build_dataset_manifest(
            dataset_name="market_prices",
            provider="alphavantage",
            endpoint="https://www.alphavantage.co/query",
            function="TIME_SERIES_MONTHLY_ADJUSTED",
            requested_symbols=["AAPL", "MSFT"],
            completed_symbols=["AAPL"],
            failed_symbols=["MSFT"],
            throttle_detected=True,
            partial_failure=True,
            fetch_started_at_utc="2026-03-30T12:00:00+00:00",
            fetch_completed_at_utc="2026-03-30T12:00:05+00:00",
            output_files=["data/raw/market/prices_monthly_alphavantage.csv"],
            row_count=120,
            min_date="2015-01-31",
            max_date="2026-02-28",
            notes=["MSFT: Alpha Vantage rate limit"],
        )
        write_dataset_manifest(manifest, manifest_path)

        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert loaded["dataset_name"] == "market_prices"
        assert loaded["requested_symbols"] == ["AAPL", "MSFT"]
        assert loaded["failed_symbols"] == ["MSFT"]
        assert loaded["throttle_detected"] is True
    finally:
        shutil.rmtree(manifest_dir, ignore_errors=True)


def test_parse_monthly_adjusted_response_returns_sorted_numeric_frame() -> None:
    """Monthly adjusted Alpha Vantage payloads should become sorted numeric rows."""
    payload = {
        "Meta Data": {"2. Symbol": "AAPL"},
        "Monthly Adjusted Time Series": {
            "2026-02-28": {
                "1. open": "10.0",
                "2. high": "12.0",
                "3. low": "9.5",
                "4. close": "11.0",
                "5. adjusted close": "11.0",
                "6. volume": "100",
                "7. dividend amount": "0.1",
                "8. split coefficient": "1.0",
            },
            "2026-01-31": {
                "1. open": "9.0",
                "2. high": "10.0",
                "3. low": "8.5",
                "4. close": "9.5",
                "5. adjusted close": "9.5",
                "6. volume": "90",
                "7. dividend amount": "0.0",
                "8. split coefficient": "1.0",
            },
        },
    }

    frame = parse_monthly_adjusted_response(
        payload,
        symbol="AAPL",
        identifier_column="ticker",
        source_function="TIME_SERIES_MONTHLY_ADJUSTED",
    )

    assert frame["ticker"].tolist() == ["AAPL", "AAPL"]
    assert frame["date"].dt.strftime("%Y-%m-%d").tolist() == ["2026-01-31", "2026-02-28"]
    assert frame["adjusted_close"].tolist() == [9.5, 11.0]
    assert frame["source_function"].unique().tolist() == ["TIME_SERIES_MONTHLY_ADJUSTED"]


def test_parse_overview_response_keeps_sector_and_industry_snapshot_fields() -> None:
    """Overview payloads should preserve classification metadata for later enrichment."""
    row = parse_overview_response(
        {
            "Symbol": "AAPL",
            "Sector": "Technology",
            "Industry": "Consumer Electronics",
            "MarketCapitalization": "100",
            "LatestQuarter": "2025-12-31",
        },
        symbol="AAPL",
    )

    assert row["ticker"] == "AAPL"
    assert row["sector"] == "Technology"
    assert row["industry"] == "Consumer Electronics"
    assert row["market_capitalization_snapshot"] == "100"


def test_build_ticker_cik_map_zero_pads_ciks() -> None:
    """SEC ticker lookup parsing should return zero-padded CIK strings."""
    mapping = build_ticker_cik_map(
        {
            "0": {"ticker": "AAPL", "cik_str": 320193},
            "1": {"ticker": "MSFT", "cik_str": 789019},
        }
    )

    assert mapping == {
        "AAPL": "0000320193",
        "MSFT": "0000789019",
    }


def test_resolve_sec_user_agent_supports_explicit_or_contact_email_env_vars() -> None:
    """SEC identity should resolve from env-vars only, either directly or by composition."""
    provider = load_remote_raw_fetch_config().sec

    explicit = resolve_sec_user_agent(
        provider=provider,
        environment={provider.user_agent_env_var: "Custom Agent test@example.com"},
    )
    composed = resolve_sec_user_agent(
        provider=provider,
        environment={provider.contact_email_env_var: "test@example.com"},
    )

    assert explicit == "Custom Agent test@example.com"
    assert composed == "MarketResearch_ML (test@example.com)"


def test_map_companyfacts_to_quarterly_fundamentals_builds_conservative_subset() -> None:
    """SEC Company Facts mapping should derive ratios and preserve report dates."""
    payload = {
        "facts": {
            "us-gaap": {
                "Assets": {
                    "units": {
                        "USD": [
                            {
                                "end": "2024-03-31",
                                "filed": "2024-05-01",
                                "form": "10-Q",
                                "val": 1000,
                            },
                            {
                                "end": "2024-06-30",
                                "filed": "2024-08-01",
                                "form": "10-Q",
                                "val": 1100,
                            },
                        ]
                    }
                },
                "StockholdersEquity": {
                    "units": {
                        "USD": [
                            {
                                "end": "2024-03-31",
                                "filed": "2024-05-01",
                                "form": "10-Q",
                                "val": 400,
                            },
                            {
                                "end": "2024-06-30",
                                "filed": "2024-08-01",
                                "form": "10-Q",
                                "val": 420,
                            },
                        ]
                    }
                },
                "AssetsCurrent": {
                    "units": {
                        "USD": [
                            {
                                "end": "2024-03-31",
                                "filed": "2024-05-01",
                                "form": "10-Q",
                                "val": 300,
                            },
                            {
                                "end": "2024-06-30",
                                "filed": "2024-08-01",
                                "form": "10-Q",
                                "val": 330,
                            },
                        ]
                    }
                },
                "LiabilitiesCurrent": {
                    "units": {
                        "USD": [
                            {
                                "end": "2024-03-31",
                                "filed": "2024-05-01",
                                "form": "10-Q",
                                "val": 150,
                            },
                            {
                                "end": "2024-06-30",
                                "filed": "2024-08-01",
                                "form": "10-Q",
                                "val": 165,
                            },
                        ]
                    }
                },
                "DebtLongtermAndShorttermCombinedAmount": {
                    "units": {
                        "USD": [
                            {
                                "end": "2024-03-31",
                                "filed": "2024-05-01",
                                "form": "10-Q",
                                "val": 100,
                            },
                            {
                                "end": "2024-06-30",
                                "filed": "2024-08-01",
                                "form": "10-Q",
                                "val": 110,
                            },
                        ]
                    }
                },
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": [
                            {
                                "start": "2024-01-01",
                                "end": "2024-03-31",
                                "filed": "2024-05-01",
                                "form": "10-Q",
                                "fp": "Q1",
                                "frame": "CY2024Q1I",
                                "val": 200,
                            },
                            {
                                "start": "2024-04-01",
                                "end": "2024-06-30",
                                "filed": "2024-08-01",
                                "form": "10-Q",
                                "fp": "Q2",
                                "frame": "CY2024Q2I",
                                "val": 220,
                            },
                        ]
                    }
                },
                "GrossProfit": {
                    "units": {
                        "USD": [
                            {
                                "start": "2024-01-01",
                                "end": "2024-03-31",
                                "filed": "2024-05-01",
                                "form": "10-Q",
                                "fp": "Q1",
                                "frame": "CY2024Q1I",
                                "val": 80,
                            },
                            {
                                "start": "2024-04-01",
                                "end": "2024-06-30",
                                "filed": "2024-08-01",
                                "form": "10-Q",
                                "fp": "Q2",
                                "frame": "CY2024Q2I",
                                "val": 88,
                            },
                        ]
                    }
                },
                "OperatingIncomeLoss": {
                    "units": {
                        "USD": [
                            {
                                "start": "2024-01-01",
                                "end": "2024-03-31",
                                "filed": "2024-05-01",
                                "form": "10-Q",
                                "fp": "Q1",
                                "frame": "CY2024Q1I",
                                "val": 50,
                            },
                            {
                                "start": "2024-04-01",
                                "end": "2024-06-30",
                                "filed": "2024-08-01",
                                "form": "10-Q",
                                "fp": "Q2",
                                "frame": "CY2024Q2I",
                                "val": 55,
                            },
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            {
                                "start": "2024-01-01",
                                "end": "2024-03-31",
                                "filed": "2024-05-01",
                                "form": "10-Q",
                                "fp": "Q1",
                                "frame": "CY2024Q1I",
                                "val": 40,
                            },
                            {
                                "start": "2024-04-01",
                                "end": "2024-06-30",
                                "filed": "2024-08-01",
                                "form": "10-Q",
                                "fp": "Q2",
                                "frame": "CY2024Q2I",
                                "val": 44,
                            },
                        ]
                    }
                },
                "EarningsPerShareDiluted": {
                    "units": {
                        "USD/shares": [
                            {
                                "start": "2024-01-01",
                                "end": "2024-03-31",
                                "filed": "2024-05-01",
                                "form": "10-Q",
                                "fp": "Q1",
                                "frame": "CY2024Q1I",
                                "val": 2.0,
                            },
                            {
                                "start": "2024-04-01",
                                "end": "2024-06-30",
                                "filed": "2024-08-01",
                                "form": "10-Q",
                                "fp": "Q2",
                                "frame": "CY2024Q2I",
                                "val": 2.2,
                            },
                        ]
                    }
                },
            }
        }
    }

    frame = map_companyfacts_to_quarterly_fundamentals(
        payload,
        ticker="AAPL",
        sector="Technology",
        industry="Consumer Electronics",
    )

    assert frame["ticker"].tolist() == ["AAPL", "AAPL"]
    assert frame["report_date"].dt.strftime("%Y-%m-%d").tolist() == ["2024-03-31", "2024-06-30"]
    assert frame["sector"].tolist() == ["Technology", "Technology"]
    assert frame["gross_margin"].tolist() == [0.4, 0.4]
    assert frame["operating_margin"].tolist() == [0.25, 0.25]
    assert frame["roa"].tolist() == [0.04, 0.04]
    assert frame["debt_to_equity"].tolist() == [0.25, pytest.approx(110 / 420)]
    assert frame["current_ratio"].tolist() == [2.0, 2.0]
