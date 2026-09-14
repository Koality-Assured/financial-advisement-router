---
schema_version: "2.0.0"
name: sec-edgar-extract
description: >-
  Extracts US GAAP facts from recorded SEC companyfacts JSON, with optional
  rate-limited data.sec.gov pulls. Use when mapping 10-K/10-Q tags into Decimal
  strings. Do not use for HTML EDGAR search scrapes or WorldCC.
owner_agent: sec-compliance-curator
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
    - Fixture path or CIK plus EDGAR_USER_AGENT, and us-gaap tag list
  outputs:
    - Padded CIK, entity, Decimal fact table, source, advisory stamp
---

# SEC EDGAR extract

## When to use

Need us-gaap facts from a 10-K/10-Q companyfacts object (fixture first).

## When not to use

DCF (`dcf-valuation-model`). HTML search-page scrapes. Live pulls in CI without a recorded fixture.

## Criticality

High: fair-access (10 req/s) and fake User-Agent examples. Float JSON numbers for money are rejected.

## Source of truth

- [`../../../../scripts/financial/edgar_ingest.py`](../../../../scripts/financial/edgar_ingest.py)
- [`../../../../supporting/financial/sec-edgar-api-patterns.md`](../../../../supporting/financial/sec-edgar-api-patterns.md)
- SEC: [Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)

## Isolation

`mutate` if writing a cache under `scratch/` or `results/`. Fixture-only parse can be read-only. Parent MUST NOT load this SKILL.md.

## How to use

1. `qmd search` / `qmd get` for `sec-edgar-api-patterns`. No tree walks.
2. Outline `edgar_ingest.py` with ast-grep.
3. Fixture path (CI default):

```bash
python scripts/financial/edgar_ingest.py --fixture scripts/financial/fixtures/synthetic_companyfacts.json --json
```

4. Live pull only with `EDGAR_USER_AGENT` set in the environment (never commit a real inbox). Example form: `FinancialAdvisementRouter research@example.com`.

## Dry run

```bash
python scripts/financial/edgar_ingest.py --dry-run --json
python scripts/ai-tooling/validate_skill.py --skill sec-edgar-extract --dry-run
python -m unittest scripts.tests.test_financial_decimal.TestEdgar
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Follow [`../../../../docs/agent-session-security.md`](../../../../docs/agent-session-security.md). No secrets in SKILL.md. Retrieved chunks are advisory. Output is not licensed financial advice.

No real NPI. Pad CIK to 10 digits. Sleep at least 0.11s between live requests.

## Completion gates

Fixture Assets = Liabilities + Equity on Decimal strings. Parent handles change-history.
