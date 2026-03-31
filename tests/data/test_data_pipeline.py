"""Focused tests for data ingestion and monthly panel assembly."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import shutil
from uuid import uuid4

import pandas as pd
import pytest

from src.data.benchmarks import build_equal_weight_benchmark
from src.data.config import RawDataPaths, load_data_pipeline_config
from src.data.fundamentals_data import build_fundamentals_monthly
from src.data.io import build_raw_file_selection_manifest, read_tabular_files, select_input_files
from src.data.market_data import standardize_price_history
from src.data.panel_assembly import assemble_monthly_panel, validate_one_row_per_ticker_per_month
from src.data.standardize import assert_unique_keys, find_duplicate_keys
from src.utils.config import load_project_config


def test_monthly_resampling_logic_uses_last_observation_per_month() -> None:
    """Daily prices should collapse to one month-end row per ticker."""
    raw = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "AAA", "AAA"],
            "date": ["2024-01-03", "2024-01-31", "2024-02-15", "2024-02-29"],
            "adjusted_close": [10.0, 12.0, 13.0, 15.0],
            "volume": [100, 150, 175, 200],
        }
    )

    monthly = standardize_price_history(
        raw,
        dataset_name="test_prices",
        id_candidates=("ticker",),
        date_candidates=("date",),
        adjusted_close_candidates=("adjusted_close", "close"),
        allowed_identifiers={"AAA"},
        start_date="2024-01-01",
        end_date=None,
        output_id_column="ticker",
    )

    assert monthly["date"].dt.strftime("%Y-%m-%d").tolist() == ["2024-01-31", "2024-02-29"]
    assert monthly["adjusted_close"].tolist() == [12.0, 15.0]
    assert monthly["volume"].tolist() == [150, 200]


def test_monthly_return_calculation_uses_adjusted_close_pct_change() -> None:
    """Monthly returns should be adjusted_close_t / adjusted_close_t-1 - 1."""
    raw = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "AAA"],
            "date": ["2024-01-31", "2024-02-29", "2024-03-31"],
            "adjusted_close": [100.0, 110.0, 121.0],
        }
    )

    monthly = standardize_price_history(
        raw,
        dataset_name="test_prices",
        id_candidates=("ticker",),
        date_candidates=("date",),
        adjusted_close_candidates=("adjusted_close",),
        allowed_identifiers={"AAA"},
        start_date="2024-01-01",
        end_date=None,
        output_id_column="ticker",
    )

    assert pd.isna(monthly.loc[0, "monthly_return"])
    assert monthly.loc[1, "monthly_return"] == pytest.approx(0.10)
    assert monthly.loc[2, "monthly_return"] == pytest.approx(0.10)


def test_duplicate_key_detection_flags_repeated_ticker_dates() -> None:
    """Duplicate-key helpers should detect repeated ticker-month rows."""
    frame = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "AAA"],
            "date": pd.to_datetime(["2024-01-31", "2024-01-31", "2024-02-29"]),
            "adjusted_close": [10.0, 10.5, 11.0],
        }
    )

    duplicates = find_duplicate_keys(frame, ["ticker", "date"])
    assert len(duplicates) == 2
    with pytest.raises(ValueError):
        assert_unique_keys(frame, ["ticker", "date"], "test_frame")


def test_benchmark_alignment_joins_returns_by_date() -> None:
    """Panel assembly should align benchmark returns deterministically by month."""
    prices = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB", "BBB"],
            "date": pd.to_datetime(["2024-01-31", "2024-02-29", "2024-01-31", "2024-02-29"]),
            "adjusted_close": [100.0, 110.0, 50.0, 55.0],
            "monthly_return": [pd.NA, 0.10, pd.NA, 0.10],
        }
    )
    fundamentals = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB", "BBB"],
            "date": pd.to_datetime(["2024-01-31", "2024-02-29", "2024-01-31", "2024-02-29"]),
            "sector": ["Tech", "Tech", "Health", "Health"],
            "industry": ["Software", "Software", "Biotech", "Biotech"],
            "market_cap": [1.0, 1.1, 2.0, 2.1],
        }
    )
    benchmarks = pd.DataFrame(
        {
            "benchmark_ticker": ["SPY", "SPY"],
            "date": pd.to_datetime(["2024-01-31", "2024-02-29"]),
            "adjusted_close": [400.0, 408.0],
            "monthly_return": [pd.NA, 0.02],
        }
    )

    panel = assemble_monthly_panel(
        prices,
        fundamentals,
        benchmarks,
        universe_tickers=("AAA", "BBB"),
        primary_benchmark="SPY",
    )

    february = panel.loc[panel["date"] == pd.Timestamp("2024-02-29"), "benchmark_return"]
    assert february.tolist() == [0.02, 0.02]


def test_one_row_per_ticker_per_month_validation_rejects_incomplete_grid() -> None:
    """Canonical panel validation should fail when the ticker-month grid is incomplete."""
    panel = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB"],
            "date": pd.to_datetime(["2024-01-31", "2024-02-29", "2024-01-31"]),
        }
    )

    with pytest.raises(ValueError):
        validate_one_row_per_ticker_per_month(
            panel,
            expected_tickers=("AAA", "BBB"),
            expected_dates=pd.DatetimeIndex(
                [pd.Timestamp("2024-01-31"), pd.Timestamp("2024-02-29")]
            ),
        )


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_fundamentals_to_month_merge_uses_effective_lag_rule() -> None:
    """Quarterly fundamentals should appear only after the configured lag month."""
    config = load_data_pipeline_config()
    raw_root = REPO_ROOT / "tests" / "data" / "runtime_raw"
    shutil.rmtree(raw_root, ignore_errors=True)
    market_dir = raw_root / "market"
    benchmarks_dir = raw_root / "benchmarks"
    fundamentals_dir = raw_root / "fundamentals"
    for directory in (market_dir, benchmarks_dir, fundamentals_dir):
        directory.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "report_date": ["2023-12-31", "2024-03-31"],
            "sector": ["Tech", "Tech"],
            "industry": ["Software", "Software"],
            "market_cap": [100.0, 120.0],
            "pe_ratio": [20.0, 22.0],
        }
    ).to_csv(fundamentals_dir / "fundamentals.csv", index=False)

    test_config = replace(
        config,
        raw=RawDataPaths(
            root_dir=raw_root,
            market_dir=market_dir,
            fundamentals_dir=fundamentals_dir,
            benchmarks_dir=benchmarks_dir,
            file_patterns=("*.csv",),
        ),
        project=replace(
            config.project,
            execution=load_project_config(execution_mode="research_scale").execution,
            universe=replace(
                config.project.universe,
                tech_tickers=("AAA",),
                comparison_tickers=(),
            ),
        ),
    )

    try:
        monthly = build_fundamentals_monthly(
            test_config,
            monthly_dates=pd.Series(pd.to_datetime(["2024-01-31", "2024-02-29", "2024-05-31"])),
        )

        january = monthly.loc[monthly["date"] == pd.Timestamp("2024-01-31"), "market_cap"].iloc[0]
        february = monthly.loc[monthly["date"] == pd.Timestamp("2024-02-29"), "market_cap"].iloc[0]
        may = monthly.loc[monthly["date"] == pd.Timestamp("2024-05-31"), "market_cap"].iloc[0]

        assert pd.isna(january)
        assert february == pytest.approx(100.0)
        assert may == pytest.approx(120.0)
    finally:
        shutil.rmtree(raw_root, ignore_errors=True)


def test_equal_weight_benchmark_averages_constituent_returns() -> None:
    """The equal-weight benchmark should average constituent monthly returns by date."""
    prices = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "AAA", "BBB"],
            "date": pd.to_datetime(["2024-01-31", "2024-01-31", "2024-02-29", "2024-02-29"]),
            "adjusted_close": [100.0, 200.0, 110.0, 220.0],
            "monthly_return": [pd.NA, pd.NA, 0.10, 0.10],
        }
    )

    equal_weight = build_equal_weight_benchmark(
        prices, benchmark_id="equal_weight_universe", start_value=100.0
    )

    assert equal_weight.loc[1, "monthly_return"] == pytest.approx(0.10)
    assert equal_weight.loc[1, "adjusted_close"] == pytest.approx(110.0)


def test_research_scale_raw_file_selection_prefers_non_sample_files() -> None:
    """Research-scale mode should prefer broader non-sample files when they exist locally."""
    raw_dir = REPO_ROOT / ".tmp" / f"research_scale_prefers_{uuid4().hex}" / "market"
    raw_dir.mkdir(parents=True, exist_ok=True)
    try:
        (raw_dir / "prices_daily_sample.csv").write_text(
            "ticker,date,adjusted_close\n",
            encoding="utf-8",
        )
        (raw_dir / "prices_daily_full.csv").write_text(
            "ticker,date,adjusted_close\n",
            encoding="utf-8",
        )

        execution = load_project_config(execution_mode="research_scale").execution
        selected = select_input_files(raw_dir, ("*.csv",), execution=execution)
        manifest = build_raw_file_selection_manifest(raw_dir, ("*.csv",), execution=execution)

        assert [path.name for path in selected] == ["prices_daily_full.csv"]
        assert manifest.selected_source_kind == "broader_local_raw"
        assert manifest.broader_raw_files_available is True
        assert manifest.used_seeded_sample_fallback is False
    finally:
        shutil.rmtree(raw_dir.parent, ignore_errors=True)


def test_research_scale_raw_file_selection_falls_back_to_sample_files() -> None:
    """Research-scale mode should degrade gracefully to the seeded sample files when needed."""
    raw_dir = REPO_ROOT / ".tmp" / f"research_scale_fallback_{uuid4().hex}" / "market"
    raw_dir.mkdir(parents=True, exist_ok=True)
    try:
        (raw_dir / "prices_daily_sample.csv").write_text(
            "ticker,date,adjusted_close\n",
            encoding="utf-8",
        )

        execution = load_project_config(execution_mode="research_scale").execution
        selected = select_input_files(raw_dir, ("*.csv",), execution=execution)
        manifest = build_raw_file_selection_manifest(raw_dir, ("*.csv",), execution=execution)

        assert [path.name for path in selected] == ["prices_daily_sample.csv"]
        assert manifest.selected_source_kind == "seeded_sample_fallback"
        assert manifest.broader_raw_files_available is False
        assert manifest.used_seeded_sample_fallback is True
    finally:
        shutil.rmtree(raw_dir.parent, ignore_errors=True)


def test_research_scale_ignores_headerless_empty_non_sample_csvs() -> None:
    """Research-scale mode should ignore unusable empty non-sample CSVs and preserve fallback."""
    raw_dir = REPO_ROOT / ".tmp" / f"research_scale_empty_non_sample_{uuid4().hex}" / "market"
    raw_dir.mkdir(parents=True, exist_ok=True)
    try:
        (raw_dir / "prices_daily_sample.csv").write_text(
            "ticker,date,adjusted_close\nAAA,2024-01-31,10.0\n",
            encoding="utf-8",
        )
        (raw_dir / "prices_daily_full.csv").write_text("\n", encoding="utf-8")

        execution = load_project_config(execution_mode="research_scale").execution
        selected = select_input_files(raw_dir, ("*.csv",), execution=execution)
        manifest = build_raw_file_selection_manifest(raw_dir, ("*.csv",), execution=execution)

        assert [path.name for path in selected] == ["prices_daily_sample.csv"]
        assert manifest.selected_source_kind == "seeded_sample_fallback"
        assert manifest.broader_raw_files_available is False
        assert manifest.used_seeded_sample_fallback is True
    finally:
        shutil.rmtree(raw_dir.parent, ignore_errors=True)


def test_read_tabular_files_records_selected_file_provenance_and_observed_coverage() -> None:
    """Loaded raw-file manifests should include per-file metadata and observed coverage."""
    raw_dir = REPO_ROOT / ".tmp" / f"raw_manifest_observed_{uuid4().hex}" / "market"
    raw_dir.mkdir(parents=True, exist_ok=True)
    try:
        sample_path = raw_dir / "prices_daily_sample.csv"
        sample_path.write_text(
            "\n".join(
                [
                    "ticker,date,adjusted_close",
                    "AAA,2024-01-02,10.0",
                    "AAA,2024-02-29,11.0",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        execution = load_project_config(execution_mode="research_scale").execution
        loaded = read_tabular_files(raw_dir, ("*.csv",), execution=execution)
        manifest = loaded.attrs["raw_file_selection_manifest"]
        detail = manifest["selected_file_details"][0]

        assert manifest["selected_source_kind"] == "seeded_sample_fallback"
        assert manifest["observed_total_row_count"] == 2
        assert manifest["observed_date_columns"] == ["date"]
        assert manifest["observed_min_date"] == "2024-01-02"
        assert manifest["observed_max_date"] == "2024-02-29"
        assert detail["file_name"] == sample_path.name
        assert detail["source_kind"] == "sample"
        assert detail["file_size_bytes"] > 0
        assert detail["last_modified_utc"].endswith("+00:00")
        assert detail["observed_row_count"] == 2
        assert detail["observed_column_count"] == 3
        assert detail["observed_columns"] == ["ticker", "date", "adjusted_close"]
        assert detail["observed_date_columns"] == [
            {
                "column": "date",
                "non_null_count": 2,
                "min_date": "2024-01-02",
                "max_date": "2024-02-29",
            }
        ]
    finally:
        shutil.rmtree(raw_dir.parent, ignore_errors=True)
