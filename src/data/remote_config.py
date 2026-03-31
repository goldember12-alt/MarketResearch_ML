"""Config loading for remote raw-data acquisition."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.data.config import DataPipelineConfig, load_data_pipeline_config


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Read a YAML file and ensure it contains a mapping."""
    parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return parsed


@dataclass(frozen=True)
class RemoteAcquisitionSettings:
    """Top-level settings controlling remote raw-data snapshot behavior."""

    default_provider: str
    latest_file_overwrite_policy: str
    write_latest_files: bool
    write_snapshot_copies: bool
    write_dataset_manifests: bool
    snapshot_timestamp_format: str


@dataclass(frozen=True)
class DatasetToggleConfig:
    """Provider dataset toggles for the first remote acquisition milestone."""

    market_prices: bool
    benchmark_prices: bool
    overview_metadata: bool
    sec_companyfacts: bool


@dataclass(frozen=True)
class AlphaVantageProviderConfig:
    """Alpha Vantage endpoint and credential settings."""

    enabled: bool
    base_url: str
    monthly_adjusted_function: str
    overview_function: str
    datatype: str
    outputsize: str
    api_key_env_var: str
    request_pause_seconds: float
    timeout_seconds: float


@dataclass(frozen=True)
class SecProviderConfig:
    """SEC endpoint and identity settings."""

    enabled: bool
    company_tickers_url: str
    company_facts_base_url: str
    user_agent_env_var: str
    contact_email_env_var: str
    app_name: str
    request_pause_seconds: float
    timeout_seconds: float


@dataclass(frozen=True)
class DatasetOutputConfig:
    """Output naming and directory settings for one fetched dataset."""

    base_dir: Path
    latest_filename: str | None
    latest_manifest_filename: str
    snapshot_subdir: Path | None
    manifest_subdir: Path
    snapshot_filename_template: str | None


@dataclass(frozen=True)
class RunManifestOutputConfig:
    """Output location for one fetch-run summary manifest."""

    base_dir: Path
    filename_template: str


@dataclass(frozen=True)
class RemoteOutputConfig:
    """Grouped output configs for all remote-acquisition datasets."""

    market: DatasetOutputConfig
    benchmarks: DatasetOutputConfig
    overview: DatasetOutputConfig
    fundamentals: DatasetOutputConfig
    sec_companyfacts_raw: DatasetOutputConfig
    run_manifest: RunManifestOutputConfig


@dataclass(frozen=True)
class RemoteRawFetchConfig:
    """Resolved config bundle for remote raw-data acquisition."""

    data_pipeline: DataPipelineConfig
    acquisition: RemoteAcquisitionSettings
    toggles: DatasetToggleConfig
    alphavantage: AlphaVantageProviderConfig
    sec: SecProviderConfig
    outputs: RemoteOutputConfig
    config_files: dict[str, Path]

    @property
    def project(self):  # noqa: ANN201
        """Expose the shared project config."""
        return self.data_pipeline.project

    @property
    def raw(self):  # noqa: ANN201
        """Expose the shared raw-data directories."""
        return self.data_pipeline.raw

    @property
    def logging(self):  # noqa: ANN201
        """Expose logging settings shared with the data pipeline."""
        return self.data_pipeline.logging


def _resolve_dataset_output(
    *,
    base_dir: Path,
    raw_mapping: dict[str, Any],
) -> DatasetOutputConfig:
    """Resolve one dataset output section against its raw-data base directory."""
    relative_dir = Path(str(raw_mapping.get("relative_dir", ".")))
    resolved_base_dir = base_dir / relative_dir
    snapshot_subdir = raw_mapping.get("snapshot_subdir")
    return DatasetOutputConfig(
        base_dir=resolved_base_dir,
        latest_filename=(
            None
            if raw_mapping.get("latest_filename") is None
            else str(raw_mapping["latest_filename"])
        ),
        latest_manifest_filename=str(raw_mapping["latest_manifest_filename"]),
        snapshot_subdir=(
            None if snapshot_subdir is None else resolved_base_dir / Path(str(snapshot_subdir))
        ),
        manifest_subdir=resolved_base_dir / Path(str(raw_mapping["manifest_subdir"])),
        snapshot_filename_template=(
            None
            if raw_mapping.get("snapshot_filename_template") is None
            else str(raw_mapping["snapshot_filename_template"])
        ),
    )


