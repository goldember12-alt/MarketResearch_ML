# 09 Risk And Bias Controls

## Core Risks

- look-ahead bias in features, labels, or portfolio decisions
- survivorship bias from a hand-selected or evolving universe
- leakage from revised historical fundamentals
- data snooping through repeated unlogged experimentation
- overfitting from flexible models on a small panel
- unrealistic execution assumptions
- benchmark cherry-picking

## Required Controls

- monthly features must use only information available by the rebalance date
- train, validation, and test periods must respect chronology
- transaction cost assumptions must be explicit
- benchmark comparisons must include `SPY`, `QQQ`, and `equal_weight_universe` unless documentation changes
- experiment runs must be logged once the reporting layer is implemented
- schema changes and feature additions must update docs and progress files

## Current Known Weak Spot

Point-in-time safety for fundamentals is not yet solved. Until it is, any deterministic or ML result using those fields must include a revised-history caveat.

## Reporting Rule

No strategy result may be presented without a note on likely bias sources and the controls currently in place.
