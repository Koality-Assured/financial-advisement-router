---
doc_kind: requirement
canonical_id: financial-practice
purpose: [requirement, reinforcement]
rank: high
topics: [financial, fiduciary, reg-bi, finra-2111, finra-2214, decimal]
rag_keywords: [financial-practice, non-discretionary, reg-bi, finra-2214, decimal-arithmetic, advisory-stamp]
---

# Financial practice and fiduciary safeguards

## Scope and authoritative grounding

All quantitative modeling, portfolio optimization, valuation, and market risk analysis produced within `financial-advisement-router` must conform to:
1. **SEC Regulation Best Interest (Exchange Act Rule 15l-1)**: Defining retail recommendation boundaries.
2. **FINRA Rule 2111 (Suitability)** and **FINRA Rule 2214 (Requirements on Investment Analysis Tools)**: Governs interactive simulation and outcome likelihood disclosures.
3. **Python Decimal and IEEE 754 Arithmetic Standards**: Governing monetary precision and ledger correctness.

## Non-negotiable practice rules

1. **Non-Discretionary Research Status**:
   - All deliverables are non-discretionary research products for analytical purposes only.
   - The spoke MUST NOT issue buy/sell orders, account recommendations, or personal investment advice.
   - Every deliverable MUST display the mandatory non-discretionary advisory legend.

2. **FINRA Rule 2214 Hypothetical Disclosures**:
   - Any tool or report outputting Monte Carlo simulations, probability distributions, or outcome likelihoods MUST display the mandatory FINRA 2214(c)(4) disclosure indicating results are hypothetical and not guarantees.

3. **Strict Zero-Float Decimal Standard**:
   - Financial ledgers, cash flows, portfolio weights, and share counts MUST be calculated using Python's `decimal.Decimal`.
   - Floating-point numbers (`float`, `np.float64`) are prohibited in final ledgers and valuation models.
   - Rounding mode must default to `ROUND_HALF_EVEN` unless an explicit schedule requires another.

4. **Synthetic Data and PII Prohibition**:
   - Fixtures and examples MUST use synthetic portfolio profiles, fictional accounts, and publicly available CIKs.
   - Real Non-Public Personal Information (NPI), SSNs, or live account credentials are strictly forbidden.
