# 01 Research Questions

## Primary Research Questions

1. Can a deterministic monthly ranking strategy built from valuation, profitability, growth, and lagged price features outperform `SPY`, `QQQ`, and the equal-weight universe benchmark on a risk-adjusted basis?
2. Does the comparison-group design improve robustness relative to a tech-only research lens by reducing sector concentration and drawdown sensitivity?
3. After deterministic baselines are working, do simple ML models add useful out-of-sample value relative to deterministic scores under chronology-safe validation?
4. Which feature families remain directionally useful across different market regimes without relying on future information?
5. Can a personal-investor-friendly remote acquisition stack based on Alpha Vantage plus SEC EDGAR provide sufficient breadth, auditability, and refreshability for longer-history monthly research runs?

## Initial Hypotheses

- A diversified deterministic score blending valuation, profitability, growth, and momentum features may outperform passive benchmark exposure on a risk-adjusted basis.
- The non-tech comparison group may reduce concentration risk and improve benchmark-relative interpretation, even if absolute returns are lower than a pure tech basket in strong tech regimes.
- Logistic regression and random forest models may only be worth keeping if they improve out-of-sample benchmark-relative results over deterministic rankings after transaction costs.
- Simpler models will likely be easier to validate and debug than more flexible models in the early dataset-building phase.
- The now-implemented hybrid source stack that uses Alpha Vantage for prices / classifications and SEC for filing-based fundamentals should be more attainable for a personal researcher than institution-oriented platforms, while still requiring explicit provenance and bias controls.

## Required Framing For Any Experiment

Every research question or experiment result must specify:

- date range
- universe preset
- benchmark set
- rebalance frequency
- transaction cost assumptions
- label definition if modeling is involved
- whether the run is exploratory or benchmark-grade

## Early-Phase Question Ordering

The question sequence for implementation is intentional:

1. Can we build a trustworthy monthly panel?
2. Can we refresh that panel reproducibly from attainable remote sources?
3. Can we create leakage-safe deterministic features?
4. Can a deterministic ranking baseline beat benchmarks after costs?
5. Only then: do simple ML baselines add value?

## Deferred Questions

- regime-specific stability
- sector-neutral ranking variants
- alternative holding counts and weighting rules
- broader universe definitions
- later paper-trading-style forward evaluation
