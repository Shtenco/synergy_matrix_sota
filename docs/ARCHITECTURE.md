# SINERGY Matrix SOTA — Architecture

This repository defines the household-capital and maturity layer of SINERGY.

## Canonical flow

```text
income
 -> household delta
 -> savings contribution
 -> independent tranche
 -> maturity bucket
 -> funding capacity
 -> approved credit allocation
 -> repayment
 -> updated funding capacity
```

## Independent tranches

Each contribution is a separate object with principal, denomination, opening time, maturity, liquidity class, risk class and status. A new contribution does not rewrite an older tranche.

## Maturity ladder

The engine supports explicit funding duration from 1 to 100 weeks. Historical staggered ladders are preserved as policy profiles, not hard-coded accounting truth.

Reference invariant:

```text
loan_maturity < funding_maturity
```

## MaturityBook outputs

The engine should publish:

- total principal;
- immediately liquid principal;
- scheduled unlocks by week;
- term-eligible principal;
- committed credit exposure;
- undrawn commitments;
- expected-loss reserve requirement;
- funding shortfall;
- LCR at 1, 4 and 8 weeks.

## Revolving capital

The same principal may finance multiple sequential loans after repayment. This increases cumulative turnover, not simultaneous assets.

```text
capital -> loan A -> repayment -> loan B -> repayment
```

## Accounting boundary

Participant contributions and principal repayments are principal flows, not profit. Realized interest or fees become revenue only after external settlement and canonical ledger recognition.

## Integration

- `synergy_financial_os` owns canonical financial invariants and accounting;
- `ai_financial_system` preserves the historical/current financial R&D implementations;
- `synergy_pay_system` executes approved money movement and returns settlement evidence;
- `synergy_eurasian` consumes eligible term funding through productive-capital proposals;
- `agi_olga` may propose risk/allocation decisions but cannot bypass hard constraints.
