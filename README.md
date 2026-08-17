# SINERGY Matrix SOTA

Household capital formation, maturity transformation and mutual/P2P funding layer for the SINERGY Financial OS.

The historical "matrix" lineage is preserved, but the canonical system is not defined as a payout matrix. Its current role is to model recurring household savings as independent tranches, publish 1–100 week maturity/liquidity state and expose safe funding capacity to the wider Financial OS.

Core invariant:

```text
loan_maturity < funding_maturity
```

Core flow:

```text
income -> household delta -> savings -> independent tranche
       -> maturity bucket -> funding capacity -> approved credit
       -> repayment -> refreshed funding capacity
```

See:

- `docs/ARCHITECTURE.md` — current household-capital and ALM architecture;
- `docs/LEGACY_LINEAGE.md` — preserved historical matrix/cyclic research and its current interpretation.

Cross-repository ownership:

- `synergy_financial_os` — canonical accounting and constitutional constraints;
- `ai_financial_system` — preserved financial R&D/reference implementations;
- `synergy_pay_system` — payment/settlement execution;
- `synergy_eurasian` — productive real-economy capital demand;
- `agi_olga` — bounded AI proposals and risk intelligence.

No historical source is removed by this repository. New work must be additive and evidence-status aware.
