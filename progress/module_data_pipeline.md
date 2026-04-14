# Module Progress: Data Pipeline

## Current State

- Implemented for the local-file-first monthly ingestion and panel-assembly workflow, with a config-driven `research_scale` raw-file selection path and the first upstream Alpha Vantage + SEC remote raw-data acquisition layer
- Stage 1 baseline stabilization is restored as of 2026-04-13: seeded and `research_scale` data ingestion both run cleanly again in the current workspace state.
- Stage 3 execution was exercised on 2026-04-13: broader non-sample SEC fundamentals coverage is now available locally and downstream `research_scale` ingestion runs cleanly again after the Stage 3 sparse-SEC, raw-manifest-path, and duplicate-month fixes, but Alpha Vantage monthly market and benchmark raw coverage is still blocked by quota exhaustion in the latest live refresh.

## Files Touched

- `config/data.yaml`
- `config/remote_data.yaml`
- `config/execution.yaml`
- `config/evaluation.yaml`
- `config/paths.yaml`
- `src/utils/config.py`
- `src/data/__init__.py`
- `src/data/config.py`
- `src/data/universe.py`
- `src/data/io.py`
- `src/data/remote_config.py`
- `src/data/remote_io.py`
- `src/data/alphavantage.py`
- `src/data/sec_companyfacts.py`
- `src/data/standardize.py`
- `src/data/market_data.py`
- `src/data/benchmarks.py`
- `src/data/fundamentals_data.py`
- `src/data/qc.py`
- `src/data/panel_assembly.py`
- `src/run_data_ingestion.py`
- `src/run_fetch_remote_raw.py`
- `scripts/run_remote_refresh_and_research_scale.ps1`
- `src/run_panel_assembly.py`
- `data/raw/README.md`
- `data/raw/market/prices_daily_sample.csv`
- `data/raw/benchmarks/benchmarks_daily_sample.csv`
- `data/raw/fundamentals/fundamentals_quarterly_sample.csv`
- `tests/data/test_data_pipeline.py`
- `tests/data/test_remote_fetch.py`
- `tests/test_repo_skeleton.py`
- `README.md`
- `docs/02_system_architecture.md`
- `docs/03_data_schema.md`
- `docs/10_development_roadmap.md`
- `progress/current_status.md`

## Completed Work

- Added a dedicated data-stage config loader with raw-data path settings, benchmark defaults, month-end normalization rules, and fundamentals lag controls.
- Implemented local raw file discovery and persistence helpers for Parquet, JSON, and CSV artifacts.
- Implemented execution-mode-aware raw file selection:
  - default `seeded` mode reads only sample-tagged raw files
  - `research_scale` mode prefers broader non-sample local raw files and falls back to sample-tagged raw files when broader history is absent
- Implemented market-price ingestion that accepts daily or monthly raw files, standardizes to one row per ticker per month, and computes `monthly_return` from `adjusted_close`.
- Implemented benchmark ingestion for `SPY` and `QQQ` plus derived `equal_weight_universe` monthly benchmark construction.
- Implemented fundamentals standardization and monthly mapping using a documented `2`-month effective lag and a `12`-month max staleness cap.
- Implemented deterministic monthly panel assembly on the full universe-by-month grid with aligned primary benchmark returns.
- Implemented dataset QC JSON outputs and per-ticker/per-date coverage CSV outputs.
- Added raw-file selection manifests to the dataset QC JSON outputs so longer-history runs are auditable.
- Enriched the raw-file selection manifests with per-file filesystem metadata plus observed raw row/date coverage so future broader-history runs can prove exactly which local files were used.
- Seeded deterministic local sample raw inputs so the implemented runners can be executed end to end inside the repo.
- Updated the project docs to define the next acquisition milestone:
- Implemented the first upstream remote-acquisition layer with:
  - `config/remote_data.yaml` for provider credentials, endpoints, overwrite policy, and output naming
  - Alpha Vantage market and benchmark fetchers that write latest non-sample raw files plus immutable snapshots and manifests
  - Alpha Vantage overview metadata fetches written under `data/raw/fundamentals/metadata`
  - SEC Company Facts raw JSON capture plus a conservative mapped quarterly fundamentals subset written to `data/raw/fundamentals/fundamentals_quarterly_sec_companyfacts.parquet`
  - machine-readable provider manifests capturing request scope, timestamps, output files, and partial-failure/throttle conditions
  - runnable `src.run_fetch_remote_raw`
