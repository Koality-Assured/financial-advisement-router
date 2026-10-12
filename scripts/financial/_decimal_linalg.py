"""Decimal matrix helpers for mean-variance math. Not indexed (underscore)."""

from __future__ import annotations

from decimal import Decimal

from _ledger import to_decimal


def zeros(n: int, m: int | None = None) -> list[list[Decimal]]:
    cols = n if m is None else m
    return [[Decimal("0") for _ in range(cols)] for _ in range(n)]


def identity(n: int) -> list[list[Decimal]]:
    out = zeros(n)
    for i in range(n):
        out[i][i] = Decimal("1")
    return out


def matvec(matrix: list[list[Decimal]], vec: list[Decimal]) -> list[Decimal]:
    return [sum((row[j] * vec[j] for j in range(len(vec))), Decimal("0")) for row in matrix]


def invert(matrix: list[list[Decimal]]) -> list[list[Decimal]]:
    """Gauss-Jordan invert a square Decimal matrix. Raises ValueError if singular."""
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        raise ValueError("covariance must be a square matrix")
    a = [row[:] + identity(n)[i] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(a[r][col]))
        a[col], a[pivot_row] = a[pivot_row], a[col]
        pivot = a[col][col]
        if pivot == 0:
            raise ValueError("singular covariance matrix")
        scale = Decimal("1") / pivot
        for j in range(2 * n):
            a[col][j] *= scale
        for i in range(n):
            if i == col:
                continue
            factor = a[i][col]
            if factor == 0:
                continue
            for j in range(2 * n):
                a[i][j] -= factor * a[col][j]
    return [row[n:] for row in a]


def as_decimal_matrix(raw: list[list[object]], *, field: str) -> list[list[Decimal]]:
    n = len(raw)
    out: list[list[Decimal]] = []
    for i, row in enumerate(raw):
        if len(row) != n:
            raise ValueError(f"{field} must be square; row {i} length {len(row)} != {n}")
        out.append(
            [to_decimal(cell, field=f"{field}[{i},{j}]") for j, cell in enumerate(row)]
        )
    return out
