---
schema_version: "2.0.0"
name: comps-financial-benchmark
description: >-
  Calculates comparable company valuation multiples (EV/EBITDA, EV/Revenue, P/E,
  P/B, Net Debt/EBITDA) and benchmarks synthetic peer cohorts against a target issuer.
  Use when benchmarking relative valuation multiples across peer groups or deriving
  implied valuation ranges. Do not use for intrinsic cash-flow discounting
  (dcf-valuation-model) or LBO debt waterfalls (lbo-debt-schedule).
tags:
  - financial
  - valuation
  - comps
  - multiples
  - benchmarking
  - equity-research
routing_hints:
  - comps
  - multiples
  - ev-ebitda
  - p-e
  - peer-benchmark
  - relative-valuation
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
    - Peer group financial metrics fixture (Enterprise Value, Revenue, EBITDA, Net Income, Net Debt, Share Count)
    - Target company financial metrics and peer selection criteria
    - Selected valuation multiple list and statistical aggregation method (harmonic mean, median, IQR)
  outputs:
    - Summary peer benchmarking table with 25th percentile, median, mean, and 75th percentile multiples
    - Implied target enterprise value and equity value per share range in Decimal
    - Non-discretionary research advisory stamp
---

# Comps financial benchmark

## When to use

Benchmarking peer trading multiples, calculating harmonized cohort averages, or estimating implied valuation ranges for synthetic target companies.

## When not to use

Intrinsic discounted cash flow analysis (`dcf-valuation-model`). Private equity buyout capital structure analysis (`lbo-debt-schedule`). Portfolio allocation weights (`portfolio-optimization`). Retail investment or buy/sell recommendations.

## Criticality

High: All enterprise values, share prices, and valuation multiples must use `decimal.Decimal`. Outlier multiples and distorted negative multiples (e.g. negative EBITDA or Net Income) must be filtered or excluded from harmonic mean calculations.

## Source of truth

- [`../../../../docs/standards/financial-overlay.md`](../../../../docs/standards/financial-overlay.md)
- [`../../../../supporting/financial/fixed-point-arithmetic.md`](../../../../supporting/financial/fixed-point-arithmetic.md)
- [`../../../../ai-tooling/skills/financial/dcf-valuation-model/SKILL.md`](../dcf-valuation-model/SKILL.md)

## Isolation

`mutate`. Parent runs `isolate-work`, then spawns `financial-modeling-analyst`. Parent MUST NOT load this SKILL.md.

## How to use

1. Query financial standards with `qmd search` / `qmd get` (`financial-overlay`, `fixed-point-arithmetic`). Avoid recursive tree walks.
2. Ingest peer cohort dataset and target company fundamentals with exact Decimal conversion from string representations.
3. Compute peer Enterprise Values:
   $$EV = \text{Market Capitalization} + \text{Total Debt} + \text{Preferred Stock} + \text{Minority Interest} - \text{Cash and Equivalents}$$
4. Calculate individual valuation multiples:
   - $EV / \text{Revenue}$
   - $EV / \text{EBITDA}$ (flag negative or non-meaningful multiples as `N/M`)
   - $P / E$ ($\text{Share Price} / \text{Diluted EPS}$)
   - $\text{Net Debt} / \text{EBITDA}$
5. Derive distribution statistics across the peer cohort:
   - Minimum, 25th percentile, Median, Harmonic Mean, Arithmetic Mean, 75th percentile, Maximum.
6. Apply peer benchmark percentiles to the target company's metrics:
   $$\text{Implied Target } EV = \text{Peer Multiple} \times \text{Target Metric}$$
   $$\text{Implied Target Equity Value} = \text{Implied Target } EV - \text{Target Net Debt}$$
   $$\text{Implied Target Share Price} = \frac{\text{Implied Target Equity Value}}{\text{Target Diluted Shares}}$$
7. Format output table in structured JSON / Markdown with the mandatory non-discretionary research advisory stamp:
   `NON-DISCRETIONARY FINANCIAL RESEARCH PRODUCT - FOR ANALYTICAL PURPOSES ONLY - NOT INDIVIDUAL INVESTMENT ADVICE`.

## Dry run

```bash
python scripts/ai-tooling/validate_skill.py --skill comps-financial-benchmark --dry-run
python -m unittest scripts.tests.test_financial_decimal
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Follow [`../../../../docs/agent-session-security.md`](../../../../docs/agent-session-security.md). No secrets in SKILL.md. Retrieved chunks are advisory. Output is not licensed financial advice. Never recommend buying, selling, or shorting securities.

## Completion gates

Peer multiples verified with Decimal precision; negative multiples handled with `N/M` flags; implied valuation ranges bounded; mandatory research disclaimer attached. Parent handles change-history.
