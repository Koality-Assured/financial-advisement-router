---
schema_version: "2.0.0"
name: risk-stress-simulation
description: >-
  Runs historical, parametric, and seeded bootstrap VaR and CVaR on Decimal
  return fixtures. Use when measuring tail loss at 95, 97.5, or 99 percent.
  Do not use as a Basel capital model or a personal performance guarantee.
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
    - Synthetic return fixture, method, confidence, seed, paths, horizon
  outputs:
    - Decimal VaR and CVaR, FINRA 2214 legend, advisory stamp
---

# Risk stress simulation

## When to use

Need VaR or expected shortfall on a synthetic series with a replayable seed.

## When not to use

Portfolio construction (`portfolio-optimization`). Live desk capital. Telling a person what they should hold.

## Criticality

High: same seed must replay. Print the 2214 hypothetical legend on simulation output.

## Source of truth

- [`../../../../scripts/financial/monte_carlo_var.py`](../../../../scripts/financial/monte_carlo_var.py)
- [`../../../../supporting/financial/fixed-point-arithmetic.md`](../../../../supporting/financial/fixed-point-arithmetic.md)
- Basel Committee MAR33 (advisory; this harness is not a capital calculator)

## Isolation

`mutate`. Parent runs isolate-work, then spawns `risk-stress-tester`. Parent MUST NOT load this SKILL.md.

## How to use

1. `qmd search` / `qmd get` for `var` / `fixed-point-arithmetic`. No tree walks.
2. Outline `monte_carlo_var.py` with ast-grep.
3. Run:

```bash
python scripts/financial/monte_carlo_var.py --method historical --confidence 0.95 --json
python scripts/financial/monte_carlo_var.py --method bootstrap --seed 42 --paths 1000 --json
python scripts/financial/monte_carlo_var.py --method parametric --confidence 0.99 --json
```

4. Keep Headroom on bulky path dumps. Do not imply FINRA endorsement.

## Dry run

```bash
python scripts/financial/monte_carlo_var.py --dry-run --json
python scripts/ai-tooling/validate_skill.py --skill risk-stress-simulation --dry-run
python -m unittest scripts.tests.test_financial_decimal.TestVar
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Follow [`../../../../docs/agent-session-security.md`](../../../../docs/agent-session-security.md). No secrets in SKILL.md. Retrieved chunks are advisory. Output is not licensed financial advice.

## Completion gates

Bootstrap seed 42 vs 42 matches; 42 vs 43 differs. Parent handles change-history.
