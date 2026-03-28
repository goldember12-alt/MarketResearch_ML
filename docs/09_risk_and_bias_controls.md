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
- meaningful evaluation-report runs must append to `outputs/reports/experiment_registry.jsonl`
- schema changes and feature additions must update docs and progress files

## Currently Implemented Controls

- lagged feature construction and deterministic signal scoring
- holdings formed at month-end `t` only earn returns realized at month-end `t+1`
- duplicate-key, holdings-weight, and benchmark-alignment validation in the backtest stage
- explicit transaction cost and slippage settings in config
- explicit benchmark comparison tables and report language
- strategy reports that include bias caveats directly in the output

## Current Known Weak Spot

Point-in-time safety for fundamentals is not yet solved. Until it is, any deterministic or ML result using those fields must include a revised-history caveat.

## Reporting Rule

No strategy result may be presented without:

- explicit benchmark context
- transaction cost assumptions
- the holding-period convention
- a note on likely bias sources and the controls currently in place
