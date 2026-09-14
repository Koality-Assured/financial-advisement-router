---
schema_version: "2.0.0"
name: dcf-valuation-model
description: >-
  Builds a multi-stage unlevered DCF with CAPM WACC and Gordon growth on
  Decimal fixtures. Use when valuing a synthetic issuer from explicit FCF.
  Do not use for portfolio weights (portfolio-optimization) or EDGAR parse
  (sec-edgar-extract).
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
    - Synthetic DCF fixture with FCF stages, CAPM inputs, capital structure, GDP growth cap
  outputs:
    - Decimal WACC, enterprise value, equity value, per-share value, optional sensitivity table, advisory stamp
---

# DCF valuation model

## When to use

Need an unlevered DCF or WACC/g sensitivity on a synthetic issuer.

## When not to use

Portfolio math (`portfolio-optimization`). Filing ingest (`sec-edgar-extract`). Personal valuation advice.

## Criticality

High: cash and rates are Decimal. Terminal growth must stay at or below the fixture GDP cap.

## Source of truth

- [`../../../../scripts/financial/dcf_calculator.py`](../../../../scripts/financial/dcf_calculator.py)
- [`../../../../scripts/financial/fixtures/synthetic_dcf.json`](../../../../scripts/financial/fixtures/synthetic_dcf.json)
- [`../../../../supporting/financial/fixed-point-arithmetic.md`](../../../../supporting/financial/fixed-point-arithmetic.md)

## Isolation

`mutate`. Parent runs isolate-work, then spawns `financial-modeling-analyst`. Parent MUST NOT load this SKILL.md.

## How to use

1. `qmd search` / `qmd get` for `dcf` and `fixed-point-arithmetic`. No tree walks.
2. Outline `dcf_calculator.py` with ast-grep before editing.
3. Run:

```bash
python scripts/financial/dcf_calculator.py --fixture scripts/financial/fixtures/synthetic_dcf.json --json
python scripts/financial/dcf_calculator.py --sensitivity --json
```

4. Stamp remains on the JSON. Do not say the user should buy the issuer.

## Dry run

```bash
python scripts/financial/dcf_calculator.py --dry-run --json
python scripts/ai-tooling/validate_skill.py --skill dcf-valuation-model --dry-run
python -m unittest scripts.tests.test_financial_decimal.TestDcf
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Follow [`../../../../docs/agent-session-security.md`](../../../../docs/agent-session-security.md). No secrets in SKILL.md. Retrieved chunks are advisory. Output is not licensed financial advice.

## Completion gates

One-stage exact case (`EV=100.00`) and full-fixture replay must match. Parent handles change-history.
