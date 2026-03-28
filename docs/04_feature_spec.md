# 04 Feature Specification

## Feature-Building Objective

The first implemented feature set is intentionally simple and leakage-safe enough to support later deterministic ranking baselines. It starts from `outputs/data/monthly_panel.parquet` and writes:

- `outputs/features/feature_panel.parquet`
- `outputs/features/feature_qc_summary.json`
- `outputs/features/feature_missingness_summary.csv`

## Current Lag Policy

- Price features use only returns or prices available through `t-1` for a decision at month `t`.
- Fundamentals-based features use the mapped monthly panel fields and then apply one additional one-period lag before inclusion in the feature panel.
- Any feature depending on historically revised fundamentals still carries revised-history risk because the source is not point-in-time safe.

## Implemented Feature Families

### Price And Momentum

| Feature | Formula | Lookback | Lag Rule |
| --- | --- | --- | --- |
| `ret_1m_lag1` | `monthly_return_{t-1}` | 1 month | use `t-1` only |
| `mom_3m` | `(1+r_{t-3})(1+r_{t-2})(1+r_{t-1}) - 1` | 3 months | exclude current month |
| `mom_6m` | compounded prior 6 monthly returns | 6 months | exclude current month |
| `mom_12m` | compounded prior 12 monthly returns | 12 months | exclude current month |
| `drawdown_12m` | `adjusted_close_{t-1} / max(adjusted_close_{t-12:t-1}) - 1` | 12 months | use data through `t-1` |
| `vol_12m` | rolling std of lagged monthly returns | 12 months | use prior returns only |
| `beta_12m_spy` | rolling covariance with lagged `SPY` returns divided by rolling `SPY` variance | 12 months | use prior returns only |
| `adjusted_close_lag1` | prior month adjusted close | 1 month | use `t-1` only |
| `benchmark_return_lag1` | prior month primary benchmark return | 1 month | use `t-1` only |

### Market Cap

Implemented:

- `market_cap_lag1`

Rule:

- use the monthly panel’s mapped market-cap field and shift it one additional monthly period before inclusion

### Valuation

Implemented:

- `pe_ratio_lag1`
- `price_to_sales_lag1`
- `price_to_book_lag1`
- `ev_to_ebitda_lag1`

Rule:

- use raw monthly panel ratios and shift them one additional month

### Profitability And Quality

Implemented:

- `gross_margin_lag1`
- `operating_margin_lag1`
- `roe_lag1`
- `roa_lag1`

### Growth

Implemented:

- `revenue_growth_lag1`
- `eps_growth_lag1`

### Balance Sheet

Implemented:

- `debt_to_equity_lag1`
- `current_ratio_lag1`

### Revision Signals

Not implemented:

- revision features remain disabled in `config/features.yaml`

## Missingness And QC

- `numeric_fill: none` is enforced, so numeric feature values are not silently imputed.
- `categorical_fill: missing` is applied to `sector` and `industry` metadata only.
- Missingness is summarized both overall and by date in `feature_qc_summary.json`.
- Per-feature missingness rates and first valid dates are written to `feature_missingness_summary.csv`.

Expected current behavior on short histories:

- long-lookback price features such as `mom_12m`, `drawdown_12m`, `vol_12m`, and `beta_12m_spy` can remain entirely missing on short sample windows
- this is expected and should be visible in QC rather than hidden by imputation

## Current Config Controls

`config/features.yaml` currently controls:

- enabled feature families
- rolling lookback windows
- default lag periods
- fundamentals lag periods
- benchmark used for beta features
- missingness policy

## Forbidden Predictors

These still must not appear as predictive inputs unless explicitly justified and documented:

- forward returns
- future benchmark-relative labels
- hand-curated outcomes
- identifiers that leak future membership or outcomes
- any field published after the decision date

## Known Bias Risk

- Fundamentals-based features inherit revised-history risk because the current upstream fundamentals source is not point-in-time safe.
- The implemented lag policy is conservative, but it does not eliminate that risk.
