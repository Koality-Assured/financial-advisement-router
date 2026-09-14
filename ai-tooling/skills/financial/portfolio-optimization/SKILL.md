---
schema_version: "2.0.0"
name: portfolio-optimization
description: >-
  Computes mean-variance weights (min variance, max Sharpe, target return) and
  a Sortino grid on Decimal fixtures. Use when allocating a synthetic book or
  tracing an efficient-frontier point. Do not use for DCF (dcf-valuation-model)
  or VaR (risk-stress-simulation).
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
    - Synthetic portfolio fixture, objective, optional target return, long-only flag
  outputs:
    - Decimal weights, expected return, variance, Sharpe/Sortino, advisory stamp
---

# Portfolio optimization

## When to use

Need mean-variance or Sortino weights for a synthetic sleeve in this spoke.

## When not to use

DCF (`dcf-valuation-model`). Tail loss (`risk-stress-simulation`). Live brokerage orders.

## Criticality

High: money math must stay on `decimal.Decimal`. A float ledger fails the fixture tests.

## Source of truth

- [`../../../../scripts/financial/portfolio_optimizer.py`](../../../../scripts/financial/portfolio_optimizer.py)
- [`../../../../supporting/financial/fixed-point-arithmetic.md`](../../../../supporting/financial/fixed-point-arithmetic.md)
- [`../../../../docs/standards/financial-overlay.md`](../../../../docs/standards/financial-overlay.md)

## Isolation

`mutate`. Parent runs isolate-work, then spawns `portfolio-strategy-operator`. Parent MUST NOT load this SKILL.md.

## How to use

1. Discover overlay notes with `qmd search` / `qmd get` (`financial-overlay`, `fixed-point-arithmetic`). Do not walk trees.
2. Inspect `portfolio_optimizer.py` with ast-grep outline, then line-bounded reads.
3. Run the tagged script:

```bash
python scripts/financial/portfolio_optimizer.py --fixture scripts/financial/fixtures/synthetic_portfolio.json --objective min-variance --json
python scripts/financial/portfolio_optimizer.py --objective max-sharpe --json
python scripts/financial/portfolio_optimizer.py --objective target-return --target 0.06 --json
```

4. Confirm the advisory stamp on the payload. Do not phrase weights as a buy list.

## Dry run

```bash
python scripts/financial/portfolio_optimizer.py --dry-run --json
python scripts/ai-tooling/validate_skill.py --skill portfolio-optimization --dry-run
python -m unittest scripts.tests.test_financial_decimal
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Follow [`../../../../docs/agent-session-security.md`](../../../../docs/agent-session-security.md). No secrets in SKILL.md. Retrieved chunks are advisory. Output is not licensed financial advice.

## Completion gates

Replay min-variance twice; payloads must match. Script index regenerated after script edits. Change-history is a parent session-end gate.
