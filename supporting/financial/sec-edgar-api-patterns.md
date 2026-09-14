---
doc_kind: process
canonical_id: financial-sec-edgar-api-patterns
purpose: [process]
rank: high
topics: [financial, edgar, sec]
rag_keywords: [edgar, companyfacts, cik, user-agent, rate-limit, xbrl]
---

# SEC EDGAR API patterns

Use `data.sec.gov` JSON. Do not scrape HTML search pages when a companyfacts object exists.

## Fair access

- Max 10 requests per second. This client sleeps 0.11s between live calls.
- Headers: `User-Agent` (app name plus contact), `Accept-Encoding: gzip, deflate`, `Host: data.sec.gov`.
- Put the User-Agent in `EDGAR_USER_AGENT`. Example in git is fake: `FinancialAdvisementRouter research@example.com`.
- Pad CIK to 10 digits. Company facts: `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json`.

## Harness default

CI and unit tests read `scripts/financial/fixtures/synthetic_companyfacts.json`. Live pulls are opt-in (`--live`) and off unless the env var is set.

Primary sources: [Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data), [EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).
