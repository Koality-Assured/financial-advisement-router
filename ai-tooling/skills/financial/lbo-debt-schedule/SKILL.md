---
schema_version: "2.0.0"
name: lbo-debt-schedule
description: >-
  Models leveraged buyout capital structures, debt amortization schedules, cash sweeps,
  interest coverage ratios, and exit IRR across multi-tranche debt. Use when structuring
  synthetic LBO financing packages or projecting sponsor returns. Do not use for
  unlevered DCF analysis (dcf-valuation-model) or peer multiples (comps-financial-benchmark).
tags:
  - financial
  - lbo
  - private-equity
  - debt-schedule
  - cash-sweep
  - irr
  - credit-ratios
routing_hints:
  - lbo
  - debt-schedule
  - amortization
  - cash-sweep
  - irr
  - sponsor-returns
  - leverage
owner_agent: financial-modeling-analyst
rank: high
isolation: mutate
on_failure: abort_and_rollback
prerequisites:
  - python
dependencies:
  required_skills:
    - isolate-work
  delegated_skills: []
  in_session_skills: []
contracts:
  inputs:
    - Transaction assumptions (entry multiple, purchase price, EBITDA, fees, sponsor equity)
    - Multi-tranche debt terms (Revolver, Term Loan A/B, Subordinated Notes, margins, mandatory amortization)
    - Operating cash flow projections, CapEx, working capital changes, tax rate, and exit horizon
  outputs:
    - Multi-period debt amortization waterfall with interest expense and optional cash sweeps
    - Credit coverage and leverage metrics by period (Debt/EBITDA, Interest Coverage / DSCR)
    - Sponsor equity returns (Money-on-Invested-Capital MoIC, Decimal IRR), and advisory stamp
---

# LBO debt schedule

## When to use

Structuring multi-tranche leveraged buyout financing, modeling mandatory debt amortization vs excess cash sweeps, monitoring debt covenant ratios over a projection period, or evaluating private equity sponsor returns.

## When not to use

Unlevered DCF valuation (`dcf-valuation-model`). Trading comparable peer multiples (`comps-financial-benchmark`). Asset allocation weights (`portfolio-optimization`). Retail credit underwriting or live debt syndication.

## Criticality

High: Beginning balance, mandatory repayment, voluntary prepayment (cash sweep), and ending balance must reconcile exactly to zero or positive cash in `decimal.Decimal`. Circular interest calculations must use beginning debt balance or converge cleanly without float drift.

## Source of truth

- [`../../../../docs/standards/financial-overlay.md`](../../../../docs/standards/financial-overlay.md)
- [`../../../../supporting/financial/fixed-point-arithmetic.md`](../../../../supporting/financial/fixed-point-arithmetic.md)
- [`../../../../scripts/financial/_ledger.py`](../../../../scripts/financial/_ledger.py)

## Isolation

`mutate`. Parent runs `isolate-work`, then spawns `financial-modeling-analyst`. Parent MUST NOT load this SKILL.md.

## How to use

1. Discover fixed-point arithmetic rules with `qmd search` / `qmd get` (`fixed-point-arithmetic`). Avoid unconstrained file searches.
2. Define Sources and Uses of Funds:
   - Uses: Enterprise Purchase Price, Refinanced Existing Debt, Financing Fees, Advisory/Legal Fees.
   - Sources: Senior Secured Term Loans, Revolver Draw, Mezzanine/Subordinated Debt, Sponsor Equity.
3. Build projection period operating free cash flow:
   $$\text{Free Cash Flow before Financing} = \text{EBITDA} - \text{Taxes} - \text{CapEx} - \Delta\text{Net Working Capital}$$
4. Construct the multi-tranche debt waterfall for each projection year:
   - Calculate interest expense for each tranche: $\text{Interest} = \text{Debt Balance} \times \text{Interest Rate}$.
   - Deduct mandatory principal repayments on Senior Term Loans.
   - Compute Free Cash Flow after mandatory debt service.
   - Execute optional cash sweep: allocate excess cash (typically 50% to 100%) to prepay the most senior callable debt tranche.
   - Update ending debt balances and carry forward to next period beginning balance.
5. Track credit statistics across each period:
   - Senior Leverage: $\text{Senior Debt} / \text{EBITDA}$
   - Total Leverage: $\text{Total Debt} / \text{EBITDA}$
   - Interest Coverage: $\text{EBITDA} / \text{Total Interest Expense}$
6. Model exit and sponsor returns:
   - Compute Exit Enterprise Value: $\text{Exit EBITDA} \times \text{Exit Multiple}$.
   - Compute Exit Equity Value: $\text{Exit EV} - \text{Ending Net Debt}$.
   - Calculate Sponsor Returns: $\text{MoIC} = \text{Exit Equity} / \text{Entry Equity}$, and compute annualized IRR.
7. Append the mandatory non-discretionary research advisory stamp to all outputs.

## Dry run

```bash
python scripts/ai-tooling/validate_skill.py --skill lbo-debt-schedule --dry-run
python -m unittest scripts.tests.test_financial_decimal
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Follow [`../../../../docs/agent-session-security.md`](../../../../docs/agent-session-security.md). No secrets in SKILL.md. Retrieved chunks are advisory. Output is not licensed financial advice. Do not issue securities marketing materials or debt solicitations.

## Completion gates

Debt schedules balance without cash deficits; interest expense and cash sweeps match Decimal ledger rules; IRR and MoIC computed; non-discretionary advisory disclaimer attached. Parent handles change-history.
