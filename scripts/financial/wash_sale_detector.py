"""IRC Section 1091 61-day wash-sale detector and tax-loss replacement engine.

tags: [financial, wash-sale, tax-loss, compliance, decimal]
routing_hints: [wash-sale, irc-1091, 61-day-window, tax-loss-harvesting, replacement-etf, decimal]

Scans trade lots against Internal Revenue Code (IRC) Section 1091 rules. Detects
disallowed losses when substantially identical securities are acquired within a
61-day window (30 days before, day of sale, and 30 days after). Calculates loss
disallowance, replacement cost basis adjustment, and holding period tacking notes.
Generates replacement ETF suggestions across correlated indexes to harvest tax losses
without violating Section 1091. Strict Decimal math; advisory research only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from decimal import Decimal
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
    stamp_payload,
    to_decimal,
)

# Standard tax-loss replacement ETF pairings across distinct index benchmarks.
# Selling an asset at a loss and purchasing a replacement ETF from a different index
# family preserves core asset allocation while avoiding the "substantially identical" rule.
REPLACEMENT_ETF_REGISTRY: dict[str, list[dict[str, str]]] = {
    # US Large Cap Core / S&P 500
    "SPY": [
        {
            "replacement_symbol": "VTI",
            "replacement_name": "Vanguard Total Stock Market ETF",
            "underlying_index": "CRSP US Total Market Index",
            "correlation": "0.99",
            "rationale": "Swaps from S&P 500 to all-cap US equity index, preserving beta while avoiding identical index identity.",
        },
        {
            "replacement_symbol": "SCHB",
            "replacement_name": "Schwab U.S. Broad Market ETF",
            "underlying_index": "Dow Jones U.S. Broad Stock Market Index",
            "correlation": "0.99",
            "rationale": "Broad market index alternative with distinct benchmark construction.",
        },
        {
            "replacement_symbol": "IWB",
            "replacement_name": "iShares Russell 1000 ETF",
            "underlying_index": "Russell 1000 Index",
            "correlation": "0.99",
            "rationale": "Russell 1000 benchmark alternative covering top 1,000 US equities.",
        },
    ],
    "VOO": [
        {
            "replacement_symbol": "VTI",
            "replacement_name": "Vanguard Total Stock Market ETF",
            "underlying_index": "CRSP US Total Market Index",
            "correlation": "0.99",
            "rationale": "Broadens exposure to total market while harvesting S&P 500 loss.",
        },
        {
            "replacement_symbol": "IWB",
            "replacement_name": "iShares Russell 1000 ETF",
            "underlying_index": "Russell 1000 Index",
            "correlation": "0.99",
            "rationale": "Russell 1000 benchmark alternative.",
        },
    ],
    "IVV": [
        {
            "replacement_symbol": "SCHB",
            "replacement_name": "Schwab U.S. Broad Market ETF",
            "underlying_index": "Dow Jones U.S. Broad Stock Market Index",
            "correlation": "0.99",
            "rationale": "Broad market replacement ETF.",
        },
        {
            "replacement_symbol": "VTI",
            "replacement_name": "Vanguard Total Stock Market ETF",
            "underlying_index": "CRSP US Total Market Index",
            "correlation": "0.99",
            "rationale": "CRSP total market alternative.",
        },
    ],
    # US Total Stock Market
    "VTI": [
        {
            "replacement_symbol": "VOO",
            "replacement_name": "Vanguard S&P 500 ETF",
            "underlying_index": "S&P 500 Index",
            "correlation": "0.99",
            "rationale": "Focuses on large-cap core index while harvesting total-market loss.",
        },
        {
            "replacement_symbol": "IWB",
            "replacement_name": "iShares Russell 1000 ETF",
            "underlying_index": "Russell 1000 Index",
            "correlation": "0.99",
            "rationale": "Russell 1000 large-cap alternative.",
        },
    ],
    "SCHB": [
        {
            "replacement_symbol": "VOO",
            "replacement_name": "Vanguard S&P 500 ETF",
            "underlying_index": "S&P 500 Index",
            "correlation": "0.99",
            "rationale": "S&P 500 benchmark alternative.",
        },
    ],
    # US Large Cap Growth / Tech / Nasdaq-100
    "QQQ": [
        {
            "replacement_symbol": "VUG",
            "replacement_name": "Vanguard Growth ETF",
            "underlying_index": "CRSP US Large Cap Growth Index",
            "correlation": "0.96",
            "rationale": "Captures large-cap growth style factors without Nasdaq exchange listing restrictions.",
        },
        {
            "replacement_symbol": "IWF",
            "replacement_name": "iShares Russell 1000 Growth ETF",
            "underlying_index": "Russell 1000 Growth Index",
            "correlation": "0.97",
            "rationale": "Diversified multi-sector growth benchmark alternative to Nasdaq 100.",
        },
        {
            "replacement_symbol": "XLK",
            "replacement_name": "Technology Select Sector SPDR Fund",
            "underlying_index": "Technology Select Sector Index",
            "correlation": "0.93",
            "rationale": "Pure-play technology sector basket replacing Nasdaq 100 exposure.",
        },
    ],
    "QQQM": [
        {
            "replacement_symbol": "VUG",
            "replacement_name": "Vanguard Growth ETF",
            "underlying_index": "CRSP US Large Cap Growth Index",
            "correlation": "0.96",
            "rationale": "CRSP large cap growth benchmark substitute.",
        },
    ],
    # Small Cap US
    "IWM": [
        {
            "replacement_symbol": "IJR",
            "replacement_name": "iShares Core S&P Small-Cap ETF",
            "underlying_index": "S&P SmallCap 600 Index",
            "correlation": "0.97",
            "rationale": "Switches from Russell 2000 to S&P 600 index with earnings quality screen.",
        },
        {
            "replacement_symbol": "VB",
            "replacement_name": "Vanguard Small-Cap ETF",
            "underlying_index": "CRSP US Small Cap Index",
            "correlation": "0.97",
            "rationale": "CRSP small cap benchmark replacement.",
        },
    ],
    # International Developed
    "VEA": [
        {
            "replacement_symbol": "IEFA",
            "replacement_name": "iShares Core MSCI EAFE ETF",
            "underlying_index": "MSCI EAFE IMI Index",
            "correlation": "0.99",
            "rationale": "Switches from FTSE Developed All Cap ex US to MSCI EAFE IMI benchmark.",
        },
        {
            "replacement_symbol": "SPDW",
            "replacement_name": "SPDR Portfolio Developed World ex-US ETF",
            "underlying_index": "S&P Developed Ex-U.S. BMI Index",
            "correlation": "0.99",
            "rationale": "S&P developed world benchmark replacement.",
        },
    ],
    # Fixed Income / Aggregate Bond
    "BND": [
        {
            "replacement_symbol": "SPAB",
            "replacement_name": "SPDR Portfolio Aggregate Bond ETF",
            "underlying_index": "Bloomberg U.S. Aggregate Bond Index",
            "correlation": "0.99",
            "rationale": "Substitute aggregate bond ETF with distinct custodial structure.",
        },
        {
            "replacement_symbol": "IEF",
            "replacement_name": "iShares 7-10 Year Treasury Bond ETF",
            "underlying_index": "ICE U.S. Treasury 7-10 Year Bond Index",
            "correlation": "0.91",
            "rationale": "Maintains intermediate duration with pure sovereign Treasury backing.",
        },
    ],
    "AGG": [
        {
            "replacement_symbol": "SCHZ",
            "replacement_name": "Schwab U.S. Aggregate Bond ETF",
            "underlying_index": "Bloomberg U.S. Aggregate Bond Index",
            "correlation": "0.99",
            "rationale": "Schwab aggregate bond equivalent.",
        },
    ],
    # Single Tech Stocks -> Sector / Industry ETFs
    "AAPL": [
        {
            "replacement_symbol": "XLK",
            "replacement_name": "Technology Select Sector SPDR Fund",
            "underlying_index": "Technology Select Sector Index",
            "correlation": "0.85",
            "rationale": "Broad tech sector ETF holding heavy Apple weighting without individual security identity.",
        },
        {
            "replacement_symbol": "VGT",
            "replacement_name": "Vanguard Information Technology ETF",
            "underlying_index": "MSCI US Investable Market Information Technology 25/50 Index",
            "correlation": "0.86",
            "rationale": "Tech basket ETF preserving sector exposure while harvesting single-stock tax loss.",
        },
    ],
    "MSFT": [
        {
            "replacement_symbol": "XLK",
            "replacement_name": "Technology Select Sector SPDR Fund",
            "underlying_index": "Technology Select Sector Index",
            "correlation": "0.86",
            "rationale": "Tech sector ETF holding substantial Microsoft allocation.",
        },
        {
            "replacement_symbol": "IGV",
            "replacement_name": "iShares Expanded Tech-Software Sector ETF",
            "underlying_index": "S&P North American Technology Software Index",
            "correlation": "0.88",
            "rationale": "Software sector focus replacing direct Microsoft equity exposure.",
        },
    ],
    "NVDA": [
        {
            "replacement_symbol": "SMH",
            "replacement_name": "VanEck Semiconductor ETF",
            "underlying_index": "MVIS US Listed Semiconductor 25 Index",
            "correlation": "0.92",
            "rationale": "Semiconductor industry ETF holding heavy Nvidia weighting.",
        },
        {
            "replacement_symbol": "SOXX",
            "replacement_name": "iShares Semiconductor ETF",
            "underlying_index": "NYSE Semiconductor Index",
            "correlation": "0.91",
            "rationale": "Diversified semiconductor basket avoiding single-name wash sale.",
        },
    ],
}

FALLBACK_EQUITY_REPLACEMENTS = [
    {
        "replacement_symbol": "VTI",
        "replacement_name": "Vanguard Total Stock Market ETF",
        "underlying_index": "CRSP US Total Market Index",
        "correlation": "0.80 - 0.95",
        "rationale": "Broad US equity diversification preserving market exposure during wash-sale exclusion period.",
    },
    {
        "replacement_symbol": "VOO",
        "replacement_name": "Vanguard S&P 500 ETF",
        "underlying_index": "S&P 500 Index",
        "correlation": "0.80 - 0.95",
        "rationale": "Core large-cap replacement maintaining equity participation.",
    },
]


def parse_date(date_val: str | dt.date) -> dt.date:
    """Parse date from ISO string or dt.date object."""
    if isinstance(date_val, dt.date):
        return date_val
    return dt.date.fromisoformat(str(date_val).strip())


def get_replacement_suggestions(symbol: str) -> list[dict[str, str]]:
    """Return curated ETF replacement candidates for tax-loss harvesting."""
    sym_upper = symbol.upper()
    if sym_upper in REPLACEMENT_ETF_REGISTRY:
        return REPLACEMENT_ETF_REGISTRY[sym_upper]
    return FALLBACK_EQUITY_REPLACEMENTS


def detect_wash_sales(
    transactions: Sequence[Mapping[str, Any]],
    *,
    window_days: int = 30,
    symbol_filter: str | None = None,
) -> dict[str, Any]:
    """Scan transaction lots against IRC Section 1091 61-day window rules.

    The 61-day window spans:
    - 30 calendar days before the loss sale date
    - The date of sale
    - 30 calendar days after the loss sale date

    Returns detailed audit records for disallowed and allowed losses, adjusted
    replacement cost bases, and replacement ETF candidates.
    """
    if window_days < 1:
        raise ValueError("window_days must be at least 1")

    # Group and sort transactions by symbol and chronological date
    parsed_txs: list[dict[str, Any]] = []
    with ledger_context():
        for i, tx in enumerate(transactions):
            sym = str(tx["symbol"]).upper().strip()
            if symbol_filter and sym != symbol_filter.upper():
                continue
            action = str(tx["action"]).upper().strip()
            if action not in ("BUY", "SELL"):
                raise ValueError(f"transaction {i} has invalid action '{action}'; must be BUY or SELL")
            qty = to_decimal(tx["quantity"], field=f"tx[{i}].quantity")
            if qty <= 0:
                raise ValueError(f"transaction {i} quantity must be positive")
            price = to_decimal(tx["price"], field=f"tx[{i}].price")
            basis = (
                to_decimal(tx["cost_basis_per_share"], field=f"tx[{i}].cost_basis_per_share")
                if "cost_basis_per_share" in tx and tx["cost_basis_per_share"] is not None
                else price
            )
            parsed_txs.append(
                {
                    "trade_id": str(tx.get("trade_id", f"TX-{i+1}")),
                    "date": parse_date(tx["date"]),
                    "symbol": sym,
                    "action": action,
                    "quantity": qty,
                    "price": price,
                    "cost_basis_per_share": basis,
                }
            )

    # Sort chronologically
    parsed_txs.sort(key=lambda t: t["date"])

    # Separate buys and sells
    buys: list[dict[str, Any]] = [
        {**t, "available_qty": t["quantity"], "allocated_disallowed_loss": Decimal("0")}
        for t in parsed_txs
        if t["action"] == "BUY"
    ]
    sells: list[dict[str, Any]] = [t for t in parsed_txs if t["action"] == "SELL"]

    wash_sale_records: list[dict[str, Any]] = []
    clean_loss_records: list[dict[str, Any]] = []

    total_realized_loss = Decimal("0")
    total_disallowed_loss = Decimal("0")
    symbols_with_losses: set[str] = set()

    with ledger_context():
        for sell in sells:
            pnl_per_share = sell["price"] - sell["cost_basis_per_share"]
            if pnl_per_share >= 0:
                # Gain or breakeven sale - IRC 1091 only applies to losses
                continue

            loss_per_share = pnl_per_share  # negative value
            sold_qty = sell["quantity"]
            realized_loss = loss_per_share * sold_qty
            total_realized_loss += realized_loss
            symbols_with_losses.add(sell["symbol"])

            loss_date = sell["date"]
            win_start = loss_date - dt.timedelta(days=window_days)
            win_end = loss_date + dt.timedelta(days=window_days)

            # Find matching replacement buys within the 61-day window
            # IRS Pub 550: match chronological earliest replacement acquisitions
            remaining_loss_qty = sold_qty

            for buy in buys:
                if buy["symbol"] != sell["symbol"]:
                    continue
                if buy["available_qty"] <= 0:
                    continue
                buy_date = buy["date"]
                # Must be inside the 61-day window [loss_date - 30d, loss_date + 30d]
                if not (win_start <= buy_date <= win_end):
                    continue

                days_diff = (buy_date - loss_date).days
                matched_shares = min(remaining_loss_qty, buy["available_qty"])
                disallowed_chunk = matched_shares * abs(loss_per_share)

                buy["available_qty"] -= matched_shares
                buy["allocated_disallowed_loss"] += disallowed_chunk
                remaining_loss_qty -= matched_shares
                total_disallowed_loss += disallowed_chunk

                # Calculate adjusted replacement cost basis
                # Disallowed loss is added to the basis of the replacement shares
                adjusted_basis_per_share = buy["price"] + (disallowed_chunk / matched_shares)

                wash_sale_records.append(
                    {
                        "loss_trade_id": sell["trade_id"],
                        "replacement_trade_id": buy["trade_id"],
                        "symbol": sell["symbol"],
                        "sale_date": loss_date.isoformat(),
                        "purchase_date": buy_date.isoformat(),
                        "window_offset_days": days_diff,
                        "disallowed_shares": str(matched_shares),
                        "sale_price": str(quantize_money(sell["price"])),
                        "cost_basis_per_share": str(quantize_money(sell["cost_basis_per_share"])),
                        "loss_per_share": str(quantize_money(loss_per_share)),
                        "disallowed_loss": str(quantize_money(-disallowed_chunk)),
                        "replacement_purchase_price": str(quantize_money(buy["price"])),
                        "adjusted_replacement_basis_per_share": str(quantize_money(adjusted_basis_per_share)),
                        "irc_holding_period_rule": "Holding period of sold shares tacks onto replacement shares under IRC 1223(3).",
                    }
                )

                if remaining_loss_qty == 0:
                    break

            if remaining_loss_qty > 0:
                allowed_loss = remaining_loss_qty * loss_per_share
                clean_loss_records.append(
                    {
                        "trade_id": sell["trade_id"],
                        "symbol": sell["symbol"],
                        "sale_date": loss_date.isoformat(),
                        "allowed_shares": str(remaining_loss_qty),
                        "sale_price": str(quantize_money(sell["price"])),
                        "cost_basis_per_share": str(quantize_money(sell["cost_basis_per_share"])),
                        "loss_per_share": str(quantize_money(loss_per_share)),
                        "allowed_loss": str(quantize_money(allowed_loss)),
                    }
                )

        net_allowable_loss = total_realized_loss + total_disallowed_loss  # both negative

        # Generate replacement suggestions for all traded symbols that incurred realized losses
        replacement_suggestions: dict[str, list[dict[str, str]]] = {}
        for sym in sorted(symbols_with_losses):
            replacement_suggestions[sym] = get_replacement_suggestions(sym)

        payload = {
            "window_days": window_days,
            "total_61_day_window_description": f"[-{window_days} days, sale day, +{window_days} days]",
            "total_realized_loss": str(quantize_money(total_realized_loss)),
            "total_disallowed_loss": str(quantize_money(-total_disallowed_loss)),
            "net_allowable_loss": str(quantize_money(net_allowable_loss)),
            "wash_sale_count": len(wash_sale_records),
            "clean_loss_count": len(clean_loss_records),
            "wash_sales": wash_sale_records,
            "clean_losses": clean_loss_records,
            "replacement_etf_suggestions": replacement_suggestions,
            "compliance_note": (
                "IRC Section 1091 disallows deduction of losses where substantially identical "
                "securities are purchased within 30 days before or after the sale. Disallowed "
                "loss is added to the basis of acquired replacement shares."
            ),
        }
        return stamp_payload(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        default=str(_HERE / "fixtures" / "synthetic_wash_sale.json"),
        help="Path to trade lots JSON fixture",
    )
    parser.add_argument("--symbol", help="Filter analysis to a specific ticker symbol")
    parser.add_argument(
        "--window-days",
        type=int,
        default=30,
        help="One-sided window duration in days (default: 30 for 61-day window)",
    )
    parser.add_argument("--json", action="store_true", help="Print structured JSON output")
    parser.add_argument("--dry-run", action="store_true", help="Inspect transaction plan and exit")

    args = parser.parse_args(argv)
    path = Path(args.fixture)

    if args.dry_run:
        plan = stamp_payload(
            {
                "dry_run": True,
                "fixture": path.as_posix(),
                "symbol_filter": args.symbol,
                "window_days": args.window_days,
            }
        )
        print(json.dumps(plan, indent=2))
        return 0

    try:
        fixture = json.loads(path.read_text(encoding="utf-8"))
        txs = fixture.get("transactions", [])
        result = detect_wash_sales(
            txs,
            window_days=args.window_days,
            symbol_filter=args.symbol,
        )
    except (OSError, KeyError, ValueError, FloatLedgerError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["advisory_stamp"])
        print(
            f"Realized Loss: {result['total_realized_loss']} | "
            f"Disallowed (Wash): {result['total_disallowed_loss']} | "
            f"Net Allowable: {result['net_allowable_loss']}"
        )
        print(f"Wash Sales Identified: {result['wash_sale_count']}")
        for w in result["wash_sales"]:
            print(
                f"  - [{w['symbol']}] Sold {w['sale_date']} -> Repurchased {w['purchase_date']} "
                f"({w['window_offset_days']:+d}d) | Disallowed: {w['disallowed_loss']} | "
                f"New Basis: {w['adjusted_replacement_basis_per_share']}"
            )
        if result["replacement_etf_suggestions"]:
            print("\nTax-Loss Replacement ETF Recommendations:")
            for sym, recs in result["replacement_etf_suggestions"].items():
                print(f"  {sym} -> {', '.join(r['replacement_symbol'] for r in recs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
