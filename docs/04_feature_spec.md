# 04 Feature Specification

## Feature-Building Objective

The first feature set should be simple, documented, and leakage-safe enough to support deterministic ranking baselines. Feature engineering should start from the canonical monthly panel and write:

- `outputs/features/feature_panel.parquet`
- `outputs/features/feature_qc_summary.json`
- `outputs/features/feature_missingness_summary.csv`

## Default Lag Policy

- Price features use only returns or prices available through `t-1` for a decision taken at month `t`.
- Fundamentals-based features should use at least a one-period lag until point-in-time availability is established.
- Any feature depending on revised historical fields must carry a bias note in docs and reports.

## Initial Feature Families

### Price And Momentum

| Feature | Formula Sketch | Lookback | Lag Rule |
| --- | --- | --- | --- |
| `ret_1m_lag1` | prior month return | 1 month | use `t-1` only |
| `mom_3m` | compounded return over `t-3` to `t-1` | 3 months | exclude current month |
| `mom_6m` | compounded return over `t-6` to `t-1` | 6 months | exclude current month |
| `mom_12m` | compounded return over `t-12` to `t-1` | 12 months | exclude current month |
| `drawdown_12m` | prior close divided by trailing 12-month high minus 1 | 12 months | use data through `t-1` |
| `vol_12m` | std of monthly returns | 12 months | use `t-12` to `t-1` |
| `beta_12m_spy` | trailing beta versus `SPY` | 12 months | use prior returns only |

### Valuation

Initial candidates:

- `pe_ratio`
- `price_to_sales`
- `ev_to_ebitda`
- `free_cash_flow_yield`

Rules:

- prefer raw ratios from the fundamentals table
- if winsorization or ranking transforms are added later, document them explicitly
- do not use forward-looking consensus fields unless the publication timing is defensible

### Profitability And Quality

Initial candidates:

- `gross_margin`
- `operating_margin`
- `roe`
- `roa`
- `free_cash_flow_margin`

### Growth

Initial candidates:

- `revenue_growth`
- `eps_growth`
- `operating_income_growth`

### Balance Sheet

Initial candidates:

- `debt_to_equity`
- `current_ratio`
- `net_cash_indicator`

### Optional Revision Signals

Deferred unless sourcing is safe and documented:

- earnings estimate revision trend
- target-price revision trend

## Missingness And QC

- Missingness rates must be summarized by column and date.
- Fill policies must be config-driven rather than hidden in notebooks.
- The initial scaffold keeps `numeric_fill: none` in `config/features.yaml` to avoid silently masking coverage problems.

## Forbidden Predictors

These must not appear in the feature panel as predictive inputs unless explicitly justified and documented:

- forward returns
- future benchmark-relative labels
- hand-curated outcomes
- identifiers that leak future membership or outcomes
- any field published after the decision date
