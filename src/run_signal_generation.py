"""CLI entrypoint for deterministic signal generation."""

from __future__ import annotations

import logging
import sys

from src.data.io import read_parquet_required, write_csv, write_json, write_parquet
from src.signals.config import configure_signal_logging, load_signal_pipeline_config
from src.signals.qc import build_signal_qc_summary, build_signal_selection_summary
from src.signals.scoring import build_signal_rankings
from src.utils.cli import parse_execution_mode_args
from src.utils.config import ensure_output_directories


def main(argv: list[str] | None = None) -> int:
    """Generate deterministic cross-sectional rankings from the feature panel."""
    args = parse_execution_mode_args(argv)
    config = load_signal_pipeline_config(execution_mode=args.execution_mode)
    configure_signal_logging(config)
    ensure_output_directories(config.project)

    logger = logging.getLogger(__name__)
    logger.info("Starting signal generation.")

    feature_panel = read_parquet_required(config.outputs.feature_panel, "feature_panel")
    rankings, metadata = build_signal_rankings(feature_panel, config)

    write_parquet(rankings, config.outputs.signal_rankings)
    write_json(
        build_signal_qc_summary(
            rankings,
            configured_features=metadata["configured_features"],
            selection_top_n=metadata["selection_top_n"],
        ),
        config.outputs.signal_qc_summary,
    )
    write_csv(build_signal_selection_summary(rankings), config.outputs.signal_selection_summary)

    logger.info("Wrote %s", config.outputs.signal_rankings)
    print("Signal generation completed.")
    print(config.outputs.signal_rankings)
    print(config.outputs.signal_qc_summary)
    print(config.outputs.signal_selection_summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
