"""Focused tests for leakage-safe modeling baselines."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from src.models.baselines import run_baseline_model
from src.models.config import (
    ModelDateWindow,
    ModelFixedDateWindowsConfig,
    ModelWalkForwardConfig,
    load_model_pipeline_config,
)
from src.models.datasets import build_modeling_dataset
from src.models.labels import build_label_table
from src.models.preprocessing import fit_preprocessor, transform_features
from src.models.windows import build_model_folds


def _base_config():
    config = load_model_pipeline_config()
    return replace(
        config,
        label=replace(
            config.label,
            target_type="forward_excess_return_top_n_binary",
            horizon_months=1,
            benchmark="SPY",
            cross_sectional_top_n=2,
        ),
        dataset=replace(
            config.dataset,
            feature_columns=("ret_1m_lag1", "mom_3m", "pe_ratio_lag1"),
            minimum_non_missing_features=1,
        ),
        execution=replace(
            config.execution,
            selected_model="logistic_regression",
            random_state=7,
            append_experiment_registry=False,
        ),
    )


def _fixed_config():
    config = _base_config()
    return replace(
        config,
        splits=replace(
            config.splits,
            scheme="fixed_date_windows",
            fixed_date_windows=ModelFixedDateWindowsConfig(
                train=ModelDateWindow("2024-01-31", "2024-02-29"),
                validation=ModelDateWindow("2024-03-31", "2024-03-31"),
                test=ModelDateWindow("2024-04-30", "2024-04-30"),
            ),
        ),
        backtest=replace(config.backtest, prediction_splits=("validation", "test")),
    )


def _walk_forward_config():
    config = _base_config()
    return replace(
        config,
        splits=replace(
            config.splits,
            scheme="expanding_walk_forward",
            walk_forward=ModelWalkForwardConfig(
                min_train_periods=2,
                validation_window_periods=0,
                test_window_periods=1,
                step_periods=1,
            ),
        ),
        backtest=replace(config.backtest, prediction_splits=("test",)),
    )


def _monthly_panel_fixture() -> pd.DataFrame:
    benchmarks = {
        "2024-01-31": None,
        "2024-02-29": 0.03,
        "2024-03-31": 0.02,
        "2024-04-30": 0.015,
        "2024-05-31": 0.01,
    }
    returns = {
        "AAA": {"2024-01-31": None, "2024-02-29": 0.10, "2024-03-31": 0.07, "2024-04-30": 0.02, "2024-05-31": 0.00},
        "BBB": {"2024-01-31": None, "2024-02-29": 0.08, "2024-03-31": 0.06, "2024-04-30": 0.01, "2024-05-31": -0.01},
        "CCC": {"2024-01-31": None, "2024-02-29": -0.01, "2024-03-31": 0.01, "2024-04-30": 0.08, "2024-05-31": 0.06},
        "DDD": {"2024-01-31": None, "2024-02-29": -0.02, "2024-03-31": 0.00, "2024-04-30": 0.07, "2024-05-31": 0.05},
    }
    rows: list[dict[str, object]] = []
    for ticker, values in returns.items():
        for date, monthly_return in values.items():
            rows.append(
                {
                    "ticker": ticker,
                    "date": date,
                    "monthly_return": monthly_return,
                    "benchmark_ticker": "SPY",
                    "benchmark_return": benchmarks[date],
                    "sector": "Technology",
                    "industry": "Software",
                }
            )
    return pd.DataFrame(rows).assign(date=lambda frame: pd.to_datetime(frame["date"]))


def _feature_panel_fixture() -> pd.DataFrame:
    feature_templates = {
        "2024-01-31": {
            "AAA": (0.9, 0.8, 10.0),
            "BBB": (0.8, 0.7, 11.0),
            "CCC": (0.2, 0.1, 20.0),
            "DDD": (0.1, 0.2, 21.0),
        },
        "2024-02-29": {
            "AAA": (0.85, 0.75, 10.5),
            "BBB": (0.75, 0.65, 11.5),
            "CCC": (0.25, 0.15, 19.5),
            "DDD": (0.15, 0.25, 20.5),
        },
        "2024-03-31": {
            "AAA": (0.30, 0.35, 18.0),
            "BBB": (0.35, 0.30, 17.5),
            "CCC": (0.80, 0.85, 9.5),
            "DDD": (0.75, 0.80, 9.0),
        },
        "2024-04-30": {
            "AAA": (0.20, 0.25, 19.0),
            "BBB": (0.25, 0.20, 18.5),
            "CCC": (0.90, 0.88, 8.5),
            "DDD": (0.88, 0.90, 8.0),
        },
        "2024-05-31": {
            "AAA": (0.15, 0.20, 19.5),
            "BBB": (0.20, 0.15, 19.0),
            "CCC": (0.85, 0.82, 8.0),
            "DDD": (0.82, 0.85, 7.5),
        },
    }
    rows: list[dict[str, object]] = []
    for date, mapping in feature_templates.items():
        for ticker, values in mapping.items():
            rows.append(
                {
                    "ticker": ticker,
                    "date": date,
                    "benchmark_ticker": "SPY",
                    "sector": "Technology",
                    "industry": "Software",
                    "ret_1m_lag1": values[0],
                    "mom_3m": values[1],
                    "pe_ratio_lag1": values[2],
                }
            )
    return pd.DataFrame(rows).assign(date=lambda frame: pd.to_datetime(frame["date"]))


def _signal_rankings_fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    feature_panel = _feature_panel_fixture()
    for date, frame in feature_panel.groupby("date", sort=False):
        ranked = frame.sort_values(["ret_1m_lag1", "ticker"], ascending=[False, True]).reset_index(drop=True)
        for index, row in ranked.iterrows():
            rows.append(
                {
                    "ticker": row["ticker"],
                    "date": date,
                    "composite_score": 1.0 - index * 0.2,
                    "score_rank": float(index + 1),
                    "score_rank_pct": float(index + 1) / len(ranked),
                    "selected_top_n": bool(index < 2),
                }
            )
    return pd.DataFrame(rows)


def test_forward_label_alignment_uses_t_plus_1_realized_returns() -> None:
    """Labels should align decision date t to realized month-end t+1 outcomes."""
    config = _fixed_config()
    labels, metadata = build_label_table(_monthly_panel_fixture(), config.label)

    january = labels.loc[
        (labels["ticker"] == "AAA") & (labels["date"] == pd.Timestamp("2024-01-31"))
    ].iloc[0]
    january_negative = labels.loc[
        (labels["ticker"] == "DDD") & (labels["date"] == pd.Timestamp("2024-01-31"))
    ].iloc[0]

    assert january["realized_label_date"] == pd.Timestamp("2024-02-29")
    assert january["forward_raw_return"] == pytest.approx(0.10)
    assert january["forward_benchmark_return"] == pytest.approx(0.03)
    assert int(january["true_label"]) == 1
    assert int(january_negative["true_label"]) == 0
    assert metadata["target_type"] == "forward_excess_return_top_n_binary"


def test_duplicate_key_detection_raises_error() -> None:
    """Duplicate keys in upstream modeling inputs should fail clearly."""
    duplicate_feature_panel = pd.concat(
        [_feature_panel_fixture(), _feature_panel_fixture().iloc[[0]]],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="duplicate keys"):
        build_modeling_dataset(
            feature_panel=duplicate_feature_panel,
            monthly_panel=_monthly_panel_fixture(),
            config=_fixed_config(),
            signal_rankings=_signal_rankings_fixture(),
        )


def test_expanding_walk_forward_split_generation_is_strictly_chronological() -> None:
    """Expanding walk-forward folds should preserve chronology and unique held-out dates."""
    bundle = build_modeling_dataset(
        feature_panel=_feature_panel_fixture(),
        monthly_panel=_monthly_panel_fixture(),
        config=_walk_forward_config(),
        signal_rankings=_signal_rankings_fixture(),
    )

    folds = build_model_folds(bundle.dataset["date"], _walk_forward_config())

    assert [fold.fold_id for fold in folds] == ["fold_001", "fold_002"]
    assert [date.strftime("%Y-%m-%d") for date in folds[0].train_dates] == [
        "2024-01-31",
        "2024-02-29",
    ]
    assert [date.strftime("%Y-%m-%d") for date in folds[0].test_dates] == ["2024-03-31"]
    assert [date.strftime("%Y-%m-%d") for date in folds[1].train_dates] == [
        "2024-01-31",
        "2024-02-29",
        "2024-03-31",
    ]
    assert [date.strftime("%Y-%m-%d") for date in folds[1].test_dates] == ["2024-04-30"]
    assert folds[0].train_end_date < folds[0].test_start_date
    assert folds[1].train_end_date < folds[1].test_start_date


def test_preprocessing_fits_on_train_only_behavior() -> None:
    """Imputation and scaling statistics should come only from training rows."""
    config = _fixed_config()
    train_frame = pd.DataFrame(
        {
            "ret_1m_lag1": [1.0, 3.0],
            "mom_3m": [2.0, 4.0],
            "pe_ratio_lag1": [10.0, None],
        }
    )
    test_frame = pd.DataFrame(
        {
            "ret_1m_lag1": [1000.0],
            "mom_3m": [2000.0],
            "pe_ratio_lag1": [None],
        }
    )

    fitted = fit_preprocessor(
        train_frame,
        feature_columns=config.dataset.feature_columns,
        config=config,
    )
    transformed_test = transform_features(test_frame, fitted)

    assert fitted.pipeline.named_steps["imputer"].statistics_.tolist() == [2.0, 3.0, 10.0]
    assert fitted.pipeline.named_steps["scaler"].mean_.tolist() == [2.0, 3.0, 10.0]
    assert transformed_test.shape == (1, 3)


def test_logistic_regression_fixed_window_output_shape() -> None:
    """The fixed-window path should remain available for backward-compatible reruns."""
    config = _fixed_config()
    bundle = build_modeling_dataset(
        feature_panel=_feature_panel_fixture(),
        monthly_panel=_monthly_panel_fixture(),
        config=config,
        signal_rankings=_signal_rankings_fixture(),
    )

    artifacts = run_baseline_model(bundle.dataset, model_type="logistic_regression", config=config)

    assert len(artifacts.train_predictions) == 8
    assert len(artifacts.test_predictions) == 8
    assert set(artifacts.test_predictions["split"].unique()) == {"validation", "test"}
    assert set(artifacts.test_predictions["fold_id"].unique()) == {"fold_001"}
    assert {
        "ticker",
        "date",
        "realized_label_date",
        "true_label",
        "predicted_probability",
        "predicted_class",
        "split",
        "fold_id",
        "train_window_start",
        "train_window_end",
        "deterministic_composite_score",
        "deterministic_selected_top_n",
    }.issubset(artifacts.train_predictions.columns)


def test_walk_forward_aggregates_unique_out_of_sample_predictions() -> None:
    """Walk-forward runs should concatenate only unique out-of-sample rows across folds."""
    config = _walk_forward_config()
    bundle = build_modeling_dataset(
        feature_panel=_feature_panel_fixture(),
        monthly_panel=_monthly_panel_fixture(),
        config=config,
        signal_rankings=_signal_rankings_fixture(),
    )

    artifacts = run_baseline_model(bundle.dataset, model_type="logistic_regression", config=config)

    assert len(artifacts.train_predictions) == 20
    assert len(artifacts.test_predictions) == 8
    assert set(artifacts.test_predictions["split"].unique()) == {"test"}
    assert set(artifacts.test_predictions["fold_id"].unique()) == {"fold_001", "fold_002"}
    assert artifacts.test_predictions[["ticker", "date"]].duplicated().sum() == 0
    assert sorted(artifacts.test_predictions["date"].dt.strftime("%Y-%m-%d").unique().tolist()) == [
        "2024-03-31",
        "2024-04-30",
    ]
    assert artifacts.metadata["preprocessing"]["fit_window_count"] == 2
    assert len(artifacts.metadata["folds"]) == 2
    assert artifacts.metadata["out_of_sample_metrics"]["row_count"] == 8


def test_random_forest_walk_forward_output_shape() -> None:
    """Random forest should emit the same canonical fold-aware prediction structure."""
    config = replace(
        _walk_forward_config(),
        execution=replace(_walk_forward_config().execution, selected_model="random_forest"),
    )
    bundle = build_modeling_dataset(
        feature_panel=_feature_panel_fixture(),
        monthly_panel=_monthly_panel_fixture(),
        config=config,
        signal_rankings=_signal_rankings_fixture(),
    )

    artifacts = run_baseline_model(bundle.dataset, model_type="random_forest", config=config)

    assert len(artifacts.train_predictions) == 20
    assert len(artifacts.test_predictions) == 8
    assert artifacts.metadata["model_type"] == "random_forest"


def test_feature_importance_export_contains_all_features() -> None:
    """Feature-importance export should cover every configured model feature exactly once."""
    config = _walk_forward_config()
    bundle = build_modeling_dataset(
        feature_panel=_feature_panel_fixture(),
        monthly_panel=_monthly_panel_fixture(),
        config=config,
        signal_rankings=_signal_rankings_fixture(),
    )

    artifacts = run_baseline_model(bundle.dataset, model_type="logistic_regression", config=config)

    assert sorted(artifacts.feature_importance["feature"].tolist()) == sorted(
        config.dataset.feature_columns
    )
    assert artifacts.feature_importance["window_count"].tolist() == [2, 2, 2]
    assert set(artifacts.feature_importance["aggregation_method"].unique()) == {
        "mean_across_folds"
    }


def test_final_month_missing_label_is_dropped() -> None:
    """Rows without a future realized label should be excluded and counted in QC."""
    bundle = build_modeling_dataset(
        feature_panel=_feature_panel_fixture(),
        monthly_panel=_monthly_panel_fixture(),
        config=_walk_forward_config(),
        signal_rankings=_signal_rankings_fixture(),
    )

    assert pd.Timestamp("2024-05-31") not in set(bundle.dataset["date"])
    assert bundle.dropped_rows_summary["missing_label"] == 4
    assert bundle.dropped_rows_summary["missing_realized_label_date"] == 4
