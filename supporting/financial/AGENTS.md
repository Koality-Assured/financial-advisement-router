# Supporting financial

Tool recipes for Decimal ledgers and SEC EDGAR fair-access. Not investment advice.

Link root [`../../AGENTS.md`](../../AGENTS.md). Default specialists: `financial-modeling-analyst` (ledger/DCF), `sec-compliance-curator` (EDGAR), `portfolio-strategy-operator` (weights), `risk-stress-tester` (VaR).

## Rules

- Money from strings or `Decimal`, never `float`.
- Example User-Agent is fake. Live pulls use `EDGAR_USER_AGENT`.
- One-way: this folder must not link to `projects/` or `scratch/`.
