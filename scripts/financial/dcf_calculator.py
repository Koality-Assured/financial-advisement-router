"""Multi-stage DCF and CAPM WACC on Decimal ledgers (advisory research only).

tags: [financial, dcf, valuation, decimal]
routing_hints: [dcf, wacc, capm, gordon-growth, sensitivity, decimal]

Unlevered free cash flow discounted at WACC. Terminal value via Gordon growth
with g capped at the fixture long-run GDP growth. Not a recommendation.
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

from _ledger import (  # noqa: E402
    ADVISORY_STAMP,
    FloatLedgerError,
    ledger_context,
    quantize_money,
    quantize_rate,
    stamp_payload,
    to_decimal,
)


def capm_cost_of_equity(risk_free: Decimal, beta: Decimal, erp: Decimal) -> Decimal:
    return risk_free + beta * erp


def wacc(
    *,
    cost_of_equity: Decimal,
    equity_weight: Decimal,
    pre_tax_cost_of_debt: Decimal,
    debt_weight: Decimal,
    tax_rate: Decimal,
) -> Decimal:
    after_tax_kd = pre_tax_cost_of_debt * (Decimal("1") - tax_rate)
    return equity_weight * cost_of_equity + debt_weight * after_tax_kd


def gordon_terminal(last_fcf: Decimal, growth: Decimal, discount: Decimal) -> Decimal:
    if growth >= discount:
        raise ValueError("terminal growth must be strictly below WACC")
    return last_fcf * (Decimal("1") + growth) / (discount - growth)


def dcf_enterprise_value(
    fcfs: list[Decimal],
    discount: Decimal,
    terminal_growth: Decimal,
) -> tuple[Decimal, Decimal, list[Decimal]]:
    if not fcfs:
        raise ValueError("fcf list is empty")
    one = Decimal("1")
    pv_fcfs: list[Decimal] = []
    for t, cash in enumerate(fcfs, start=1):
        pv_fcfs.append(cash / (one + discount) ** t)
    tv = gordon_terminal(fcfs[-1], terminal_growth, discount)
    pv_tv = tv / (one + discount) ** len(fcfs)
    ev = sum(pv_fcfs, Decimal("0")) + pv_tv
    return ev, pv_tv, pv_fcfs


def value_from_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    capm = fixture["capm"]
    structure = fixture["capital_structure"]
    rf = to_decimal(capm["risk_free"], field="risk_free")
    beta = to_decimal(capm["beta"], field="beta")
    erp = to_decimal(capm["equity_risk_premium"], field="equity_risk_premium")
    we = to_decimal(structure["equity_weight"], field="equity_weight")
    wd = to_decimal(structure["debt_weight"], field="debt_weight")
    kd = to_decimal(structure["pre_tax_cost_of_debt"], field="pre_tax_cost_of_debt")
    tax = to_decimal(structure["tax_rate"], field="tax_rate")
    if we + wd != Decimal("1"):
        raise ValueError("equity_weight + debt_weight must equal 1")
    fcfs = [to_decimal(v, field=f"fcf[{i}]") for i, v in enumerate(fixture["fcf"])]
    g = to_decimal(fixture["terminal_growth"], field="terminal_growth")
    g_cap = to_decimal(fixture.get("long_run_gdp_growth_cap", "0.03"), field="gdp_cap")
    if g > g_cap:
        raise ValueError("terminal growth exceeds long-run GDP cap in fixture")
    net_debt = to_decimal(fixture.get("net_debt", "0"), field="net_debt")
    shares = to_decimal(fixture.get("shares_outstanding", "1"), field="shares_outstanding")
    if shares <= 0:
        raise ValueError("shares_outstanding must be positive")
    with ledger_context():
        ke = capm_cost_of_equity(rf, beta, erp)
        discount = wacc(
            cost_of_equity=ke,
            equity_weight=we,
            pre_tax_cost_of_debt=kd,
            debt_weight=wd,
            tax_rate=tax,
        )
        ev, pv_tv, pv_fcfs = dcf_enterprise_value(fcfs, discount, g)
        equity = ev - net_debt
        per_share = equity / shares
        return stamp_payload(
            {
                "issuer": fixture.get("issuer", "synthetic"),
                "cost_of_equity": str(quantize_rate(ke)),
                "wacc": str(quantize_rate(discount)),
                "terminal_growth": str(quantize_rate(g)),
                "enterprise_value": str(quantize_money(ev)),
                "pv_terminal": str(quantize_money(pv_tv)),
                "pv_explicit_fcf": [str(quantize_money(x)) for x in pv_fcfs],
                "net_debt": str(quantize_money(net_debt)),
                "equity_value": str(quantize_money(equity)),
                "value_per_share": str(quantize_money(per_share)),
            }
        )


def sensitivity_table(
    fixture: dict[str, Any],
    *,
    wacc_deltas: tuple[str, ...] = ("-0.01", "0", "0.01"),
    g_deltas: tuple[str, ...] = ("-0.005", "0", "0.005"),
) -> dict[str, Any]:
    base = value_from_fixture(fixture)
    base_wacc = to_decimal(base["wacc"], field="wacc")
    base_g = to_decimal(fixture["terminal_growth"], field="terminal_growth")
    rows: list[dict[str, str]] = []
    with ledger_context():
        for dw in wacc_deltas:
            for dg in g_deltas:
                discount = base_wacc + to_decimal(dw, field="dw")
                growth = base_g + to_decimal(dg, field="dg")
                fcfs = [to_decimal(v, field="fcf") for v in fixture["fcf"]]
                ev, _, _ = dcf_enterprise_value(fcfs, discount, growth)
                equity = ev - to_decimal(fixture.get("net_debt", "0"), field="net_debt")
                rows.append(
                    {
                        "wacc": str(quantize_rate(discount)),
                        "g": str(quantize_rate(growth)),
                        "equity_value": str(quantize_money(equity)),
                    }
                )
    return stamp_payload({"base": base, "sensitivity": rows})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        default=str(_HERE / "fixtures" / "synthetic_dcf.json"),
        help="Synthetic DCF JSON (default: scripts/financial/fixtures/synthetic_dcf.json)",
    )
    parser.add_argument("--sensitivity", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    path = Path(args.fixture)
    if args.dry_run:
        print(json.dumps(stamp_payload({"dry_run": True, "fixture": path.as_posix()}), indent=2))
        return 0
    try:
        fixture = json.loads(path.read_text(encoding="utf-8"))
        result = sensitivity_table(fixture) if args.sensitivity else value_from_fixture(fixture)
    except (OSError, KeyError, ValueError, FloatLedgerError, json.JSONDecodeError, ZeroDivisionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["advisory_stamp"])
        if "equity_value" in result:
            print(f"equity_value={result['equity_value']}")
        else:
            print(f"rows={len(result['sensitivity'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
