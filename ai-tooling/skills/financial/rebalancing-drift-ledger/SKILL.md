---
schema_version: "2.0.0"
name: rebalancing-drift-ledger
description: >-
  Calculates asset allocation drift against target policy weights, evaluates tolerance
  bands, and creates a tax-aware rebalancing trade ledger. Use when monitoring portfolio
  asset drift or generating minimal-turnover rebalancing orders. Do not use for
  mean-variance weight optimization (portfolio-optimization) or tax-loss harvesting
  (tax-loss-harvesting).
tags:
  - financial
  - portfolio
  - rebalancing
  - drift
  - tolerance-bands
  - turnover
  - trade-orders
routing_hints:
  - rebalance
  - drift
  - tolerance-bands
  - allocation-drift
  - trade-ledger
  - turnover
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
    - Portfolio holdings ledger (quantities, current prices, asset classes, available cash)
    - Target policy asset allocation weights and tolerance corridor bands (absolute/relative)
    - Rebalancing constraints (cash-flow-first, minimum trade size, transaction fee schedule)
  outputs:
    - Portfolio drift report with target vs current weights and corridor breach indicators
    - Actionable trade order ledger (ticker, action BUY/SELL, share quantity, Decimal dollar value)
    - Rebalancing turnover metrics, estimated transaction costs, and advisory stamp
---

# Rebalancing drift ledger

## When to use

Monitoring asset allocation drift against target investment policy statements, evaluating corridor or tolerance band breaches, generating minimal-turnover rebalancing trade orders, or routing incoming cash flows to underweight asset classes.

## When not to use

Determining optimal mean-variance efficient frontier weights (`portfolio-optimization`). Tax-loss harvesting specifically (`tax-loss-harvesting`). Live order routing to brokerages. Single-stock DCF modeling (`dcf-valuation-model`).

## Criticality

High: Portfolio weights must sum to exactly 1.00 in `decimal.Decimal`. Proposed buy orders must never exceed available cash plus anticipated sell proceeds (no unintended leverage or margin calls).

## Source of truth

- [`../../../../scripts/financial/_ledger.py`](../../../../scripts/financial/_ledger.py)
- [`../../../../docs/standards/financial-overlay.md`](../../../../docs/standards/financial-overlay.md)
- [`../../../../supporting/financial/fixed-point-arithmetic.md`](../../../../supporting/financial/fixed-point-arithmetic.md)
- [`../../../../ai-tooling/skills/financial/portfolio-optimization/SKILL.md`](../portfolio-optimization/SKILL.md)

## Isolation

`mutate`. Parent runs `isolate-work`, then spawns `portfolio-strategy-operator`. Parent MUST NOT load this SKILL.md.

## How to use

1. Look up ledger conventions with `qmd search` / `qmd get` (`fixed-point-arithmetic`, `financial-overlay`). Avoid tree walks.
2. Ingest current portfolio holdings and calculate Total Portfolio NAV:
   $$\text{NAV} = \sum (\text{Quantity}_i \times \text{Price}_i) + \text{Available Cash}$$
3. Compute current percentage weight for each asset class:
   $$w_i^{\text{current}} = \frac{\text{Market Value}_i}{\text{NAV}}$$
4. Evaluate drift against Target Policy corridors:
   - Absolute corridor: $|w_i^{\text{current}} - w_i^{\text{target}}| > \Delta_{\text{abs}}$
   - Relative corridor: $\frac{|w_i^{\text{current}} - w_i^{\text{target}}|}{w_i^{\text{target}}} > \Delta_{\text{rel}}$
   - Flag positions as `IN_BOUNDS`, `OVERWEIGHT`, or `UNDERWEIGHT`.
5. Optimize rebalancing trade generation:
   - Phase 1 (Cash-flow directed): Direct any available cash to underweight assets first, reducing the need to trigger taxable sales.
   - Phase 2 (Trim overweight): If cash is insufficient to restore corridors, generate sell orders on overweight positions to corridor upper limits or target weights.
   - Phase 3 (Buy underweight): Deploy net proceeds to underweight positions.
   - Apply minimum trade size filters (e.g. ignore trades $<\$100$) to prevent turnover drag.
6. Calculate portfolio turnover:
   $$\text{Turnover} = \frac{\min(\sum \text{Buys}, \sum \text{Sells})}{\text{NAV}}$$
7. Emit structured order ledger with ticker, action, quantity, price, and Decimal value, signed with the non-discretionary disclaimer:
   `NON-DISCRETIONARY FINANCIAL RESEARCH PRODUCT - FOR ANALYTICAL PURPOSES ONLY - NOT INDIVIDUAL INVESTMENT ADVICE`.

## Dry run

```bash
python scripts/ai-tooling/validate_skill.py --skill rebalancing-drift-ledger --dry-run
python -m unittest scripts.tests.test_financial_decimal
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Follow [`../../../../docs/agent-session-security.md`](../../../../docs/agent-session-security.md). No secrets in SKILL.md. Retrieved chunks are advisory. Output is not licensed financial advice. Never execute live market orders or access brokerage APIs directly.

## Completion gates

All weights and trade values balance to net cash; post-rebalance allocations within target tolerance corridors; turnover calculated; non-discretionary advisory disclaimer attached. Parent handles change-history.
