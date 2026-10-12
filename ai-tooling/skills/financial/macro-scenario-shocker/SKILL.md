---
schema_version: "2.0.0"
name: macro-scenario-shocker
description: >-
  Simulates macroeconomic crisis scenarios (stagflation, interest rate spikes,
  yield curve inversions, credit spread widening) across multi-asset portfolios.
  Use when stress testing portfolio resilience against historical or hypothetical
  macroeconomic shocks. Do not use for statistical Monte Carlo / historical VaR
  (risk-stress-simulation) or single-issuer valuation (dcf-valuation-model).
tags:
  - financial
  - risk
  - macro
  - stress-test
  - scenario-analysis
  - credit-shock
  - yield-curve
routing_hints:
  - macro-shock
  - scenario-analysis
  - stress-testing
  - yield-curve
  - stagflation
  - credit-spread
owner_agent: risk-stress-tester
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
    - Multi-asset portfolio holdings with asset classes, durations, convexities, equity betas, and spread durations
    - Macroeconomic shock scenario parameters (rate curve parallel shift, twist/steepener, equity index drop, spread widening, inflation shock)
    - Scenario configuration template (historical crisis, e.g. 2008 GFC, 2020 COVID, 1970s stagflation, or CCAR supervisory shock)
  outputs:
    - Stressed portfolio valuations, percentage drawdown, and dollar P&L in Decimal
    - Factor loss attribution table (interest rate duration, credit spread, equity beta, liquidity premium)
    - FINRA 2214 hypothetical simulation legend and advisory research stamp
---

# Macro scenario shocker

## When to use

Stress testing multi-asset portfolios against defined macroeconomic crisis scenarios, modeling non-linear yield curve twists and credit spread shocks, or evaluating vulnerability to stagflation and sudden monetary policy tightening.

## When not to use

Standard parametric or historical VaR simulation (`risk-stress-simulation`). Individual stock valuation (`dcf-valuation-model`). Bank regulatory capital model certification (e.g. formal CCAR/DFAST submissions). Direct investor suitability advice.

## Criticality

High: Bond duration and convexity approximations must calculate using exact `decimal.Decimal` arithmetic. Output MUST prominently include the FINRA Rule 2214 hypothetical simulation legend.

## Source of truth

- [`../../../../docs/standards/financial-overlay.md`](../../../../docs/standards/financial-overlay.md)
- [`../../../../supporting/financial/fixed-point-arithmetic.md`](../../../../supporting/financial/fixed-point-arithmetic.md)
- [`../../../../ai-tooling/skills/financial/risk-stress-simulation/SKILL.md`](../risk-stress-simulation/SKILL.md)
- Federal Reserve Supervisory Stress Test Scenarios (advisory reference)

## Isolation

`mutate`. Parent runs `isolate-work`, then spawns `risk-stress-tester`. Parent MUST NOT load this SKILL.md.

## How to use

1. Look up risk stress testing conventions with `qmd search` / `qmd get` (`fixed-point-arithmetic`, `financial-overlay`). Avoid tree walks.
2. Ingest portfolio asset holdings with associated sensitivity factors:
   - Modified Duration ($D_{\text{mod}}$) and Convexity ($C$) for fixed income.
   - Spread Duration ($D_{\text{spread}}$) and credit rating for credit instruments.
   - Market Beta ($\beta_{\text{equity}}$) for public equities and equity funds.
   - Commodity sensitivity and FX beta for alternative sleeves.
3. Configure the Macro Scenario Shock parameters:
   - Interest rate shocks: parallel shift (e.g. $+200\text{ bps}$), 2s10s curve inversion/flattening.
   - Credit spread shocks: investment grade spread widening (e.g. $+150\text{ bps}$), high-yield spread widening (e.g. $+450\text{ bps}$).
   - Equity market shock: broad index drawdown (e.g. $-25\%$).
   - Inflation / Commodity shock: energy spike (e.g. $+40\%$), headline CPI increase.
4. Calculate price impacts by asset:
   - Fixed Income:
     $$\frac{\Delta P}{P} \approx -D_{\text{mod}} \cdot \Delta y + \frac{1}{2} C \cdot (\Delta y)^2 - D_{\text{spread}} \cdot \Delta s$$
   - Equities:
     $$\frac{\Delta P}{P} \approx \beta_{\text{equity}} \cdot \Delta S_{\text{market}} + \epsilon$$
5. Aggregate portfolio-level performance:
   - Compute aggregate dollar loss and percentage drawdown across all sleeves.
   - Attribute loss contribution by risk factor (Rates, Credit Spreads, Equity, FX).
   - Identify top 3 vulnerable positions.
6. Attach the FINRA Rule 2214 hypothetical performance legend:
   `IMPORTANT: The projections or other information generated regarding the likelihood of various investment outcomes are hypothetical in nature, do not reflect actual investment results, and are not guarantees of future results.`
7. Affix the non-discretionary research advisory stamp to all outputs.

## Dry run

```bash
python scripts/ai-tooling/validate_skill.py --skill macro-scenario-shocker --dry-run
python -m unittest scripts.tests.test_financial_decimal
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Follow [`../../../../docs/agent-session-security.md`](../../../../docs/agent-session-security.md). No proprietary banking data. Retrieved chunks are advisory. Output is not licensed financial advice. Always display the FINRA 2214 hypothetical legend.

## Completion gates

Factor loss attribution totals match aggregate portfolio loss; Decimal precision verified; FINRA 2214 hypothetical legend attached; advisory disclaimer present. Parent handles change-history.