- Standardized future repo-local operational logs under `.cache/logs/` by updating `config/logging.yaml` and adding a one-shot PowerShell runner that logs the full fetch-plus-pipeline sequence there.
- Upgraded the remote fetch and wrapper logging so CLI `INFO` logs now go to stdout, fetch runs emit deterministic run ids with stage/symbol progress details, and wrapper failures write explicit error blocks plus child exit codes into the timestamped `.cache/logs/...` files.
- Added a repo-local credential loader for PowerShell refresh runs:
  - persistent local values now live in `config/remote_provider_env.local.ps1`
  - template lives in `config/remote_provider_env.local.example.ps1`
  - wrapper import helper lives in `scripts/import_remote_provider_env.ps1`
- Hardened raw-file discovery so headerless empty non-sample CSVs are ignored, preserving the documented `research_scale` fallback to seeded sample files when broader raw coverage is unusable.
- Hardened fundamentals monthly alignment so post-merge `fundamentals_source_date` and `fundamentals_effective_date` are coerced back to datetimelike dtype before staleness masking.
- Hardened `month_difference()` so object-backed datetime-like series with nulls are coerced safely instead of raising `.dt` accessor errors.
- Patched the live-run failure modes discovered on 2026-03-31:
  - later Alpha Vantage stages are now skipped once a daily quota condition has already been detected in the same run
  - zero-row fetch stages no longer overwrite latest/snapshot raw CSVs
  - SEC Company Facts responses now decode gzip-compressed payloads before JSON parsing
- Patched the 2026-04-13 Stage 3 live-run failure modes:
  - sparse SEC Company Facts payloads that omit optional concepts now remain usable instead of failing the whole ticker mapping
  - SEC raw-manifest path resolution no longer tries to format the `{symbol}` placeholder from raw snapshot filename templates
  - duplicate same-month fundamentals source rows are now collapsed after month normalization so refreshed broader SEC parquet inputs satisfy the deterministic `ticker` plus month-end uniqueness contract downstream
- Disabled pytest cache-provider persistence in `pyproject.toml` because this workspace was producing access-denied cache fallbacks under the repo root.

## Testing Status

- `tests/data/test_data_pipeline.py` now covers:
  - monthly resampling logic
  - monthly return calculation
  - duplicate key detection
  - benchmark alignment
  - one-row-per-ticker-per-month validation
  - fundamentals lagged monthly merge behavior
  - fundamentals monthly alignment when some universe tickers have no fundamentals history
  - object-backed datetime/null coercion in `month_difference()`
  - equal-weight benchmark construction
  - research-scale raw-file selection preference and fallback behavior
  - research-scale fallback when headerless empty non-sample CSVs are present
  - raw-file manifest enrichment with per-file provenance and observed raw coverage
- `tests/data/test_remote_fetch.py` now covers:
  - remote fetch config loading
  - output naming and manifest path construction
  - dataset manifest JSON writing
  - stdout-first CLI stream handler selection
  - fetch frame-summary and aggregated symbol-summary helpers
  - Alpha Vantage daily-quota detection
  - zero-row output write skipping
  - SEC gzip response decoding
  - Alpha Vantage monthly adjusted response parsing
  - Alpha Vantage overview response parsing
  - SEC ticker-to-CIK parsing
  - SEC user-agent resolution
  - SEC Company Facts conservative mapping logic
- `tests/data/test_remote_fetch.py` now also covers:
  - sparse SEC concept coverage where optional metrics are absent
  - raw SEC manifest-path resolution when snapshot templates include a `{symbol}` placeholder
- `tests/test_repo_skeleton.py` was updated so the data-stage CLIs are tested as implemented runners rather than scaffold-only stubs.
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `74 passed` on 2026-03-30.
- `.\.venv\Scripts\python.exe -m pytest -q tests/data/test_data_pipeline.py` passed with `13 passed` on 2026-04-13 after the fundamentals datetime/null-handling fix.
- `.\.venv\Scripts\python.exe -m pytest -q tests/test_repo_skeleton.py::test_data_ingestion_cli_supports_research_scale_mode` passed on 2026-04-13 after the same fix restored the `research_scale` ingestion smoke path.
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `79 passed` on 2026-04-13.
- `.\.venv\Scripts\python.exe -m pytest -q tests/data/test_data_pipeline.py tests/data/test_remote_fetch.py` passed with `30 passed` on 2026-04-13 after the Stage 3 sparse-SEC, raw-manifest-path, and duplicate-month fundamentals fixes.
- `.\.venv\Scripts\python.exe -m pytest -q` passed with `85 passed` on 2026-04-13 after the same Stage 3 fixes.

