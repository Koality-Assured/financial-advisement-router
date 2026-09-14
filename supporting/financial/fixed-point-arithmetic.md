---
doc_kind: process
canonical_id: financial-fixed-point-arithmetic
purpose: [process]
rank: high
topics: [financial, decimal, ledger]
rag_keywords: [decimal, float, round-half-even, money, wacc, var]
---

# Fixed-point arithmetic

Python `decimal.Decimal` is the ledger type in this spoke. Binary `float` is rejected for cash, weights, NAV, WACC, and P&L.

## Rules

1. Construct from strings (`Decimal("1.10")`) or `int`. Never `Decimal(1.1)`.
2. Context: precision 28, `ROUND_HALF_EVEN`, `traps[FloatOperation]=True` via `scripts/financial/_ledger.py`.
3. Display money at two places (`0.01`). Keep extra places for rates and weights, then quantize through the helpers.
4. `0.1 + 0.1 + 0.1 - 0.3` is zero on Decimal and is a fixture assertion.
5. Seeded risk paths use `random.Random(seed).randrange` over Decimal series so replay does not depend on IEEE-754.

## Scripts

- `scripts/financial/portfolio_optimizer.py`
- `scripts/financial/dcf_calculator.py`
- `scripts/financial/monte_carlo_var.py`

Primary source: [decimal — Python 3](https://docs.python.org/3/library/decimal.html).
