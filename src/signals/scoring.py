"""Deterministic cross-sectional signal scoring and ranking."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.data.standardize import assert_unique_keys
from src.signals.config import SignalPipelineConfig


def _cross_sectional_feature_score(series: pd.Series, *, higher_is_better: bool) -> pd.Series:
    """Convert a raw feature into a cross-sectional percentile score within a month."""
    if series.notna().sum() == 0:
        return pd.Series(np.nan, index=series.index, dtype="float64")
    return series.rank(method="average", pct=True, ascending=higher_is_better)


def _weighted_available_average(
    frame: pd.DataFrame,
    *,
    score_columns: list[str],
    score_weights: dict[str, float],
) -> pd.Series:
    """Compute an available-feature weighted average row by row."""
    numerators = pd.Series(0.0, index=frame.index, dtype="float64")
    denominators = pd.Series(0.0, index=frame.index, dtype="float64")
    for score_column in score_columns:
        weight = score_weights[score_column]
        values = frame[score_column]
        mask = values.notna()
        numerators.loc[mask] += values.loc[mask] * weight
        denominators.loc[mask] += weight
    return numerators / denominators.replace(0.0, np.nan)


def build_signal_rankings(
    feature_panel: pd.DataFrame, config: SignalPipelineConfig
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build deterministic cross-sectional composite rankings from the feature panel."""
    assert_unique_keys(feature_panel, ["ticker", "date"], "feature_panel")
    rankings = feature_panel.copy().sort_values(["date", "ticker"]).reset_index(drop=True)

    configured_features = list(config.features.all_features)
    missing_feature_columns = [
        feature_name for feature_name in configured_features if feature_name not in rankings.columns
    ]
    if missing_feature_columns:
        raise ValueError(
            "Configured signal features are missing from the feature panel: "
            f"{missing_feature_columns}"
        )

    score_groups: dict[str, list[str]] = {"higher_is_better": [], "lower_is_better": []}
    score_weights: dict[str, float] = {}

    for feature_name in config.features.higher_is_better:
        score_column = f"score__{feature_name}"
        rankings[score_column] = rankings.groupby("date", sort=False)[feature_name].transform(
            lambda series: _cross_sectional_feature_score(series, higher_is_better=True)
        )
        score_groups["higher_is_better"].append(score_column)
        score_weights[score_column] = config.weights[feature_name]

    for feature_name in config.features.lower_is_better:
        score_column = f"score__{feature_name}"
        rankings[score_column] = rankings.groupby("date", sort=False)[feature_name].transform(
            lambda series: _cross_sectional_feature_score(series, higher_is_better=False)
        )
        score_groups["lower_is_better"].append(score_column)
        score_weights[score_column] = config.weights[feature_name]

    score_columns = score_groups["higher_is_better"] + score_groups["lower_is_better"]
    rankings["non_missing_feature_count"] = rankings[configured_features].notna().sum(axis=1)

    if config.strategy.score_missing_policy != "available_weighted_mean":
        raise ValueError(
            "Only score_missing_policy='available_weighted_mean' is implemented currently."
        )

    rankings["composite_score"] = _weighted_available_average(
        rankings,
        score_columns=score_columns,
        score_weights=score_weights,
    )
    rankings.loc[
        rankings["non_missing_feature_count"] < config.strategy.minimum_non_missing_features,
        "composite_score",
    ] = np.nan

    rankings["score_rank"] = np.nan
    rankings["score_rank_pct"] = np.nan
    rankings["selected_top_n"] = False

    ranked_frames: list[pd.DataFrame] = []
    for _, month_frame in rankings.groupby("date", sort=False):
        month = month_frame.copy()
        asc = []
        cols = []
        for tie_breaker in config.tie_breakers:
            if tie_breaker.column not in month.columns:
                raise ValueError(
                    f"Tie-break column {tie_breaker.column!r} is missing from signal inputs."
                )
            cols.append(tie_breaker.column)
            asc.append(tie_breaker.ascending)

        ranked = month.sort_values(cols, ascending=asc, na_position="last").reset_index(drop=True)
        scored_mask = ranked["composite_score"].notna()
        scored_count = int(scored_mask.sum())
        if scored_count > 0:
            ranked.loc[scored_mask, "score_rank"] = np.arange(1, scored_count + 1, dtype=float)
            ranked.loc[scored_mask, "score_rank_pct"] = ranked.loc[scored_mask, "score_rank"] / scored_count
            ranked.loc[scored_mask, "selected_top_n"] = (
                ranked.loc[scored_mask, "score_rank"] <= config.strategy.selection_top_n
            )
        ranked_frames.append(ranked)

    rankings = pd.concat(ranked_frames, ignore_index=True)
    rankings = rankings.sort_values(["ticker", "date"]).reset_index(drop=True)
    assert_unique_keys(rankings, ["ticker", "date"], "signal_rankings")

    metadata: dict[str, Any] = {
        "configured_features": configured_features,
        "score_columns": score_columns,
        "score_groups": score_groups,
        "strategy_name": config.strategy.name,
        "selection_top_n": config.strategy.selection_top_n,
        "minimum_non_missing_features": config.strategy.minimum_non_missing_features,
    }
    return rankings, metadata
