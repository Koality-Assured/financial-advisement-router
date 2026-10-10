"""Comparable company analysis (comps) multiples on Decimal ledgers (advisory only).

tags: [financial, comps, multiples, valuation, decimal]
routing_hints: [comps, ev-ebitda, pe-ratio, harmonic-mean, valuation-percentiles, decimal]

Computes peer EV/EBITDA, P/E, EV/Revenue, and P/B multiples, harmonic and arithmetic
means, valuation percentiles, and implied target company equity and share valuations.
Uses strict Decimal math with banker's rounding (ROUND_HALF_EVEN) and FloatOperation
trapped. Outputs are non-discretionary analytical research only, not investment advice.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any, Mapping, Sequence

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _ledger import (  # noqa: E402
    ADVISORY_STAMP,
    FloatLedgerError,
    decimal_sum,
    ledger_context,
    quantize_money,
    quantize_multiple,
    stamp_payload,
    to_decimal,
)

METRIC_CHOICES = ("all", "ev_ebitda", "pe", "ev_revenue", "price_to_book")


def compute_peer_multiples(peer: Mapping[str, Any]) -> dict[str, Decimal | None]:
    """Calculate valuation multiples for a single peer company."""
    multiples: dict[str, Decimal | None] = {
        "ev_ebitda": None,
        "pe": None,
        "ev_revenue": None,
        "price_to_book": None,
    }

    # 1. EV / EBITDA
    if "ev_ebitda" in peer and peer["ev_ebitda"] is not None:
        multiples["ev_ebitda"] = to_decimal(peer["ev_ebitda"], field=f"{peer.get('ticker', 'peer')}.ev_ebitda")
    elif "enterprise_value" in peer and "ebitda" in peer:
        ev = to_decimal(peer["enterprise_value"], field=f"{peer.get('ticker', 'peer')}.enterprise_value")
        ebitda = to_decimal(peer["ebitda"], field=f"{peer.get('ticker', 'peer')}.ebitda")
        if ebitda > 0:
            multiples["ev_ebitda"] = ev / ebitda

    # 2. P / E
    if "pe" in peer and peer["pe"] is not None:
        multiples["pe"] = to_decimal(peer["pe"], field=f"{peer.get('ticker', 'peer')}.pe")
    elif "market_cap" in peer and "net_income" in peer:
        mcap = to_decimal(peer["market_cap"], field=f"{peer.get('ticker', 'peer')}.market_cap")
        ni = to_decimal(peer["net_income"], field=f"{peer.get('ticker', 'peer')}.net_income")
        if ni > 0:
            multiples["pe"] = mcap / ni
    elif "price" in peer and "eps" in peer:
        p = to_decimal(peer["price"], field=f"{peer.get('ticker', 'peer')}.price")
        eps = to_decimal(peer["eps"], field=f"{peer.get('ticker', 'peer')}.eps")
        if eps > 0:
            multiples["pe"] = p / eps

    # 3. EV / Revenue
    if "ev_revenue" in peer and peer["ev_revenue"] is not None:
        multiples["ev_revenue"] = to_decimal(peer["ev_revenue"], field=f"{peer.get('ticker', 'peer')}.ev_revenue")
    elif "enterprise_value" in peer and "revenue" in peer:
        ev = to_decimal(peer["enterprise_value"], field=f"{peer.get('ticker', 'peer')}.enterprise_value")
        rev = to_decimal(peer["revenue"], field=f"{peer.get('ticker', 'peer')}.revenue")
        if rev > 0:
            multiples["ev_revenue"] = ev / rev

    # 4. P / B (Price to Book)
    if "price_to_book" in peer and peer["price_to_book"] is not None:
        multiples["price_to_book"] = to_decimal(peer["price_to_book"], field=f"{peer.get('ticker', 'peer')}.price_to_book")
    elif "market_cap" in peer and "book_value" in peer:
        mcap = to_decimal(peer["market_cap"], field=f"{peer.get('ticker', 'peer')}.market_cap")
        bv = to_decimal(peer["book_value"], field=f"{peer.get('ticker', 'peer')}.book_value")
        if bv > 0:
            multiples["price_to_book"] = mcap / bv

    return multiples


def arithmetic_mean(values: Sequence[Decimal]) -> Decimal:
    """Compute arithmetic mean across a sequence of Decimals."""
    if not values:
        raise ValueError("cannot calculate arithmetic mean of empty series")
    return decimal_sum(values) / Decimal(len(values))


def harmonic_mean(values: Sequence[Decimal]) -> Decimal:
    """Compute harmonic mean across positive Decimals.

    In valuation literature (Baker & Ruback 2002), harmonic mean mitigates upward
    bias inherent in arithmetic averages of price ratios where the denominator varies.
    Non-positive multiples are excluded.
    """
    positives = [v for v in values if v > 0]
    if not positives:
        raise ValueError("cannot calculate harmonic mean without positive multiples")
    inv_sum = sum((Decimal("1") / v for v in positives), Decimal("0"))
    return Decimal(len(positives)) / inv_sum


def valuation_percentiles(
    values: Sequence[Decimal],
    percentiles: Sequence[Decimal | str] = ("0.10", "0.25", "0.50", "0.75", "0.90"),
) -> dict[str, Decimal]:
    """Compute exact valuation percentiles via linear interpolation between ranks."""
    if not values:
        raise ValueError("cannot calculate percentiles of empty series")
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    results: dict[str, Decimal] = {
        "min": sorted_vals[0],
        "max": sorted_vals[-1],
    }

    if n == 1:
        for p in percentiles:
            p_dec = to_decimal(p)
            label = f"p{int(p_dec * 100)}"
            results[label] = sorted_vals[0]
        results["median"] = sorted_vals[0]
        return results

    for p in percentiles:
        p_dec = to_decimal(p)
        if not (Decimal("0") <= p_dec <= Decimal("1")):
            raise ValueError(f"percentile must be between 0 and 1, got {p_dec}")
        rank = p_dec * Decimal(n - 1)
        low_idx = int(rank)
        high_idx = min(low_idx + 1, n - 1)
        fraction = rank - Decimal(low_idx)
        val = sorted_vals[low_idx] + fraction * (sorted_vals[high_idx] - sorted_vals[low_idx])
        label = f"p{int(p_dec * 100)}"
        results[label] = val
        if p_dec == Decimal("0.50"):
            results["median"] = val

    return results


def summarize_multiples(values: Sequence[Decimal]) -> dict[str, Any]:
    """Generate comprehensive summary statistics for a peer multiple distribution."""
    if not values:
        return {}
    positives = [v for v in values if v > 0]
    amean = arithmetic_mean(values)
    hmean = harmonic_mean(positives) if positives else None
    pcts = valuation_percentiles(values)

    p25 = pcts.get("p25", pcts["min"])
    p75 = pcts.get("p75", pcts["max"])
    iqr = p75 - p25

    # Population standard deviation
    n = Decimal(len(values))
    variance = decimal_sum((v - amean) ** 2 for v in values) / n if n > 0 else Decimal("0")
    std_dev = variance.sqrt()

    return {
        "count": len(values),
        "valid_count": len(positives),
        "arithmetic_mean": str(quantize_multiple(amean)),
        "harmonic_mean": str(quantize_multiple(hmean)) if hmean is not None else None,
        "median": str(quantize_multiple(pcts["median"])),
        "min": str(quantize_multiple(pcts["min"])),
        "max": str(quantize_multiple(pcts["max"])),
        "p10": str(quantize_multiple(pcts.get("p10", pcts["min"]))),
        "p25": str(quantize_multiple(p25)),
        "p75": str(quantize_multiple(p75)),
        "p90": str(quantize_multiple(pcts.get("p90", pcts["max"]))),
        "iqr": str(quantize_multiple(iqr)),
        "std_dev": str(quantize_multiple(std_dev)),
    }


def compute_target_implied_valuations(
    stats: dict[str, Any],
    metric: str,
    target: dict[str, Any],
) -> dict[str, dict[str, str]]:
    """Compute target implied enterprise value, equity value, and per-share price."""
    stat_keys = ("harmonic_mean", "arithmetic_mean", "median", "p25", "p75", "min", "max")
    implied: dict[str, dict[str, str]] = {}

    shares = to_decimal(target.get("shares_outstanding", "1"), field="target.shares_outstanding")
    if shares <= 0:
        raise ValueError("target shares_outstanding must be strictly positive")
    net_debt = to_decimal(target.get("net_debt", "0"), field="target.net_debt")

    for key in stat_keys:
        raw_stat = stats.get(key)
        if raw_stat is None:
            continue
        mult = to_decimal(raw_stat, field=f"stat.{key}")

        if metric == "ev_ebitda":
            if "ebitda" not in target:
                continue
            ebitda = to_decimal(target["ebitda"], field="target.ebitda")
            ev = mult * ebitda
            equity = ev - net_debt
            per_share = equity / shares
            implied[key] = {
                "multiple": str(quantize_multiple(mult)),
                "enterprise_value": str(quantize_money(ev)),
                "equity_value": str(quantize_money(equity)),
                "value_per_share": str(quantize_money(per_share)),
            }
        elif metric == "pe":
            if "net_income" in target:
                ni = to_decimal(target["net_income"], field="target.net_income")
                equity = mult * ni
                ev = equity + net_debt
                per_share = equity / shares
            elif "eps" in target:
                eps = to_decimal(target["eps"], field="target.eps")
                per_share = mult * eps
                equity = per_share * shares
                ev = equity + net_debt
            else:
                continue
            implied[key] = {
                "multiple": str(quantize_multiple(mult)),
                "enterprise_value": str(quantize_money(ev)),
                "equity_value": str(quantize_money(equity)),
                "value_per_share": str(quantize_money(per_share)),
            }
        elif metric == "ev_revenue":
            if "revenue" not in target:
                continue
            rev = to_decimal(target["revenue"], field="target.revenue")
            ev = mult * rev
            equity = ev - net_debt
            per_share = equity / shares
            implied[key] = {
                "multiple": str(quantize_multiple(mult)),
                "enterprise_value": str(quantize_money(ev)),
                "equity_value": str(quantize_money(equity)),
                "value_per_share": str(quantize_money(per_share)),
            }

    return implied


def run_comps(
    fixture: dict[str, Any],
    *,
    metric_filter: str = "all",
    target_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute complete peer comps analysis on Decimal ledgers."""
    if metric_filter not in METRIC_CHOICES:
        raise ValueError(f"metric must be one of {METRIC_CHOICES}, got {metric_filter}")

    peers_raw = fixture.get("peers", [])
    if not peers_raw:
        raise ValueError("comps fixture contains no peer companies")

    target = dict(fixture.get("target", {}))
    if target_overrides:
        target.update({k: v for k, v in target_overrides.items() if v is not None})

    with ledger_context():
        peer_results: list[dict[str, Any]] = []
        multiples_by_metric: dict[str, list[Decimal]] = {
            "ev_ebitda": [],
            "pe": [],
            "ev_revenue": [],
            "price_to_book": [],
        }

        for peer in peers_raw:
            p_mults = compute_peer_multiples(peer)
            peer_summary: dict[str, Any] = {
                "name": peer.get("name", "Unknown"),
                "ticker": peer.get("ticker", "N/A"),
                "multiples": {},
            }
            for k, val in p_mults.items():
                if val is not None:
                    multiples_by_metric[k].append(val)
                    peer_summary["multiples"][k] = str(quantize_multiple(val))
                else:
                    peer_summary["multiples"][k] = "N/M"
            peer_results.append(peer_summary)

        metrics_to_report = (
            [m for m in METRIC_CHOICES if m != "all"]
            if metric_filter == "all"
            else [metric_filter]
        )

        statistics: dict[str, Any] = {}
        implied_valuations: dict[str, Any] = {}

        for m in metrics_to_report:
            series = multiples_by_metric.get(m, [])
            if not series:
                continue
            summary = summarize_multiples(series)
            statistics[m] = summary
            if target:
                implied = compute_target_implied_valuations(summary, m, target)
                if implied:
                    implied_valuations[m] = implied

        result = {
            "target": target.get("name", target.get("ticker", "Target")),
            "peer_count": len(peers_raw),
            "metric_filter": metric_filter,
            "peers": peer_results,
            "multiples_summary": statistics,
            "target_implied_valuations": implied_valuations,
        }
        return stamp_payload(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        default=str(_HERE / "fixtures" / "synthetic_comps.json"),
        help="Path to comparable companies JSON fixture",
    )
    parser.add_argument(
        "--metric",
        choices=METRIC_CHOICES,
        default="all",
        help="Filter valuation metric (default: all)",
    )
    parser.add_argument("--target-ebitda", help="Override target company EBITDA (Decimal string)")
    parser.add_argument("--target-net-income", help="Override target company Net Income (Decimal string)")
    parser.add_argument("--target-net-debt", help="Override target company Net Debt (Decimal string)")
    parser.add_argument("--target-shares", help="Override target company diluted shares (Decimal string)")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output")
    parser.add_argument("--dry-run", action="store_true", help="Validate fixture and exit without full calc")

    args = parser.parse_args(argv)
    path = Path(args.fixture)

    if args.dry_run:
        plan = stamp_payload(
            {
                "dry_run": True,
                "fixture": path.as_posix(),
                "metric": args.metric,
                "target_overrides": {
                    "ebitda": args.target_ebitda,
                    "net_income": args.target_net_income,
                    "net_debt": args.target_net_debt,
                    "shares_outstanding": args.target_shares,
                },
            }
        )
        print(json.dumps(plan, indent=2))
        return 0

    try:
        fixture = json.loads(path.read_text(encoding="utf-8"))
        overrides = {
            "ebitda": args.target_ebitda,
            "net_income": args.target_net_income,
            "net_debt": args.target_net_debt,
            "shares_outstanding": args.target_shares,
        }
        result = run_comps(fixture, metric_filter=args.metric, target_overrides=overrides)
    except (OSError, KeyError, ValueError, FloatLedgerError, json.JSONDecodeError, ZeroDivisionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["advisory_stamp"])
        print(f"Target: {result['target']} | Peers Analyzed: {result['peer_count']}")
        for m, stats in result["multiples_summary"].items():
            print(f"\n--- {m.upper()} ---")
            print(
                f"Harmonic Mean: {stats.get('harmonic_mean')} | "
                f"Arithmetic Mean: {stats.get('arithmetic_mean')} | "
                f"Median: {stats.get('median')} | "
                f"IQR: [{stats.get('p25')} - {stats.get('p75')}]"
            )
            if m in result["target_implied_valuations"]:
                imp = result["target_implied_valuations"][m]
                if "harmonic_mean" in imp:
                    print(f"Implied Share Price (Harmonic): ${imp['harmonic_mean']['value_per_share']}")
                if "median" in imp:
                    print(f"Implied Share Price (Median): ${imp['median']['value_per_share']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
