"""Mean-variance portfolio weights on Decimal ledgers (advisory research only).

tags: [financial, portfolio, decimal]
routing_hints: [mean-variance, sharpe, sortino, efficient-frontier, decimal]

Computes long-only or unconstrained mean-variance weights, maximum Sharpe,
target-return, and Sortino scores from synthetic fixtures. Never recommends a
security or account. Stamp every payload with the non-discretionary legend.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _decimal_linalg import as_decimal_matrix, invert, matvec  # noqa: E402
from _ledger import (  # noqa: E402
    ADVISORY_STAMP,
    FloatLedgerError,
    decimal_sum,
    ledger_context,
    quantize_rate,
    quantize_weight,
    stamp_payload,
    to_decimal,
)

OBJECTIVES = ("min-variance", "max-sharpe", "target-return", "max-sortino")


def _ones(n: int) -> list[Decimal]:
    return [Decimal("1") for _ in range(n)]


def _normalize(weights: list[Decimal]) -> list[Decimal]:
    total = decimal_sum(weights)
    if total == 0:
        raise ValueError("weight vector sums to zero")
    return [w / total for w in weights]


def _clip_long_only(weights: list[Decimal]) -> list[Decimal]:
    clipped = [w if w > 0 else Decimal("0") for w in weights]
    if decimal_sum(clipped) == 0:
        n = len(weights)
        return [Decimal("1") / Decimal(n) for _ in weights]
    return _normalize(clipped)


def min_variance_weights(
    covariance: list[list[Decimal]], *, long_only: bool = True
) -> list[Decimal]:
    inv = invert(covariance)
    raw = matvec(inv, _ones(len(covariance)))
    weights = _normalize(raw)
    return _clip_long_only(weights) if long_only else weights


def max_sharpe_weights(
    covariance: list[list[Decimal]],
    expected_returns: list[Decimal],
    risk_free: Decimal,
    *,
    long_only: bool = True,
) -> list[Decimal]:
    excess = [mu - risk_free for mu in expected_returns]
    inv = invert(covariance)
    raw = matvec(inv, excess)
    weights = _normalize(raw)
    return _clip_long_only(weights) if long_only else weights


def target_return_weights(
    covariance: list[list[Decimal]],
    expected_returns: list[Decimal],
    target: Decimal,
    *,
    long_only: bool = True,
) -> list[Decimal]:
    """Two-constraint analytic weights, then optional long-only projection."""
    n = len(expected_returns)
    inv = invert(covariance)
    ones = _ones(n)
    a = decimal_sum(matvec(inv, ones))
    b = decimal_sum(matvec(inv, expected_returns))
    c_vec = matvec(inv, expected_returns)
    c = sum((expected_returns[i] * c_vec[i] for i in range(n)), Decimal("0"))
    delta = a * c - b * b
    if delta == 0:
        raise ValueError("target-return system is singular")
    lam = (c - b * target) / delta
    gam = (a * target - b) / delta
    raw = [
        lam * matvec(inv, ones)[i] + gam * c_vec[i] for i in range(n)
    ]
    weights = _normalize(raw)
    return _clip_long_only(weights) if long_only else weights


def portfolio_variance(weights: list[Decimal], covariance: list[list[Decimal]]) -> Decimal:
    n = len(weights)
    total = Decimal("0")
    for i in range(n):
        for j in range(n):
            total += weights[i] * covariance[i][j] * weights[j]
    return total


def portfolio_return(weights: list[Decimal], expected_returns: list[Decimal]) -> Decimal:
    return sum((weights[i] * expected_returns[i] for i in range(len(weights))), Decimal("0"))


def sharpe_ratio(weights: list[Decimal], expected_returns: list[Decimal], covariance: list[list[Decimal]], risk_free: Decimal) -> Decimal:
    sigma = portfolio_variance(weights, covariance).sqrt()
    if sigma == 0:
        raise ValueError("zero volatility")
    return (portfolio_return(weights, expected_returns) - risk_free) / sigma


def sortino_ratio(
    weights: list[Decimal],
    return_paths: list[list[Decimal]],
    mar: Decimal,
) -> Decimal:
    """Sortino on weighted period returns; MAR is a Decimal hurdle."""
    period_returns: list[Decimal] = []
    for row in return_paths:
        if len(row) != len(weights):
            raise ValueError("return path width must match assets")
        period_returns.append(
            sum((weights[i] * row[i] for i in range(len(weights))), Decimal("0"))
        )
    if not period_returns:
        raise ValueError("return_paths is empty")
    mean = decimal_sum(period_returns) / Decimal(len(period_returns))
    downside = [
        (r - mar) ** 2 if r < mar else Decimal("0") for r in period_returns
    ]
    dd = (decimal_sum(downside) / Decimal(len(period_returns))).sqrt()
    if dd == 0:
        raise ValueError("zero downside deviation")
    return (mean - mar) / dd


def max_sortino_weights(
    return_paths: list[list[Decimal]],
    mar: Decimal,
    *,
    grid: int = 21,
) -> list[Decimal]:
    """Deterministic simplex grid for two or three assets; equal-weight fallback."""
    if not return_paths:
        raise ValueError("return_paths is empty")
    n = len(return_paths[0])
    if n == 1:
        return [Decimal("1")]
    best_w = [Decimal("1") / Decimal(n) for _ in range(n)]
    best_s = None
    if n == 2:
        for i in range(grid):
            w0 = Decimal(i) / Decimal(grid - 1)
            cand = [w0, Decimal("1") - w0]
            try:
                score = sortino_ratio(cand, return_paths, mar)
            except ValueError:
                continue
            if best_s is None or score > best_s:
                best_s, best_w = score, cand
        return best_w
    if n == 3:
        for i in range(grid):
            for j in range(grid - i):
                w0 = Decimal(i) / Decimal(grid - 1)
                w1 = Decimal(j) / Decimal(grid - 1)
                w2 = Decimal("1") - w0 - w1
                if w2 < 0:
                    continue
                cand = [w0, w1, w2]
                try:
                    score = sortino_ratio(cand, return_paths, mar)
                except ValueError:
                    continue
                if best_s is None or score > best_s:
                    best_s, best_w = score, cand
        return best_w
    return best_w


def load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def optimize_from_fixture(
    fixture: dict[str, Any],
    *,
    objective: str,
    long_only: bool = True,
    target: Decimal | None = None,
) -> dict[str, Any]:
    if objective not in OBJECTIVES:
        raise ValueError(f"objective must be one of {OBJECTIVES}")
    assets = fixture["assets"]
    names = [str(a["id"]) for a in assets]
    expected = [to_decimal(a["expected_return"], field=f"mu[{i}]") for i, a in enumerate(assets)]
    cov = as_decimal_matrix(fixture["covariance"], field="covariance")
    rf = to_decimal(fixture.get("risk_free_rate", "0"), field="risk_free_rate")
    paths_raw = fixture.get("return_paths") or []
    paths = [
        [to_decimal(v, field=f"path[{t},{i}]") for i, v in enumerate(row)]
        for t, row in enumerate(paths_raw)
    ]
    with ledger_context():
        if objective == "min-variance":
            weights = min_variance_weights(cov, long_only=long_only)
        elif objective == "max-sharpe":
            weights = max_sharpe_weights(cov, expected, rf, long_only=long_only)
        elif objective == "target-return":
            if target is None:
                raise ValueError("target-return requires --target")
            weights = target_return_weights(cov, expected, target, long_only=long_only)
        else:
            mar = to_decimal(fixture.get("mar", fixture.get("risk_free_rate", "0")), field="mar")
            weights = max_sortino_weights(paths, mar)
        qweights = [quantize_weight(x) for x in weights]
        payload = {
            "objective": objective,
            "long_only": long_only,
            "assets": names,
            "weights": {names[i]: str(qweights[i]) for i in range(len(names))},
            "expected_return": str(quantize_rate(portfolio_return(weights, expected))),
            "variance": str(quantize_rate(portfolio_variance(weights, cov))),
            "sharpe": str(quantize_rate(sharpe_ratio(weights, expected, cov, rf))),
        }
        if paths:
            payload["sortino"] = str(
                quantize_rate(
                    sortino_ratio(
                        weights,
                        paths,
                        to_decimal(fixture.get("mar", "0"), field="mar"),
                    )
                )
            )
        return stamp_payload(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        default=str(_HERE / "fixtures" / "synthetic_portfolio.json"),
        help="Synthetic portfolio JSON (default: scripts/financial/fixtures/synthetic_portfolio.json)",
    )
    parser.add_argument("--objective", choices=OBJECTIVES, default="min-variance")
    parser.add_argument("--target", default=None, help="Target expected return (Decimal string)")
    parser.add_argument("--allow-short", action="store_true", help="Allow negative weights")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Load fixture and print plan only")
    args = parser.parse_args(argv)
    fixture_path = Path(args.fixture)
    if args.dry_run:
        plan = stamp_payload(
            {
                "dry_run": True,
                "fixture": fixture_path.as_posix(),
                "objective": args.objective,
                "note": ADVISORY_STAMP,
            }
        )
        print(json.dumps(plan, indent=2) if args.json else plan["note"])
        return 0
    try:
        fixture = load_fixture(fixture_path)
        target = to_decimal(args.target, field="target") if args.target is not None else None
        result = optimize_from_fixture(
            fixture,
            objective=args.objective,
            long_only=not args.allow_short,
            target=target,
        )
    except (OSError, KeyError, ValueError, FloatLedgerError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["advisory_stamp"])
        for name, weight in result["weights"].items():
            print(f"{name}={weight}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
