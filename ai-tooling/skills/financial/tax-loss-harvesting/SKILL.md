---
schema_version: "2.0.0"
name: tax-loss-harvesting
description: >-
  Identifies unrealized capital losses across tax lots, validates IRS wash-sale rules
  (30-day window), and recommends correlated substitute securities. Use when optimizing
  taxable account tax drag or harvesting capital losses without changing target risk exposure.
  Do not use for tax preparation filings or portfolio frontier math (portfolio-optimization).
tags:
  - financial
  - tax
  - tax-loss-harvesting
  - wash-sale
  - tax-lots
  - wealth-management
routing_hints:
  - tlh
  - tax-loss
  - wash-sale
  - tax-lots
  - loss-harvesting
  - substitute-etf
owner_agent: portfolio-strategy-operator
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
    - Tax lot inventory with acquisition dates, cost basis, quantities, and current market values
    - 30-day prior/subsequent trade execution history for wash-sale detection
    - Candidate substitute security universe with correlation, tracking error, and expense ratio specs
  outputs:
    - Eligible tax loss harvest schedule detailing unrealized loss amounts in Decimal
    - Wash-sale violation flags and disqualified share lot counts per IRC Section 1091
    - Recommended substitute purchase orders to maintain asset class beta exposure, with advisory stamp
---

# Tax loss harvesting

## When to use

Scanning taxable account holdings for tax loss harvesting opportunities, verifying compliance with the 30-day IRS wash-sale rule, identifying suitable replacement proxy ETFs, and calculating after-tax alpha from realized capital losses.

## When not to use

Tax-exempt or tax-deferred accounts (e.g. 401k, IRA, where capital loss deduction does not apply). Formal tax return preparation or CPA tax filing advice. Mean-variance portfolio construction (`portfolio-optimization`). Macro stress testing (`macro-scenario-shocker`).

## Criticality

High: Strict adherence to IRC Section 1091 (wash-sale rule covering 30 days before and 30 days after the sale date, a 61-day window). Cost basis, sale proceeds, and harvested loss calculations must use exact `decimal.Decimal` arithmetic.

## Source of truth

- IRC Section 1091 (Loss from Wash Sales of Stock or Securities)
- [`../../../../docs/standards/financial-overlay.md`](../../../../docs/standards/financial-overlay.md)
- [`../../../../supporting/financial/fixed-point-arithmetic.md`](../../../../supporting/financial/fixed-point-arithmetic.md)
- [`../../../../ai-tooling/skills/financial/portfolio-optimization/SKILL.md`](../portfolio-optimization/SKILL.md)

## Isolation

`mutate`. Parent runs `isolate-work`, then spawns `portfolio-strategy-operator`. Parent MUST NOT load this SKILL.md.

## How to use

1. Discover tax guidelines and fixed-point standards with `qmd search` / `qmd get` (`fixed-point-arithmetic`, `financial-overlay`). Avoid tree walks.
2. Ingest tax lot ledger with exact purchase date, per-share cost basis, share count, and current bid/ask price in Decimal.
3. Filter lots using Highest-In, First-Out (HIFO) or Specific Identification to isolate positions with unrealized losses exceeding minimum harvest thresholds (e.g. loss > \$250 or loss > 3% of position value).
4. Conduct Wash-Sale Rule Audit (IRC Section 1091):
   - Check the 30 days preceding the intended sale date for any purchase of the same or substantially identical securities.
   - Check for pending dividend reinvestments or open option contracts that could trigger wash-sale status.
   - If wash sale occurs, mark disqualified shares and calculate disallowed loss to adjust basis of replacement shares.
5. Select Proxy / Substitute Asset:
   - Identify candidate replacement ETF or mutual fund tracking a complementary index to maintain target asset class exposure (e.g., replace S&P 500 ETF with Russell 1000 or Total US Stock Market ETF).
   - Verify that substitute is not "substantially identical" under IRS definitions.
   - Confirm high correlation ($r > 0.98$) and low tracking error to minimize portfolio benchmark drift.
6. Calculate Estimated Tax Benefit:
   $$\text{Estimated Tax Savings} = \text{Harvested Loss} \times \text{Marginal Tax Rate}$$
7. Generate trade execution plan (Sell Lot orders paired with Buy Substitute orders) and attach the mandatory research disclaimer:
   `NON-DISCRETIONARY FINANCIAL RESEARCH PRODUCT - FOR ANALYTICAL PURPOSES ONLY - NOT INDIVIDUAL INVESTMENT ADVICE`.

## Dry run

```bash
python scripts/ai-tooling/validate_skill.py --skill tax-loss-harvesting --dry-run
python -m unittest scripts.tests.test_financial_decimal
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Follow [`../../../../docs/agent-session-security.md`](../../../../docs/agent-session-security.md). No real taxpayer PII, SSNs, or live brokerage account numbers. Output is non-discretionary analytical research and does not constitute formal legal or CPA tax advice.

## Completion gates

61-day wash-sale audit completed; tax loss harvest amounts verified with Decimal arithmetic; substitute ETF mappings documented; non-discretionary advisory disclaimer attached. Parent handles change-history.
