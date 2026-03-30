"""Smoke tests for the aligned project scaffold."""

from importlib import import_module
from pathlib import Path

import yaml

from src.utils.config import ensure_output_directories, load_project_config


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_documented_src_subpackages_are_importable() -> None:
    """Ensure the documented package boundaries exist as importable modules."""
    module_names = [
        "src",
        "src.data",
        "src.features",
        "src.signals",
        "src.portfolio",
        "src.backtest",
        "src.models",
        "src.evaluation",
        "src.reporting",
        "src.utils",
    ]

    for module_name in module_names:
        assert import_module(module_name).__name__ == module_name


def test_cli_entrypoints_expose_main() -> None:
    """Ensure the runner modules are importable and callable."""
    runner_modules = [
        "src.run_data_ingestion",
        "src.run_panel_assembly",
        "src.run_feature_generation",
        "src.run_signal_generation",
        "src.run_backtest",
        "src.run_modeling_baselines",
        "src.run_logistic_regression",
        "src.run_random_forest",
        "src.run_model_backtest",
        "src.run_model_evaluation_report",
        "src.run_evaluation_report",
    ]

    for module_name in runner_modules:
        module = import_module(module_name)
        assert callable(module.main)


def test_config_files_parse_and_cover_expected_categories() -> None:
    """Ensure the documented config files exist and are valid YAML."""
    config_files = {
        "backtest": REPO_ROOT / "config" / "backtest.yaml",
        "data": REPO_ROOT / "config" / "data.yaml",
        "evaluation": REPO_ROOT / "config" / "evaluation.yaml",
        "execution": REPO_ROOT / "config" / "execution.yaml",
        "features": REPO_ROOT / "config" / "features.yaml",
        "logging": REPO_ROOT / "config" / "logging.yaml",
        "model": REPO_ROOT / "config" / "model.yaml",
        "paths": REPO_ROOT / "config" / "paths.yaml",
        "signals": REPO_ROOT / "config" / "signals.yaml",
        "universe": REPO_ROOT / "config" / "universe.yaml",
    }

    for expected_key, path in config_files.items():
        assert path.exists()
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict)
        assert parsed
        assert expected_key in path.stem


def test_project_config_matches_documented_defaults() -> None:
    """Ensure the shared config loader resolves the scaffold contract."""
    config = load_project_config(REPO_ROOT)

    assert config.universe.preset_name == "initial_large_cap_tech_plus_comparison"
    assert config.universe.frequency == "monthly"
    assert config.execution.mode_name == "seeded"
    assert config.universe.explicit_benchmarks == ("SPY", "QQQ")
    assert config.universe.derived_benchmarks == ("equal_weight_universe",)
    assert config.evaluation.evidence.minimum_months_for_descriptive_segment == 3
    assert config.evaluation.evidence.minimum_months_for_broader_coverage_segment == 12
    assert len(config.universe.tech_tickers) == 10
    assert len(config.universe.comparison_tickers) == 10
    assert config.backtest.top_n == 10
    assert config.backtest.frequency == "monthly"
    assert config.backtest.transaction_cost_bps == 10.0
    assert config.outputs.monthly_panel == REPO_ROOT / "outputs" / "data" / "monthly_panel.parquet"
    assert config.outputs.panel_qc_summary == REPO_ROOT / "outputs" / "data" / "panel_qc_summary.json"
    assert config.outputs.signal_rankings == REPO_ROOT / "outputs" / "signals" / "signal_rankings.parquet"
    assert (
        config.outputs.experiment_registry
        == REPO_ROOT / "outputs" / "reports" / "experiment_registry.jsonl"
    )
    assert (
        config.outputs.model_strategy_report
        == REPO_ROOT / "outputs" / "reports" / "model_strategy_report.md"
    )
    assert config.outputs.run_summary == REPO_ROOT / "outputs" / "reports" / "run_summary.json"
    assert (
        config.outputs.model_comparison_summary
        == REPO_ROOT / "outputs" / "reports" / "model_comparison_summary.json"
    )
    assert (
        config.outputs.model_subperiod_comparison
        == REPO_ROOT / "outputs" / "reports" / "model_subperiod_comparison.csv"
    )


def test_output_directories_exist_or_can_be_ensured() -> None:
    """Ensure the canonical output directories are present for the pipeline stages."""
    config = load_project_config(REPO_ROOT)
    created = ensure_output_directories(config)
    assert created == config.outputs.stage_directories
    for directory in created:
        assert directory.exists()
        assert directory.is_dir()


def test_data_cli_entrypoints_return_success(capsys) -> None:
    """Ensure the implemented data-stage CLIs run end to end."""
    ingestion = import_module("src.run_data_ingestion")
    panel = import_module("src.run_panel_assembly")

    assert ingestion.main() == 0
    captured = capsys.readouterr()
    assert "Data ingestion completed." in captured.out

    assert panel.main() == 0
    captured = capsys.readouterr()
    assert "Panel assembly completed." in captured.out


