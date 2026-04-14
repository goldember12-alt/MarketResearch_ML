# Module Progress: Reporting

## Current State

- Baseline evaluation reporting and overlap-aware model-aware reporting are implemented, and Stage 2 reporting/provenance consistency hardening is complete as of 2026-04-13.
- Reporting has now also been manually exercised on a Stage 3 mixed-input `research_scale` rerun as of 2026-04-13, where broader local raw was selected only for `fundamentals_monthly` while `prices_monthly` and `benchmarks_monthly` still fell back to seeded samples.

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
- Added compact raw-dataset provenance summaries to the coverage-audit sections and to `outputs/reports/run_summary.json`.
- Hardened the raw-data coverage contract so reporting now distinguishes:
  - broader local raw files that exist on disk
  - the raw-input profile actually selected for the current run
  - whether research-scale seeded fallback was triggered
- Updated deterministic and model-aware markdown coverage audits so seeded runs explicitly say when broader local raw files exist on disk but the run still selected seeded sample inputs only.
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
  - compact raw-dataset provenance summaries in coverage reporting
  - seeded-run reporting when broader local raw files exist on disk but the run still selected sample inputs only
- `tests/evaluation/test_model_comparison.py` now covers:
  - overlap-aware deterministic-vs-model comparison logic
  - held-out fold coverage diagnostics
  - comparison-convention metadata
  - overlap-window subperiod and regime diagnostics
  - evidence-tier behavior for short overlap segments
- `tests/test_repo_skeleton.py` now exercises:
  - `src.run_evaluation_report`
  - `src.run_model_evaluation_report`
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `62 passed` on 2026-03-30.
- `.\.venv\Scripts\python.exe -m pytest -q tests/reporting/test_evaluation_reporting.py tests/evaluation/test_model_comparison.py` passed with `14 passed` on 2026-04-13 after the Stage 2 provenance/reporting hardening patch.
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `82 passed` on 2026-04-13 after the same patch added seeded-versus-broader-availability reporting tests.

## Manual Verification Status

- `.\.venv\Scripts\python.exe -m src.run_evaluation_report` completed successfully on 2026-03-28.
- `.\.venv\Scripts\python.exe -m src.run_model_evaluation_report` completed successfully on 2026-03-30.
- `.\.venv\Scripts\python.exe -m src.run_evaluation_report --execution-mode research_scale` completed successfully on 2026-03-30.
- `.\.venv\Scripts\python.exe -m src.run_model_evaluation_report --execution-mode research_scale` completed successfully on 2026-03-30.
- `outputs/reports/strategy_report.md`, `outputs/reports/model_strategy_report.md`, `outputs/reports/run_summary.json`, `outputs/reports/model_comparison_summary.json`, `outputs/reports/model_subperiod_comparison.csv`, and `outputs/reports/experiment_registry.jsonl` were manually reviewed for content, append behavior, and required context.
- The refreshed research-scale report outputs now surface raw-dataset provenance lines for the selected sample fallback files plus observed raw row/date spans.
- `.\.venv\Scripts\python.exe -m src.run_modeling_baselines --execution-mode research_scale`, `.\.venv\Scripts\python.exe -m src.run_model_backtest --execution-mode research_scale`, and `.\.venv\Scripts\python.exe -m src.run_model_evaluation_report --execution-mode research_scale` were rerun sequentially on 2026-03-30 after the automated suite so the canonical model/report outputs remain in the default `logistic_regression` state.
- `.\.venv\Scripts\python.exe -m src.run_evaluation_report` completed successfully on 2026-04-13 after the Stage 2 patch.
- `.\.venv\Scripts\python.exe -m src.run_model_evaluation_report` completed successfully on 2026-04-13 after the same patch.
- The regenerated `outputs/reports/strategy_report.md`, `outputs/reports/model_strategy_report.md`, `outputs/reports/run_summary.json`, and `outputs/reports/model_comparison_summary.json` were manually reviewed on 2026-04-13 and now state explicitly that the seeded run selected sample inputs only even though broader fundamentals raw files exist on disk.
- `.\.venv\Scripts\python.exe -m src.run_evaluation_report --execution-mode research_scale` completed successfully again on 2026-04-13 after the Stage 3 data fixes and live refresh attempt.
- The regenerated 2026-04-13 deterministic `research_scale` reporting artifacts were manually reviewed and now show the mixed selected-input state explicitly:
  - `outputs/reports/strategy_report.md`: coverage audit says `mixed seeded sample and broader local raw`, lists seeded fallback for `prices_monthly` and `benchmarks_monthly`, and identifies `fundamentals_quarterly_sec_companyfacts.parquet` as the broader local raw input actually selected
  - `outputs/reports/run_summary.json`: `coverage_summary.raw_data_selection.selected_input_profile` is `mixed_selected_inputs`, `datasets_using_broader_local_raw_inputs` contains only `fundamentals_monthly`, and `datasets_using_seeded_sample_fallback` contains `prices_monthly` and `benchmarks_monthly`
  - `outputs/reports/experiment_registry.jsonl`: a new `evaluation_report` entry was appended for the 2026-04-13 `research_scale` deterministic rerun
- The reporting outputs also confirm the practical Stage 3 limit of the current run:
  - broader raw fundamentals coverage was selected upstream with observed raw date coverage from `2006-09-30` through `2026-03-25`
  - downstream monthly outputs and realized deterministic backtest history still span only `2024-01-31` through `2024-06-30` because market and benchmark inputs remained sample-backed

## Known Issues / Risks

- Current report output is intentionally cautious and still exploratory.
- Regime-aware diagnostics are now implemented, but the current overlap window is too short for strong regime evidence.
- The coverage audit now distinguishes on-disk broader raw availability from the raw inputs actually selected, but a genuinely informative longer-history report still requires broader non-sample raw files to be selected and propagated through the downstream pipeline.
- The latest `research_scale` report is more informative than the seeded report, but it is still not benchmark-quality because the selected-input profile is mixed rather than fully broader-history.
- Richer attribution and more detailed report formatting remain unimplemented.
- Report conclusions still inherit revised-history caveats from fundamentals-derived inputs.
- The model-aware report reflects the latest canonical model artifacts, so explicit run versioning is still limited.
- Broader non-sample provenance is still identified through per-file details and filenames rather than through a normalized provider taxonomy in the coverage summary.

## Immediate Next Step

- Complete Stage 3 from `docs/10_development_roadmap.md` by rerunning the credentialed Alpha Vantage monthly price refresh on a fresh quota window, then regenerate the `research_scale` report and confirm the selected-input profile is no longer mixed.
