# Module Progress: Reporting

## Current State

- Baseline evaluation reporting and overlap-aware model-aware reporting with structured coverage diagnostics implemented

## Files Touched

- `config/paths.yaml`
- `config/execution.yaml`
- `config/evaluation.yaml`
- `src/evaluation/__init__.py`
- `src/evaluation/coverage.py`
- `src/evaluation/comparison.py`
- `src/evaluation/summary.py`
- `src/reporting/__init__.py`
- `src/reporting/markdown.py`
- `src/reporting/registry.py`
- `src/run_evaluation_report.py`
- `src/run_model_evaluation_report.py`
- `tests/evaluation/test_model_comparison.py`
- `tests/reporting/test_evaluation_reporting.py`
- `tests/test_repo_skeleton.py`
- `README.md`
- `docs/02_system_architecture.md`
- `docs/03_data_schema.md`
- `docs/07_evaluation_spec.md`
- `docs/08_experiment_tracking.md`
- `docs/10_development_roadmap.md`
- `progress/current_status.md`

## Completed Work

- Implemented structured evaluation-summary generation from the backtest artifacts.
- Implemented benchmark-aware strategy-report rendering to Markdown.
- Implemented model-aware evaluation-summary generation from model metadata plus model-backtest artifacts.
- Implemented model-aware strategy-report rendering to Markdown.
- Added overlap-aware deterministic-vs-model comparison logic keyed only on shared realized dates.
- Added held-out fold coverage diagnostics to the model-aware reporting path.
- Added cross-stage coverage summary generation and `outputs/reports/run_summary.json`.
- Added `outputs/reports/model_comparison_summary.json` as a machine-readable summary for model comparison reporting.
- Added overlap-window subperiod and regime diagnostics by fold, calendar quarter, calendar half-year, calendar year, benchmark direction, benchmark drawdown state, and benchmark volatility state.
- Added explicit segment evidence tiers for insufficient-history versus broader-coverage exploratory diagnostics.
- Added `outputs/reports/model_subperiod_comparison.csv` as a machine-readable segment-level comparison table.
- Implemented experiment-registry record creation and JSONL append behavior for deterministic and model-aware reports.
- Replaced the scaffold evaluation-report CLI with a runnable implementation that writes the canonical reporting artifacts.
- Added `src.run_model_evaluation_report` to write `outputs/reports/model_strategy_report.md`, `outputs/reports/model_comparison_summary.json`, and `outputs/reports/model_subperiod_comparison.csv` from the current canonical model artifacts.
- Updated docs so reporting now consumes the backtest-owned metric tables and logs exploratory runs explicitly.

## Testing Status

- `tests/reporting/test_evaluation_reporting.py` now covers:
  - evaluation-summary construction
  - strategy report rendering
  - run-summary artifact construction
  - experiment-registry append behavior
  - model-evaluation-summary construction
  - model strategy report rendering
  - model experiment-registry append behavior
- `tests/evaluation/test_model_comparison.py` now covers:
  - overlap-aware deterministic-vs-model comparison logic
  - held-out fold coverage diagnostics
  - comparison-convention metadata
  - overlap-window subperiod and regime diagnostics
  - evidence-tier behavior for short overlap segments
- `tests/test_repo_skeleton.py` now exercises:
  - `src.run_evaluation_report`
  - `src.run_model_evaluation_report`
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `61 passed` on 2026-03-30.

## Manual Verification Status

- `.\.venv\Scripts\python.exe -m src.run_evaluation_report` completed successfully on 2026-03-28.
- `.\.venv\Scripts\python.exe -m src.run_model_evaluation_report` completed successfully on 2026-03-30.
- `.\.venv\Scripts\python.exe -m src.run_evaluation_report --execution-mode research_scale` completed successfully on 2026-03-30.
- `.\.venv\Scripts\python.exe -m src.run_model_evaluation_report --execution-mode research_scale` completed successfully on 2026-03-30.
- `outputs/reports/strategy_report.md`, `outputs/reports/model_strategy_report.md`, `outputs/reports/run_summary.json`, `outputs/reports/model_comparison_summary.json`, `outputs/reports/model_subperiod_comparison.csv`, and `outputs/reports/experiment_registry.jsonl` were manually reviewed for content, append behavior, and required context.

## Known Issues / Risks

- Current report output is intentionally cautious and still exploratory.
- Regime-aware diagnostics are now implemented, but the current overlap window is too short for strong regime evidence.
- The coverage audit correctly reports `research_scale` sample fallback today, but broader local raw files are still needed for a genuinely informative longer-history report.
- Richer attribution and more detailed report formatting remain unimplemented.
- Report conclusions still inherit revised-history caveats from fundamentals-derived inputs.
- The model-aware report reflects the latest canonical model artifacts, so explicit run versioning is still limited.

## Immediate Next Step

- Rerun the reporting stages after broader non-sample local raw history is added so the new coverage and segment-evidence layers move beyond the current insufficient-history tier.
