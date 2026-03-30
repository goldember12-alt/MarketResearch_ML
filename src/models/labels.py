"""Forward-return label construction for the modeling-baselines stage."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.data.standardize import assert_unique_keys
from src.models.config import ModelLabelConfig


def _compound_forward_return(series: pd.Series, horizon_months: int) -> pd.Series:
    """Compound realized returns from t+1 through t+h for each row."""
    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype="float64", copy=False)
    output = np.full(len(values), np.nan, dtype="float64")

    for idx in range(len(values)):
        start = idx + 1
        stop = start + horizon_months
        if stop > len(values):
            continue
        window = values[start:stop]
        if np.isnan(window).any():
            continue
        output[idx] = float(np.prod(1.0 + window) - 1.0)

    return pd.Series(output, index=series.index, dtype="float64")


def _build_top_n_binary_label(
    frame: pd.DataFrame,
    *,
    value_column: str,
    top_n: int,
) -> pd.DataFrame:
    """Assign a 1/0 label for the top-N future outcomes within each decision month."""
    ranked_frames: list[pd.DataFrame] = []
    for _, month_frame in frame.groupby("date", sort=False):
        ranked = month_frame.copy()
        ranked["label_rank"] = np.nan
        ranked["true_label"] = pd.Series(pd.NA, index=ranked.index, dtype="Int64")

        available = ranked[ranked[value_column].notna()].copy()
        if not available.empty:
            available = available.sort_values(
                [value_column, "ticker"],
                ascending=[False, True],
                na_position="last",
            ).reset_index(drop=True)
            available["label_rank"] = np.arange(1, len(available) + 1, dtype=float)
            available["true_label"] = (available["label_rank"] <= top_n).astype("Int64")
            ranked = ranked.drop(columns=["label_rank", "true_label"]).merge(
                available[["ticker", "label_rank", "true_label"]],
                on="ticker",
                how="left",
            )
        ranked_frames.append(ranked)

    return pd.concat(ranked_frames, ignore_index=True)


def _build_threshold_binary_label(
    frame: pd.DataFrame,
    *,
    value_column: str,
    threshold: float,
) -> pd.DataFrame:
    """Assign a threshold-based 1/0 label from a forward-return column."""
    labeled = frame.copy()
    labeled["label_rank"] = np.nan
    labeled["true_label"] = pd.Series(pd.NA, index=labeled.index, dtype="Int64")
    mask = labeled[value_column].notna()
    labeled.loc[mask, "true_label"] = (labeled.loc[mask, value_column] > threshold).astype("Int64")
    return labeled


def build_label_table(
    monthly_panel: pd.DataFrame,
    config: ModelLabelConfig,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build the modeling label table keyed by ticker and decision date."""
    assert_unique_keys(monthly_panel, ["ticker", "date"], "monthly_panel")

    panel = monthly_panel.copy().sort_values(["ticker", "date"]).reset_index(drop=True)
    panel["forward_raw_return"] = panel.groupby("ticker", sort=False)["monthly_return"].transform(
        lambda series: _compound_forward_return(series, config.horizon_months)
    )
    panel["forward_benchmark_return"] = panel.groupby("ticker", sort=False)[
        "benchmark_return"
    ].transform(lambda series: _compound_forward_return(series, config.horizon_months))
    panel["realized_label_date"] = panel.groupby("ticker", sort=False)["date"].shift(
        -config.horizon_months
    )
    panel["forward_excess_return"] = (
        panel["forward_raw_return"] - panel["forward_benchmark_return"]
    )

    label_frame = panel[
        [
            "ticker",
            "date",
            "benchmark_ticker",
            "realized_label_date",
            "forward_raw_return",
            "forward_benchmark_return",
            "forward_excess_return",
        ]
    ].copy()

    if config.target_type == "forward_excess_return_top_n_binary":
        if config.cross_sectional_top_n is None:
            raise ValueError("cross_sectional_top_n must be provided for the top-N label.")
        label_frame = _build_top_n_binary_label(
            label_frame,
            value_column="forward_excess_return",
            top_n=config.cross_sectional_top_n,
        )
        label_definition = (
            f"Label is 1 when the ticker ranks inside the top {config.cross_sectional_top_n} "
            f"next-{config.horizon_months}-month benchmark-relative returns across the decision-month "
            "cross-section, using month-end t inputs and realized month-end t+1 outcomes."
        )
    elif config.target_type == "forward_excess_return_positive_binary":
        label_frame = _build_threshold_binary_label(
            label_frame,
            value_column="forward_excess_return",
            threshold=config.positive_threshold,
        )
        label_definition = (
            "Label is 1 when the next realized benchmark-relative return exceeds the configured "
            f"threshold of {config.positive_threshold:.4f} over the next {config.horizon_months} month(s)."
        )
    elif config.target_type == "forward_raw_return_positive_binary":
        label_frame = _build_threshold_binary_label(
            label_frame,
            value_column="forward_raw_return",
            threshold=config.positive_threshold,
        )
        label_definition = (
            "Label is 1 when the next realized raw return exceeds the configured "
            f"threshold of {config.positive_threshold:.4f} over the next {config.horizon_months} month(s)."
        )
    else:
        raise ValueError(f"Unsupported label target_type: {config.target_type}")

    label_frame = label_frame.sort_values(["date", "ticker"]).reset_index(drop=True)
    assert_unique_keys(label_frame, ["ticker", "date"], "model_labels")

    metadata = {
        "target_type": config.target_type,
        "horizon_months": config.horizon_months,
        "benchmark": config.benchmark,
        "positive_threshold": config.positive_threshold,
        "cross_sectional_top_n": config.cross_sectional_top_n,
        "definition": label_definition,
    }
    return label_frame, metadata
