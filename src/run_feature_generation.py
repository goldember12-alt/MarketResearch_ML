"""CLI entrypoint for leakage-safe feature generation."""

from __future__ import annotations

import logging

from src.data.io import read_parquet_required, write_csv, write_json, write_parquet
from src.features.config import configure_feature_logging, load_feature_pipeline_config
from src.features.engineering import build_feature_panel
from src.features.qc import build_feature_missingness_summary, build_feature_qc_summary
from src.utils.config import ensure_output_directories


def main() -> int:
    """Generate leakage-safe monthly features from the canonical panel."""
    config = load_feature_pipeline_config()
    configure_feature_logging(config)
    ensure_output_directories(config.project)

    logger = logging.getLogger(__name__)
    logger.info("Starting feature generation.")

    monthly_panel = read_parquet_required(config.outputs.monthly_panel, "monthly_panel")
    feature_panel, metadata = build_feature_panel(monthly_panel, config)

    write_parquet(feature_panel, config.outputs.feature_panel)
    write_json(
        build_feature_qc_summary(
            feature_panel,
            feature_columns=metadata["feature_columns"],
            feature_groups=metadata["feature_groups"],
        ),
        config.outputs.feature_qc_summary,
    )
    write_csv(
        build_feature_missingness_summary(
            feature_panel,
            feature_columns=metadata["feature_columns"],
            feature_groups=metadata["feature_groups"],
        ),
        config.outputs.feature_missingness_summary,
    )

    logger.info("Wrote %s", config.outputs.feature_panel)
    print("Feature generation completed.")
    print(config.outputs.feature_panel)
    print(config.outputs.feature_qc_summary)
    print(config.outputs.feature_missingness_summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
