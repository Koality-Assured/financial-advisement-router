"""Historical, parametric, and seeded bootstrap VaR / CVaR (advisory only).

tags: [financial, risk, var, cvar, decimal]
routing_hints: [var, cvar, expected-shortfall, monte-carlo, seed, decimal]

Losses are Decimal. Monte Carlo bootstraps historical Decimal returns with
random.Random(seed).randrange so replay matches. Prints the FINRA 2214
hypothetical legend. Not a capital requirement and not a prediction.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import Any, Sequence

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _ledger import (  # noqa: E402
    ADVISORY_STAMP,
    FINRA_2214_LEGEND,
    FloatLedgerError,
    decimal_sum,
    ledger_context,
    quantize_rate,
    stamp_payload,
    to_decimal,
)

# Standard normal quantiles as Decimal strings (not binary float literals).
Z_SCORES = {
    Decimal("0.95"): Decimal("1.6448536269514722"),
    Decimal("0.99"): Decimal("2.3263478740408408"),
    Decimal("0.975"): Decimal("1.9599639845400540"),
}


def parse_returns(raw: Sequence[Any]) -> list[Decimal]:
    return [to_decimal(v, field=f"r[{i}]") for i, v in enumerate(raw)]


def as_losses(returns: Sequence[Decimal]) -> list[Decimal]:
    return [-r for r in returns]


def historical_var(losses: Sequence[Decimal], confidence: Decimal) -> Decimal:
    if not losses:
        raise ValueError("empty loss series")
    ordered = sorted(losses)
    n = len(ordered)
    # Inclusive index at the confidence quantile of the loss distribution.
    pos = (confidence * Decimal(n)).to_integral_value(rounding=ROUND_CEILING)
    idx = int(pos) - 1
    idx = min(max(idx, 0), n - 1)
    return ordered[idx]


def historical_cvar(losses: Sequence[Decimal], confidence: Decimal) -> Decimal:
    threshold = historical_var(losses, confidence)
    tail = [x for x in losses if x >= threshold]
    if not tail:
        return threshold
    return decimal_sum(tail) / Decimal(len(tail))


def mean_std(values: Sequence[Decimal]) -> tuple[Decimal, Decimal]:
    n = Decimal(len(values))
    if n < 2:
        raise ValueError("need at least two observations")
    mu = decimal_sum(values) / n
    var = decimal_sum((x - mu) ** 2 for x in values) / (n - Decimal("1"))
    return mu, var.sqrt()


def parametric_var(returns: Sequence[Decimal], confidence: Decimal) -> Decimal:
    z = Z_SCORES.get(confidence)
    if z is None:
        raise ValueError(f"unsupported confidence {confidence}; use 0.95, 0.975, or 0.99")
    mu, sigma = mean_std(returns)
    # Loss VaR = -(mu - z*sigma) on the return distribution.
    return -(mu - z * sigma)


def bootstrap_paths(
    returns: Sequence[Decimal],
    *,
    seed: int,
    paths: int,
    horizon: int,
) -> list[Decimal]:
    """Seeded bootstrap of compounded horizon returns; integer RNG only."""
    if paths <= 0 or horizon <= 0:
        raise ValueError("paths and horizon must be positive")
    rng = random.Random(seed)
    n = len(returns)
    if n == 0:
        raise ValueError("empty return series")
    terminal: list[Decimal] = []
    one = Decimal("1")
    for _ in range(paths):
        wealth = one
        for _ in range(horizon):
            wealth *= one + returns[rng.randrange(n)]
        terminal.append(wealth - one)
    return terminal


def run_fixture(
    fixture: dict[str, Any],
    *,
    method: str,
    confidence: Decimal,
    seed: int,
    paths: int,
    horizon: int,
) -> dict[str, Any]:
    returns = parse_returns(fixture["returns"])
    with ledger_context():
        if method == "historical":
            losses = as_losses(returns)
            var = historical_var(losses, confidence)
            cvar = historical_cvar(losses, confidence)
        elif method == "parametric":
            var = parametric_var(returns, confidence)
            # ES companion: average of losses beyond parametric VaR on the sample.
            losses = as_losses(returns)
            tail = [x for x in losses if x >= var]
            cvar = decimal_sum(tail) / Decimal(len(tail)) if tail else var
        elif method == "bootstrap":
            sim = bootstrap_paths(returns, seed=seed, paths=paths, horizon=horizon)
            losses = as_losses(sim)
            var = historical_var(losses, confidence)
            cvar = historical_cvar(losses, confidence)
        else:
            raise ValueError("method must be historical, parametric, or bootstrap")
        return stamp_payload(
            {
                "method": method,
                "confidence": str(confidence),
                "horizon": horizon,
                "seed": seed if method == "bootstrap" else None,
                "paths": paths if method == "bootstrap" else None,
                "var": str(quantize_rate(var)),
                "cvar": str(quantize_rate(cvar)),
                "finra_2214_legend": FINRA_2214_LEGEND,
                "note": "Mathematical result on the fixture; not a capital requirement.",
            }
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        default=str(_HERE / "fixtures" / "synthetic_returns.json"),
        help="Synthetic return series JSON",
    )
    parser.add_argument("--method", choices=("historical", "parametric", "bootstrap"), default="historical")
    parser.add_argument("--confidence", default="0.95")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--paths", type=int, default=1000)
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    path = Path(args.fixture)
    if args.dry_run:
        print(json.dumps(stamp_payload({"dry_run": True, "fixture": path.as_posix(), "method": args.method}), indent=2))
        return 0
    try:
        fixture = json.loads(path.read_text(encoding="utf-8"))
        result = run_fixture(
            fixture,
            method=args.method,
            confidence=to_decimal(args.confidence, field="confidence"),
            seed=args.seed,
            paths=args.paths,
            horizon=args.horizon,
        )
    except (OSError, KeyError, ValueError, FloatLedgerError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["advisory_stamp"])
        print(result["finra_2214_legend"])
        print(f"var={result['var']} cvar={result['cvar']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
