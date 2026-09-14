---
doc_kind: requirement
canonical_id: financial-overlay
purpose: [requirement]
rank: medium
topics: [financial, overlay]
rag_keywords: [financial, domain-overlay, spoke, decimal, edgar, var, dcf]
---

# financial domain overlay

This spoke is a `financial` harness scaffolded from `ai-harness-core`. Domain packs live here. Keep generic machinery in the core. Do not copy this overlay, instance `projects/`, `research/`, or `ai-tooling/memory/` back to the generic core.

Every model output is a non-discretionary research product: `NON-DISCRETIONARY FINANCIAL RESEARCH PRODUCT - FOR ANALYTICAL PURPOSES ONLY - NOT INDIVIDUAL INVESTMENT ADVICE`. It is not licensed financial advice.

## Domain agents

| Agent | Tier | Skill |
| --- | --- | --- |
| `portfolio-strategy-operator` | high | `portfolio-optimization` |
| `financial-modeling-analyst` | high | `dcf-valuation-model` |
| `sec-compliance-curator` | standard | `sec-edgar-extract` |
| `risk-stress-tester` | high | `risk-stress-simulation` |

Pairing: true specialists are allowed in this distinct domain repository.

## Scripts and fixtures

- `scripts/financial/portfolio_optimizer.py`
- `scripts/financial/dcf_calculator.py`
- `scripts/financial/edgar_ingest.py`
- `scripts/financial/monte_carlo_var.py`
- Synthetic statements under `scripts/financial/fixtures/`

Money is `decimal.Decimal`. Tests reject binary float ledgers.

Pull core updates: `python scripts/sync/pull_harness_core.py --dry-run --json`.

Propose generic core changes: `python scripts/sync/propose_core_update.py --dry-run --json`.
