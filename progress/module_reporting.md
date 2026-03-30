# Module Progress: Reporting

## Current State

- Baseline evaluation reporting and model-aware reporting implemented

## Files Touched

- `config/paths.yaml`
- `src/evaluation/__init__.py`
- `src/evaluation/summary.py`
- `src/reporting/__init__.py`
- `src/reporting/markdown.py`
- `src/reporting/registry.py`
- `src/run_evaluation_report.py`
- `src/run_model_evaluation_report.py`
- `tests/reporting/test_evaluation_reporting.py`
- `tests/test_repo_skeleton.py`
- `README.md`
- `docs/02_system_architecture.md`
- `docs/03_data_schema.md`
- `docs/07_evaluation_spec.md`
- `docs/08_experiment_tracking.md`
- `docs/09_risk_and_bias_controls.md`
- `docs/10_development_roadmap.md`
- `progress/current_status.md`

## Completed Work

- Implemented structured evaluation-summary generation from the backtest artifacts.
- Implemented benchmark-aware strategy-report rendering to Markdown.
- Implemented model-aware evaluation-summary generation from model metadata plus model-backtest artifacts.
- Implemented model-aware strategy-report rendering to Markdown.
- Implemented experiment-registry record creation and JSONL append behavior for deterministic and model-aware reports.
- Replaced the scaffold evaluation-report CLI with a runnable implementation that writes the canonical reporting artifacts.
- Added `src.run_model_evaluation_report` to write `outputs/reports/model_strategy_report.md` from the current canonical model artifacts.
- Updated docs so reporting now consumes the backtest-owned metric tables and logs exploratory runs explicitly.

## Testing Status

- `tests/reporting/test_evaluation_reporting.py` now covers:
  - evaluation-summary construction
  - strategy report rendering
  - experiment-registry append behavior
  - model-evaluation-summary construction
  - model strategy report rendering
  - model experiment-registry append behavior
- `tests/test_repo_skeleton.py` now exercises:
  - `src.run_evaluation_report`
  - `src.run_model_evaluation_report`
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `53 passed` on 2026-03-30.

## Manual Verification Status

- `.\.venv\Scripts\python.exe -m src.run_evaluation_report` completed successfully on 2026-03-28.
- `.\.venv\Scripts\python.exe -m src.run_model_evaluation_report` completed successfully on 2026-03-30.
- `outputs/reports/strategy_report.md`, `outputs/reports/model_strategy_report.md`, and `outputs/reports/experiment_registry.jsonl` were manually reviewed for content, append behavior, and required context.

## Known Issues / Risks

- Current report output is intentionally cautious and still exploratory.
- Regime-aware diagnostics, richer attribution, and more detailed report formatting remain unimplemented.
- Report conclusions still inherit revised-history caveats from fundamentals-derived inputs.
- The model-aware report reflects the latest canonical model artifacts, so explicit run versioning is still limited.

## Immediate Next Step

- Extend model-aware reporting with longer-history walk-forward coverage, richer attribution, and robustness breakdowns.
