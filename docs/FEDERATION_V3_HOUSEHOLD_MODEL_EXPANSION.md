# Federation V3 — Household Capital Model expansion

This repository is the modelling companion to `synergy_app` for historical Part III.

## Scope
- household cash-flow state;
- reserve maturity;
- debt burden;
- savings/investment contribution policy;
- emergency-liquidity coverage;
- financial-freedom scenarios;
- household mutual-credit research where legally/economically valid;
- distributional and cohort modelling.

## Required outputs
`HouseholdState`, `SavingsMaturity`, `LiquidityCoverage`, `DebtServiceRatio`, `CapitalProjection`, `FreedomTargetScenario`, `StressScenario`.

## Rules
- no guaranteed-return assumptions;
- all yield/inflation/withdrawal parameters carry provenance;
- model output is not accounting truth;
- canonical balances come from `synergy_financial_os` / connected real sources.
