---
schema_version: "2.0.0"
name: form-adv-compliance
description: >-
  Audits investment adviser Form ADV Part 1 items and Part 2A/2B narrative brochure
  disclosures against SEC Investment Advisers Act rules. Use when verifying Regulatory
  AUM (RAUM), fee disclosures, conflict of interest disclosures, or disciplinary history.
  Do not use for EDGAR companyfacts XBRL parsing (sec-edgar-extract) or portfolio risk
  (risk-stress-simulation).
tags:
  - financial
  - compliance
  - sec
  - form-adv
  - ria
  - raum
  - reg-bi
  - brochure-rule
routing_hints:
  - form-adv
  - part-2a
  - brochure
  - raum
  - ria-compliance
  - investment-adviser
  - sec-audit
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
    - Form ADV Part 1 data (Item 5 RAUM, client accounts, advisory business model)
    - Form ADV Part 2A narrative brochure text (Item 4 Advisory Business, Item 5 Fees, Item 8 Strategies, Item 10 Conflicts)
    - SEC Form ADV Instructions and Compliance Review Checklist
  outputs:
    - Compliance audit checklist with item-by-item status (Compliant, Deficient, Incomplete)
    - Regulatory AUM reconciliation table (discretionary vs non-discretionary vs total RAUM in Decimal)
    - Conflict of interest cross-reference summary and non-discretionary advisory stamp
---

# Form ADV compliance

## When to use

Auditing Registered Investment Adviser (RIA) Form ADV Part 1 filings and Part 2A narrative brochures, verifying Regulatory Assets Under Management (RAUM) calculation methodology, checking fee schedule transparency, and auditing disclosures of material conflicts of interest.

## When not to use

Public operating company 10-K/10-Q XBRL parsing (`sec-edgar-extract`). Legal representation in SEC enforcement actions. Client investment advisory agreement drafting. DCF equity modeling (`dcf-valuation-model`).

## Criticality

High: Regulatory AUM (RAUM) must follow SEC Item 5.F instructions (gross asset value without deduction for indebtedness) using exact `decimal.Decimal` numbers. Audit outputs represent analytical research and do not substitute for qualified securities legal counsel.

## Source of truth

- SEC Form ADV Instructions and Glossary (17 CFR § 279.1)
- SEC Release No. IA-3060 (Amendments to Form ADV)
- [`../../../../supporting/financial/sec-edgar-api-patterns.md`](../../../../supporting/financial/sec-edgar-api-patterns.md)
- [`../../../../docs/standards/financial-overlay.md`](../../../../docs/standards/financial-overlay.md)
- [`../../../../ai-tooling/skills/financial/sec-edgar-extract/SKILL.md`](../sec-edgar-extract/SKILL.md)

## Isolation

`mutate`. Parent runs `isolate-work`, then spawns `sec-compliance-curator`. Parent MUST NOT load this SKILL.md.

## How to use

1. Discover SEC regulatory guidelines with `qmd search` / `qmd get` (`sec-edgar-api-patterns`, `financial-overlay`). Avoid tree walks.
2. Ingest Form ADV Part 1 metrics and Part 2A narrative brochure text.
3. Verify Regulatory Assets Under Management (RAUM) per SEC Form ADV Instructions:
   - Check Item 5.F: RAUM must be calculated on a gross basis without deducting accrued liabilities, margin debt, or short positions.
   - Reconcile Discretionary RAUM + Non-Discretionary RAUM = Total RAUM in Decimal.
   - Verify that the date of calculation is within 90 days of the filing date.
4. Audit Part 2A Brochure 18 Standard Items:
   - Item 4 (Advisory Business): Description of firm, principal owners, specialized services, and RAUM disclosure matching Part 1.
   - Item 5 (Fees and Compensation): Fee schedule, billing frequency, deductibility, and third-party fees (custody, trading).
   - Item 8 (Methods of Analysis, Investment Strategies, and Risk of Loss): Material risks of specific strategies disclosed.
   - Item 10 (Other Financial Industry Activities and Affiliations): Broker-dealer, commodity pool operator, or municipal advisor affiliations.
   - Item 11 (Code of Ethics, Participation or Interest in Client Transactions): Personal trading policies, soft-dollar practices, and agency cross transactions.
5. Cross-reference Conflict of Interest Disclosures:
   - Compare Part 1 Item 7 (Financial Industry Affiliations) with Part 2A Item 10 to ensure full consistency.
   - Verify Reg BI / Form CRS disclosure alignment where retail investors are served.
6. Generate Compliance Audit Report:
   - Item-by-item status table: `COMPLIANT`, `DEFICIENT`, or `NEEDS_CLARIFICATION`.
   - Actionable remediation suggestions for flagged items.
7. Stamp the report with the non-discretionary regulatory research disclaimer:
   `NON-DISCRETIONARY FINANCIAL RESEARCH PRODUCT - FOR ANALYTICAL PURPOSES ONLY - NOT LEGAL OR REGULATORY COMPLIANCE OPINION`.

## Dry run

```bash
python scripts/ai-tooling/validate_skill.py --skill form-adv-compliance --dry-run
python -m unittest scripts.tests.test_financial_decimal
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Follow [`../../../../docs/agent-session-security.md`](../../../../docs/agent-session-security.md). No real adviser employee PII, client account numbers, or non-public regulatory examination documents. Output is research and does not constitute formal legal counsel.

## Completion gates

RAUM reconciled on gross basis with Decimal precision; Part 1 and Part 2A disclosures cross-checked; compliance status documented; non-discretionary advisory disclaimer attached. Parent handles change-history.