## Manual Verification Status

- `.\.venv\Scripts\python.exe -m src.run_data_ingestion` completed successfully on 2026-03-28.
- `.\.venv\Scripts\python.exe -m src.run_panel_assembly` completed successfully on 2026-03-28.
- `.\.venv\Scripts\python.exe -m src.run_fetch_remote_raw --help` completed successfully on 2026-03-30.
- `powershell -NoProfile -Command "[scriptblock]::Create((Get-Content 'scripts\run_remote_refresh_and_research_scale.ps1' -Raw)) | Out-Null; Write-Output 'parsed'"` completed successfully on 2026-03-30.
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion` completed successfully on 2026-03-30 after the remote-fetch implementation.
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion` completed successfully on 2026-04-13 after the fundamentals datetime/null-handling fix.
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion --execution-mode research_scale` completed successfully on 2026-03-30.
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion --execution-mode research_scale` completed successfully on 2026-04-13 after the fundamentals datetime/null-handling fix.
- `.\.venv\Scripts\python.exe -m pytest -q tests/data/test_remote_fetch.py` completed successfully on 2026-03-30 after the fetch logging patch.
- `.\.venv\Scripts\python.exe -m pytest -q tests/data/test_data_pipeline.py tests/data/test_remote_fetch.py` completed successfully on 2026-03-30 after the empty-CSV fallback hardening.
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion` completed successfully on 2026-03-30 after the fetch logging patch.
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion --execution-mode research_scale` completed successfully on 2026-03-30 after the empty-CSV fallback hardening restored seeded fallback.
- Running `scripts/run_remote_refresh_and_research_scale.ps1` with `ALPHAVANTAGE_API_KEY`, `SEC_USER_AGENT`, and `SEC_CONTACT_EMAIL` intentionally unset produced `wrapper_exit_code=1` and wrote an explicit error block to `.cache/logs/remote_refresh_research_scale_20260331T035813Z.log` on 2026-03-31 UTC.
- `.\.venv\Scripts\python.exe -m src.run_fetch_remote_raw --provider alphavantage_sec --execution-mode research_scale` was manually exercised with live credentials on 2026-03-31 and surfaced two concrete provider-side edge cases before this patch: Alpha Vantage daily quota exhaustion after `5` overview symbols and a SEC gzip decode failure.
- `.\.venv\Scripts\python.exe -m pytest -q tests/data/test_remote_fetch.py` completed successfully on 2026-03-31 after the SEC gzip and Alpha Vantage quota patch.
- `.\.venv\Scripts\python.exe -m pytest -q` completed successfully on 2026-03-31 with `77 passed`.
- `powershell -NoProfile -Command "[scriptblock]::Create((Get-Content 'scripts\import_remote_provider_env.ps1' -Raw)) | Out-Null; [scriptblock]::Create((Get-Content 'scripts\run_remote_refresh_and_research_scale.ps1' -Raw)) | Out-Null; Write-Output 'parsed'"` completed successfully on 2026-03-31 after the repo-local credential loader was added.
- `.\.venv\Scripts\python.exe -m src.run_panel_assembly --execution-mode research_scale` completed successfully on 2026-03-30.
- Output row counts and QC summaries were manually reviewed for consistency with the seeded universe and sample date range.
- Research-scale verification confirmed that broader local raw files were absent and that the new sample-fallback manifest fields were populated correctly.
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion --execution-mode research_scale` was rerun successfully on 2026-03-30 after the provenance upgrade.
- The refreshed dataset QC summaries now show the observed seeded fallback coverage:
  - `prices_daily_sample.csv`: `2580` raw rows, raw date span `2024-01-02` to `2024-06-28`
  - `benchmarks_daily_sample.csv`: `258` raw rows, raw date span `2024-01-02` to `2024-06-28`
  - `fundamentals_quarterly_sample.csv`: `60` raw rows, raw date span `2023-09-30` to `2024-03-31`
- Live provider fetches were not manually executed on 2026-03-30 because this workspace verification pass did not include Alpha Vantage credentials or SEC identity values.
- Live provider fetches were also not exercised during the 2026-03-31 UTC wrapper failure-path check because provider credentials were intentionally unset to test the preflight logging path only.
- A live provider run on 2026-03-31 did confirm that the Alpha Vantage free key daily quota can be exhausted mid-run for the configured symbol list, so broader-history refreshes remain constrained by provider limits even though the crash/empty-write handling is now fixed.
- `powershell -ExecutionPolicy Bypass -File .\scripts\run_remote_refresh_and_research_scale.ps1` was executed on 2026-04-13 with live credentials available through the repo-local PowerShell helper.
- The 2026-04-13 live refresh verified the exact provider outcomes:
  - Alpha Vantage overview metadata succeeded for all `20` configured universe symbols and wrote refreshed latest plus snapshot CSV outputs under `data/raw/fundamentals/metadata/`
  - Alpha Vantage monthly market prices failed on the first `AAPL` request with the provider's quota/throttle message and wrote only the dataset manifest under `data/raw/market/manifests/`
  - Alpha Vantage benchmark prices were skipped after the earlier quota detection and wrote only the dataset manifest under `data/raw/benchmarks/manifests/`
  - SEC Company Facts completed for all `20` configured universe symbols and wrote refreshed latest plus snapshot parquet outputs and `20` raw JSON payload snapshots under `data/raw/fundamentals/`
- The same 2026-04-13 run exposed a local `KeyError: 'symbol'` in `_resolve_manifest_path()` for the raw SEC manifest path. That bug is now fixed, but the fetch CLI was not rerun after the patch because the Alpha Vantage key had already hit its quota condition for the day.
- `.\.venv\Scripts\python.exe -m src.run_data_ingestion --execution-mode research_scale` initially failed on 2026-04-13 because the refreshed SEC parquet produced duplicate same-month source rows after month normalization. After the duplicate-collapse fix, the command completed successfully.
- The full deterministic downstream `research_scale` chain completed successfully on 2026-04-13 after those fixes:
  - `.\.venv\Scripts\python.exe -m src.run_data_ingestion --execution-mode research_scale`
  - `.\.venv\Scripts\python.exe -m src.run_panel_assembly --execution-mode research_scale`
  - `.\.venv\Scripts\python.exe -m src.run_feature_generation --execution-mode research_scale`
  - `.\.venv\Scripts\python.exe -m src.run_signal_generation --execution-mode research_scale`
  - `.\.venv\Scripts\python.exe -m src.run_backtest --execution-mode research_scale`
  - `.\.venv\Scripts\python.exe -m src.run_evaluation_report --execution-mode research_scale`
- Manual inspection of the refreshed data-stage QC outputs on 2026-04-13 confirmed:
  - `prices_monthly` still used seeded fallback from `prices_daily_sample.csv`
  - `benchmarks_monthly` still used seeded fallback from `benchmarks_daily_sample.csv`
  - `fundamentals_monthly` selected broader local raw from `fundamentals_quarterly_sec_companyfacts.parquet`
  - the broader raw fundamentals file now contains `1386` quarterly rows with observed date coverage from `2006-09-30` through `2026-03-25`
- Repo-local `src/` and `tests/` `__pycache__` directories were moved into `.cache/cleanup_archive/20260331T032749Z/python_bytecode/` on 2026-03-30.
- Legacy root-level `pytest-cache-files-*` directories remained in place on 2026-03-30 because the current shell received `Access is denied` when attempting to move them.

## Known Issues / Risks

- Fundamentals are still subject to revised-history bias because the current source is not point-in-time safe.
- The downstream raw-data adapter layer is still local-file-first only by design; remote providers are upstream helpers, not downstream dependencies.
- Historical root-level `pytest-cache-files-*` clutter came from pytest cache fallback behavior after cache writes failed in this OneDrive-backed workspace.
- The new SEC Company Facts mapping is intentionally conservative and leaves some canonical valuation fields unmapped.
- The latest live Alpha Vantage refresh still did not produce usable non-sample local monthly market or benchmark files because the provider quota was exhausted before those stages could refresh.
- The 2026-04-13 deterministic `research_scale` rerun therefore remained a mixed-input exploratory run rather than a fully broader-history run.
- The equal-weight universe benchmark is intentionally simple and does not yet include execution realism.

## Immediate Next Step

- Finish Stage 3 from `docs/10_development_roadmap.md` by rerunning the Alpha Vantage monthly price refresh on a fresh quota window so `data/raw/market/` and `data/raw/benchmarks/` gain usable non-sample latest files, then rerun the downstream `research_scale` pipeline and confirm the selected-input profile is no longer mixed.