def test_data_ingestion_cli_supports_research_scale_mode(capsys) -> None:
    """The research-scale execution mode should still run when only seeded sample files exist."""
    ingestion = import_module("src.run_data_ingestion")

    assert ingestion.main(["--execution-mode", "research_scale"]) == 0
    captured = capsys.readouterr()
    assert "Data ingestion completed." in captured.out


def test_feature_cli_entrypoint_returns_success(capsys) -> None:
    """Ensure the implemented feature-generation CLI runs end to end."""
    ingestion = import_module("src.run_data_ingestion")
    panel = import_module("src.run_panel_assembly")
    feature_generation = import_module("src.run_feature_generation")

    assert ingestion.main() == 0
    capsys.readouterr()
    assert panel.main() == 0
    capsys.readouterr()
    assert feature_generation.main() == 0
    captured = capsys.readouterr()
    assert "Feature generation completed." in captured.out


def test_signal_cli_entrypoint_returns_success(capsys) -> None:
    """Ensure the implemented signal-generation CLI runs end to end."""
    ingestion = import_module("src.run_data_ingestion")
    panel = import_module("src.run_panel_assembly")
    feature_generation = import_module("src.run_feature_generation")
    signal_generation = import_module("src.run_signal_generation")

    assert ingestion.main() == 0
    capsys.readouterr()
    assert panel.main() == 0
    capsys.readouterr()
    assert feature_generation.main() == 0
    capsys.readouterr()
    assert signal_generation.main() == 0
    captured = capsys.readouterr()
    assert "Signal generation completed." in captured.out


def test_backtest_cli_entrypoint_returns_success(capsys) -> None:
    """Ensure the implemented backtest CLI runs end to end."""
    ingestion = import_module("src.run_data_ingestion")
    panel = import_module("src.run_panel_assembly")
    feature_generation = import_module("src.run_feature_generation")
    signal_generation = import_module("src.run_signal_generation")
    backtest = import_module("src.run_backtest")

    assert ingestion.main() == 0
    capsys.readouterr()
    assert panel.main() == 0
    capsys.readouterr()
    assert feature_generation.main() == 0
    capsys.readouterr()
    assert signal_generation.main() == 0
    capsys.readouterr()
    assert backtest.main() == 0
    captured = capsys.readouterr()
    assert "Backtest completed." in captured.out


def test_evaluation_report_cli_entrypoint_returns_success(capsys) -> None:
    """Ensure the implemented evaluation-report CLI runs end to end."""
    ingestion = import_module("src.run_data_ingestion")
    panel = import_module("src.run_panel_assembly")
    feature_generation = import_module("src.run_feature_generation")
    signal_generation = import_module("src.run_signal_generation")
    backtest = import_module("src.run_backtest")
    evaluation_report = import_module("src.run_evaluation_report")

    assert ingestion.main() == 0
    capsys.readouterr()
    assert panel.main() == 0
    capsys.readouterr()
    assert feature_generation.main() == 0
    capsys.readouterr()
    assert signal_generation.main() == 0
    capsys.readouterr()
    assert backtest.main() == 0
    capsys.readouterr()
    assert evaluation_report.main() == 0
    captured = capsys.readouterr()
    assert "Evaluation reporting completed." in captured.out
    assert (REPO_ROOT / "outputs" / "reports" / "run_summary.json").exists()


def test_modeling_cli_entrypoints_return_success(capsys) -> None:
    """Ensure the implemented modeling CLIs run end to end."""
    ingestion = import_module("src.run_data_ingestion")
    panel = import_module("src.run_panel_assembly")
    feature_generation = import_module("src.run_feature_generation")
    signal_generation = import_module("src.run_signal_generation")
    modeling = import_module("src.run_modeling_baselines")
    logistic_regression = import_module("src.run_logistic_regression")
    random_forest = import_module("src.run_random_forest")
    model_backtest = import_module("src.run_model_backtest")
    model_evaluation_report = import_module("src.run_model_evaluation_report")

    assert ingestion.main() == 0
    capsys.readouterr()
    assert panel.main() == 0
    capsys.readouterr()
    assert feature_generation.main() == 0
    capsys.readouterr()
    assert signal_generation.main() == 0
    capsys.readouterr()

    assert modeling.main() == 0
    captured = capsys.readouterr()
    assert "Modeling baselines completed." in captured.out

    assert logistic_regression.main() == 0
    captured = capsys.readouterr()
    assert "Modeling baselines completed." in captured.out

    assert random_forest.main() == 0
    captured = capsys.readouterr()
    assert "Modeling baselines completed." in captured.out

    assert model_backtest.main() == 0
    captured = capsys.readouterr()
    assert "Model backtest completed." in captured.out

    assert model_evaluation_report.main() == 0
    captured = capsys.readouterr()
    assert "Model evaluation reporting completed." in captured.out
    assert (REPO_ROOT / "outputs" / "reports" / "run_summary.json").exists()
    assert (REPO_ROOT / "outputs" / "reports" / "model_comparison_summary.json").exists()
    assert (REPO_ROOT / "outputs" / "reports" / "model_subperiod_comparison.csv").exists()