def load_remote_raw_fetch_config(
    root_dir: Path | None = None,
    execution_mode: str | None = None,
) -> RemoteRawFetchConfig:
    """Load the remote raw-data acquisition config bundle."""
    data_pipeline = load_data_pipeline_config(root_dir=root_dir, execution_mode=execution_mode)
    resolved_root = data_pipeline.root_dir
    remote_path = resolved_root / "config" / "remote_data.yaml"
    remote_raw = _load_yaml_mapping(remote_path)

    acquisition_raw = remote_raw["remote_acquisition"]
    toggles_raw = remote_raw["dataset_toggles"]
    providers_raw = remote_raw["providers"]
    outputs_raw = remote_raw["outputs"]
    alphavantage_raw = providers_raw["alphavantage"]
    sec_raw = providers_raw["sec"]

    acquisition = RemoteAcquisitionSettings(
        default_provider=str(acquisition_raw["default_provider"]),
        latest_file_overwrite_policy=str(acquisition_raw["latest_file_overwrite_policy"]),
        write_latest_files=bool(acquisition_raw["write_latest_files"]),
        write_snapshot_copies=bool(acquisition_raw["write_snapshot_copies"]),
        write_dataset_manifests=bool(acquisition_raw["write_dataset_manifests"]),
        snapshot_timestamp_format=str(acquisition_raw["snapshot_timestamp_format"]),
    )
    if acquisition.latest_file_overwrite_policy not in {"overwrite", "fail"}:
        raise ValueError(
            "remote_acquisition.latest_file_overwrite_policy must be 'overwrite' or 'fail'."
        )

    toggles = DatasetToggleConfig(
        market_prices=bool(toggles_raw["market_prices"]),
        benchmark_prices=bool(toggles_raw["benchmark_prices"]),
        overview_metadata=bool(toggles_raw["overview_metadata"]),
        sec_companyfacts=bool(toggles_raw["sec_companyfacts"]),
    )

    alphavantage = AlphaVantageProviderConfig(
        enabled=bool(alphavantage_raw["enabled"]),
        base_url=str(alphavantage_raw["base_url"]),
        monthly_adjusted_function=str(alphavantage_raw["monthly_adjusted_function"]),
        overview_function=str(alphavantage_raw["overview_function"]),
        datatype=str(alphavantage_raw["datatype"]),
        outputsize=str(alphavantage_raw["outputsize"]),
        api_key_env_var=str(alphavantage_raw["api_key_env_var"]),
        request_pause_seconds=float(alphavantage_raw["request_pause_seconds"]),
        timeout_seconds=float(alphavantage_raw["timeout_seconds"]),
    )

    sec = SecProviderConfig(
        enabled=bool(sec_raw["enabled"]),
        company_tickers_url=str(sec_raw["company_tickers_url"]),
        company_facts_base_url=str(sec_raw["company_facts_base_url"]),
        user_agent_env_var=str(sec_raw["user_agent_env_var"]),
        contact_email_env_var=str(sec_raw["contact_email_env_var"]),
        app_name=str(sec_raw["app_name"]),
        request_pause_seconds=float(sec_raw["request_pause_seconds"]),
        timeout_seconds=float(sec_raw["timeout_seconds"]),
    )

    outputs = RemoteOutputConfig(
        market=_resolve_dataset_output(
            base_dir=data_pipeline.raw.market_dir, raw_mapping=outputs_raw["market"]
        ),
        benchmarks=_resolve_dataset_output(
            base_dir=data_pipeline.raw.benchmarks_dir,
            raw_mapping=outputs_raw["benchmarks"],
        ),
        overview=_resolve_dataset_output(
            base_dir=data_pipeline.raw.fundamentals_dir,
            raw_mapping=outputs_raw["overview"],
        ),
        fundamentals=_resolve_dataset_output(
            base_dir=data_pipeline.raw.fundamentals_dir,
            raw_mapping=outputs_raw["fundamentals"],
        ),
        sec_companyfacts_raw=_resolve_dataset_output(
            base_dir=data_pipeline.raw.fundamentals_dir,
            raw_mapping=outputs_raw["sec_companyfacts_raw"],
        ),
        run_manifest=RunManifestOutputConfig(
            base_dir=data_pipeline.raw.root_dir
            / Path(str(outputs_raw["run_manifest"]["relative_dir"])),
            filename_template=str(outputs_raw["run_manifest"]["filename_template"]),
        ),
    )

    return RemoteRawFetchConfig(
        data_pipeline=data_pipeline,
        acquisition=acquisition,
        toggles=toggles,
        alphavantage=alphavantage,
        sec=sec,
        outputs=outputs,
        config_files={
            **data_pipeline.config_files,
            "remote_data": remote_path,
        },
    )
