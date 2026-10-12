---
doc_kind: requirement
canonical_id: financial-representations
purpose: [requirement, reinforcement]
rank: high
topics: [financial, representations, registry, check-profiles]
rag_keywords: [financial-representations, portfolio, dcf, var, xbrl, comps, tax-loss-harvest]
---

# Financial representations standard

## Scope and purpose

This standard establishes the normative taxonomy of quantitative financial representations recognized by `financial-advisement-router`. Each representation defines an authoritative asset family, aliases, adjacent routes, asset types, and mandatory check profiles.

Machine-readable mapping is codified in [`financial-representation-registry.json`](./financial-representation-registry.json).

## Representation matrix

### 1. Portfolio allocations (`portfolio_allocation`)
Covers target asset weights, mean-variance quadratic programming, and Black-Litterman allocations.
- **Check profiles**: `decimal_ledger`, `reg_bi_compliance`.
- **Key controls**: Weight vector normalization ($\sum w_i = 1.0$), non-negative bounds for long-only profiles, and covariance matrix positive semi-definiteness.

### 2. DCF valuation schedules (`dcf_schedule`)
Covers unlevered and levered discounted cash flow valuation models.
- **Check profiles**: `decimal_ledger`, `reg_bi_compliance`.
- **Key controls**: WACC discount calculation, Gordon growth terminal value bounds ($g \le \text{GDP growth}$), explicit sensitivity matrices, and pure Decimal math.

### 3. Value-at-risk and stress simulations (`var_risk_simulation`)
Covers parametric, historical, and Monte Carlo VaR / Expected Shortfall (CVaR).
- **Check profiles**: `var_cvar_metric`, `reg_bi_compliance`.
- **Key controls**: 95% and 99% one-tailed confidence horizons, explicit PRNG seed verification, tail risk metrics, and FINRA Rule 2214 hypothetical legends.

### 4. Three-statement accounting models (`three_statement_model`)
Covers integrated income statement, balance sheet, and cash flow schedules.
- **Check profiles**: `decimal_ledger`, `reg_bi_compliance`.
- **Key controls**: Balance sheet identity ($Assets = Liabilities + Equity$), cash flow reconciliation to balance sheet cash, and zero floating-point residues.

### 5. SEC EDGAR XBRL filings (`sec_xbrl_statement`)
Covers parsed corporate facts from official SEC submissions (Forms 10-K, 10-Q, 8-K).
- **Check profiles**: `xbrl_integrity`.
- **Key controls**: CIK 10-digit padding, US GAAP taxonomy concept matching, instant vs duration period handling, and rate limit compliance (max 10 req/s).

### 6. Portfolio drift and rebalancing ledgers (`rebalancing_drift`)
Covers allocation drift tracking, rebalancing trade generation, and cash drag monitoring.
- **Check profiles**: `decimal_ledger`, `reg_bi_compliance`.
- **Key controls**: Rebalancing bands, transaction cost friction modeling, and conservation of total account value.

### 7. Tax-loss harvesting ledgers (`tax_loss_harvest`)
Covers identifying loss positions and IRS wash-sale 30-day window violations.
- **Check profiles**: `decimal_ledger`, `reg_bi_compliance`.
- **Key controls**: 30-day pre/post sale window tracking, substantially identical security checks, and replacement asset selection.

### 8. Comparable company benchmarks (`comps_benchmark`)
Covers trading and transaction multiple tables (EV/EBITDA, P/E, EV/Revenue).
- **Check profiles**: `decimal_ledger`, `reg_bi_compliance`.
- **Key controls**: Peer group harmonization, enterprise value reconciliation, and harmonic mean multiple calculation.
