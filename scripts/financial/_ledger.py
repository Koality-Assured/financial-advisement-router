"""Shared Decimal ledger helpers for financial scripts.

Money, weights, and rates are ``decimal.Decimal`` only. Binary ``float`` is
rejected. Outputs are a non-discretionary research product, not advice.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, FloatOperation, getcontext, localcontext
from typing import Any, Iterable, Mapping

ADVISORY_STAMP = (
    "NON-DISCRETIONARY FINANCIAL RESEARCH PRODUCT - FOR ANALYTICAL PURPOSES "
    "ONLY - NOT INDIVIDUAL INVESTMENT ADVICE"
)

FINRA_2214_LEGEND = (
    "Projections are hypothetical, do not reflect actual investment results, "
    "and are not guarantees of future results."
)

MONEY_QUANT = Decimal("0.01")
RATE_QUANT = Decimal("0.00000001")
WEIGHT_QUANT = Decimal("0.00000001")


class FloatLedgerError(TypeError):
    """Raised when a binary float is supplied where Decimal money is required."""


def ledger_context(*, prec: int = 28):
    """Return a localcontext with banker rounding and FloatOperation trapped."""
    ctx = getcontext().copy()
    ctx.prec = prec
    ctx.rounding = ROUND_HALF_EVEN
    ctx.traps[FloatOperation] = True
    return localcontext(ctx)


def to_decimal(value: Any, *, field: str = "value") -> Decimal:
    """Construct Decimal from str, int, or Decimal. Reject float."""
    if isinstance(value, float):
        raise FloatLedgerError(
            f"binary float rejected for {field}; pass a str or decimal.Decimal"
        )
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise FloatLedgerError(f"bool rejected for {field}")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        return Decimal(value)
    raise FloatLedgerError(
        f"unsupported type {type(value).__name__} for {field}; pass str or Decimal"
    )


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_EVEN)


def quantize_rate(value: Decimal) -> Decimal:
    return value.quantize(RATE_QUANT, rounding=ROUND_HALF_EVEN)


def quantize_weight(value: Decimal) -> Decimal:
    return value.quantize(WEIGHT_QUANT, rounding=ROUND_HALF_EVEN)


def decimal_sum(values: Iterable[Any]) -> Decimal:
    total = Decimal("0")
    for item in values:
        total += to_decimal(item)
    return total


def stamp_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Copy a result mapping and attach the advisory stamp (never advice)."""
    out = dict(payload)
    out["advisory_stamp"] = ADVISORY_STAMP
    out["licensed_advice"] = False
    return out
