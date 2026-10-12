"""Comprehensive tests for financial valuation, risk, portfolio, comps, and compliance scripts.

tags: [tests, financial, decimal]
routing_hints: [tests, dcf, var, portfolio, edgar, comps, wash-sale, decimal]
"""

from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from decimal import Decimal
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
_FIN = _SCRIPTS / "financial"
sys.path.insert(0, str(_FIN))

from _ledger import (  # noqa: E402
    ADVISORY_STAMP,
    FloatLedgerError,
    ledger_context,
    quantize_money,
    quantize_multiple,
    to_decimal,
)
from comps_calculator import (  # noqa: E402
    arithmetic_mean,
    compute_peer_multiples,
    compute_target_implied_valuations,
    harmonic_mean,
    main as comps_main,
    run_comps,
    summarize_multiples,
    valuation_percentiles,
)
from dcf_calculator import (  # noqa: E402
    capm_cost_of_equity,
    dcf_enterprise_value,
    gordon_terminal,
    main as dcf_main,
    sensitivity_table,
    value_from_fixture,
    wacc,
)
from edgar_ingest import (  # noqa: E402
    extract_gaap_facts,
    ingest_payload,
    main as edgar_main,
    pad_cik,
)
from monte_carlo_var import (  # noqa: E402
    bootstrap_paths,
    historical_cvar,
    historical_var,
    main as var_main,
    parametric_var,
    run_fixture as run_var_fixture,
)
from portfolio_optimizer import (  # noqa: E402
    main as portfolio_main,
    max_sharpe_weights,
    min_variance_weights,
    optimize_from_fixture,
    portfolio_variance,
    sortino_ratio,
    target_return_weights,
)
from wash_sale_detector import (  # noqa: E402
    detect_wash_sales,
    get_replacement_suggestions,
    main as wash_sale_main,
    parse_date,
)

FIXTURES = _FIN / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class TestCompsCalculator(unittest.TestCase):
    def test_peer_multiples_derived_and_direct(self) -> None:
        with ledger_context():
            # Derived from enterprise value and ebitda
            peer1 = {
                "ticker": "ABC",
                "enterprise_value": "500.00",
                "ebitda": "50.00",
                "market_cap": "400.00",
                "net_income": "25.00",
                "revenue": "200.00",
                "book_value": "100.00",
            }
            m1 = compute_peer_multiples(peer1)
            self.assertEqual(m1["ev_ebitda"], Decimal("10"))
            self.assertEqual(m1["pe"], Decimal("16"))
            self.assertEqual(m1["ev_revenue"], Decimal("2.5"))
            self.assertEqual(m1["price_to_book"], Decimal("4"))

            # Derived from price and eps
            peer2 = {
                "ticker": "XYZ",
                "price": "60.00",
                "eps": "3.00",
            }
            m2 = compute_peer_multiples(peer2)
            self.assertEqual(m2["pe"], Decimal("20"))

            # Direct multiples provided
            peer3 = {
                "ticker": "DIR",
                "ev_ebitda": "14.50",
                "pe": "22.00",
            }
            m3 = compute_peer_multiples(peer3)
            self.assertEqual(m3["ev_ebitda"], Decimal("14.50"))
            self.assertEqual(m3["pe"], Decimal("22.00"))

            # Non-meaningful (negative or zero denominator)
            peer_neg = {
                "ticker": "NEG",
                "enterprise_value": "100.00",
                "ebitda": "-10.00",
                "market_cap": "80.00",
                "net_income": "0",
            }
            m_neg = compute_peer_multiples(peer_neg)
            self.assertIsNone(m_neg["ev_ebitda"])
            self.assertIsNone(m_neg["pe"])

    def test_arithmetic_mean(self) -> None:
        with ledger_context():
            vals = [Decimal("10"), Decimal("20"), Decimal("30")]
            self.assertEqual(arithmetic_mean(vals), Decimal("20"))
            with self.assertRaises(ValueError):
                arithmetic_mean([])

    def test_harmonic_mean(self) -> None:
        with ledger_context():
            # Classic harmonic mean of 10 and 20: 2 / (1/10 + 1/20) = 2 / (3/20) = 40/3 = 13.3333...
            vals = [Decimal("10"), Decimal("20")]
            h = harmonic_mean(vals)
            expected = Decimal("40") / Decimal("3")
            self.assertEqual(quantize_multiple(h), quantize_multiple(expected))
            # Harmonic mean is strictly less than or equal to arithmetic mean
            self.assertTrue(h <= arithmetic_mean(vals))

            # Non-positive values raise error if no positive values remain
            with self.assertRaises(ValueError):
                harmonic_mean([Decimal("-5"), Decimal("0")])

    def test_valuation_percentiles(self) -> None:
        with ledger_context():
            vals = [Decimal("10"), Decimal("12"), Decimal("14"), Decimal("16"), Decimal("18")]
            pcts = valuation_percentiles(vals)
            self.assertEqual(pcts["min"], Decimal("10"))
            self.assertEqual(pcts["max"], Decimal("18"))
            self.assertEqual(pcts["median"], Decimal("14"))
            self.assertEqual(pcts["p25"], Decimal("12"))
            self.assertEqual(pcts["p75"], Decimal("16"))

            # Single value edge case
            single_pcts = valuation_percentiles([Decimal("15")])
            self.assertEqual(single_pcts["median"], Decimal("15"))
            self.assertEqual(single_pcts["min"], Decimal("15"))

    def test_summarize_multiples(self) -> None:
        with ledger_context():
            vals = [Decimal("10"), Decimal("12"), Decimal("14")]
            summary = summarize_multiples(vals)
            self.assertEqual(summary["count"], 3)
            self.assertEqual(summary["valid_count"], 3)
            self.assertEqual(summary["median"], "12.0000")
            self.assertIn("iqr", summary)
            self.assertIn("std_dev", summary)

    def test_target_implied_valuations(self) -> None:
        with ledger_context():
            stats = {
                "harmonic_mean": "10.0000",
                "arithmetic_mean": "12.0000",
                "median": "11.0000",
            }
            target = {
                "ebitda": "20000000.00",
                "net_debt": "10000000.00",
                "shares_outstanding": "2000000",
            }
            implied = compute_target_implied_valuations(stats, "ev_ebitda", target)
            # harmonic: ev = 10 * 20m = 200m; equity = 200m - 10m = 190m; per_share = 190m / 2m = 95.00
            self.assertEqual(implied["harmonic_mean"]["enterprise_value"], "200000000.00")
            self.assertEqual(implied["harmonic_mean"]["equity_value"], "190000000.00")
            self.assertEqual(implied["harmonic_mean"]["value_per_share"], "95.00")

    def test_target_implied_valuations_price_to_book(self) -> None:
        with ledger_context():
            stats = {
                "harmonic_mean": "3.0000",
                "arithmetic_mean": "4.0000",
                "median": "3.5000",
            }
            # Target with total book_value
            target_bv = {
                "book_value": "50000000.00",
                "net_debt": "10000000.00",
                "shares_outstanding": "2000000",
            }
            implied_bv = compute_target_implied_valuations(stats, "price_to_book", target_bv)
            # harmonic: equity = 3 * 50m = 150m; ev = 150m + 10m = 160m; per_share = 150m / 2m = 75.00
            self.assertEqual(implied_bv["harmonic_mean"]["equity_value"], "150000000.00")
            self.assertEqual(implied_bv["harmonic_mean"]["enterprise_value"], "160000000.00")
            self.assertEqual(implied_bv["harmonic_mean"]["value_per_share"], "75.00")

            # Target with book_value_per_share
            target_bvps = {
                "book_value_per_share": "25.00",
                "net_debt": "10000000.00",
                "shares_outstanding": "2000000",
            }
            implied_bvps = compute_target_implied_valuations(stats, "price_to_book", target_bvps)
            # harmonic: per_share = 3 * 25 = 75.00; equity = 75 * 2m = 150m; ev = 150m + 10m = 160m
            self.assertEqual(implied_bvps["harmonic_mean"]["value_per_share"], "75.00")
            self.assertEqual(implied_bvps["harmonic_mean"]["equity_value"], "150000000.00")
            self.assertEqual(implied_bvps["harmonic_mean"]["enterprise_value"], "160000000.00")

    def test_comps_fixture_and_replay(self) -> None:
        fixture = _load("synthetic_comps.json")
        first = run_comps(fixture)
        second = run_comps(fixture)
        self.assertEqual(first, second)
        self.assertEqual(first["advisory_stamp"], ADVISORY_STAMP)
        self.assertFalse(first["licensed_advice"])
        self.assertEqual(first["peer_count"], 5)
        self.assertIn("ev_ebitda", first["multiples_summary"])
        self.assertIn("pe", first["multiples_summary"])

    def test_float_rejection_in_comps(self) -> None:
        peer_with_float = {
            "name": "Float Co",
            "ticker": "FLT",
            "enterprise_value": 500.0,  # float literal
            "ebitda": "50.00",
        }
        with self.assertRaises(FloatLedgerError):
            compute_peer_multiples(peer_with_float)

    def test_comps_cli_execution(self) -> None:
        f = io.StringIO()
        with redirect_stdout(f):
            rc = comps_main(["--json"])
        self.assertEqual(rc, 0)
        output = json.loads(f.getvalue())
        self.assertEqual(output["target"], "Apex Cloud Technologies")

        # Dry run CLI
        f_dry = io.StringIO()
        with redirect_stdout(f_dry):
            rc_dry = comps_main(["--dry-run"])
        self.assertEqual(rc_dry, 0)
        output_dry = json.loads(f_dry.getvalue())
        self.assertTrue(output_dry["dry_run"])

        # Metric filter CLI
        f_metric = io.StringIO()
        with redirect_stdout(f_metric):
            rc_metric = comps_main(["--metric", "ev_ebitda", "--json"])
        self.assertEqual(rc_metric, 0)
        output_metric = json.loads(f_metric.getvalue())
        self.assertEqual(output_metric["metric_filter"], "ev_ebitda")

        # Invalid fixture error
        f_err = io.StringIO()
        with redirect_stderr(f_err):
            rc_err = comps_main(["--fixture", "nonexistent_file_xyz.json"])
        self.assertEqual(rc_err, 2)


class TestWashSaleDetector(unittest.TestCase):
    def test_parse_date(self) -> None:
        d1 = parse_date("2026-03-15")
        self.assertEqual(d1.year, 2026)
        self.assertEqual(d1.month, 3)
        self.assertEqual(d1.day, 15)
        self.assertEqual(parse_date(d1), d1)

    def test_replacement_suggestions(self) -> None:
        spy_recs = get_replacement_suggestions("SPY")
        self.assertTrue(any(r["replacement_symbol"] == "VTI" for r in spy_recs))
        qqq_recs = get_replacement_suggestions("QQQ")
        self.assertTrue(any(r["replacement_symbol"] == "VUG" for r in qqq_recs))
        aapl_recs = get_replacement_suggestions("AAPL")
        self.assertTrue(any(r["replacement_symbol"] == "XLK" for r in aapl_recs))
        # Unknown fallback
        unknown_recs = get_replacement_suggestions("XYZCORP")
        self.assertTrue(any(r["replacement_symbol"] == "VTI" for r in unknown_recs))

    def test_wash_sale_subsequent_purchase(self) -> None:
        txs = [
            {"trade_id": "B1", "date": "2026-01-01", "symbol": "XYZ", "action": "BUY", "quantity": "100", "price": "100.00"},
            {"trade_id": "S1", "date": "2026-02-01", "symbol": "XYZ", "action": "SELL", "quantity": "100", "price": "80.00", "cost_basis_per_share": "100.00"},
            {"trade_id": "B2", "date": "2026-02-15", "symbol": "XYZ", "action": "BUY", "quantity": "100", "price": "85.00"},
        ]
        res = detect_wash_sales(txs)
        self.assertEqual(res["wash_sale_count"], 1)
        self.assertEqual(res["total_realized_loss"], "-2000.00")
        self.assertEqual(res["total_disallowed_loss"], "-2000.00")
        self.assertEqual(res["net_allowable_loss"], "0.00")
        wash = res["wash_sales"][0]
        self.assertEqual(wash["window_offset_days"], 14)
        self.assertEqual(wash["adjusted_replacement_basis_per_share"], "105.00")

    def test_wash_sale_prior_purchase(self) -> None:
        txs = [
            {"trade_id": "B1", "date": "2026-01-01", "symbol": "XYZ", "action": "BUY", "quantity": "50", "price": "100.00"},
            {"trade_id": "B2", "date": "2026-01-20", "symbol": "XYZ", "action": "BUY", "quantity": "50", "price": "90.00"},
            {"trade_id": "S1", "date": "2026-02-05", "symbol": "XYZ", "action": "SELL", "quantity": "50", "price": "80.00", "cost_basis_per_share": "100.00"},
        ]
        res = detect_wash_sales(txs)
        self.assertEqual(res["wash_sale_count"], 1)
        wash = res["wash_sales"][0]
        self.assertEqual(wash["window_offset_days"], -16)
        self.assertEqual(wash["disallowed_loss"], "-1000.00")
        self.assertEqual(wash["adjusted_replacement_basis_per_share"], "110.00")

    def test_wash_sale_partial_disallowance(self) -> None:
        txs = [
            {"trade_id": "B1", "date": "2026-01-01", "symbol": "XYZ", "action": "BUY", "quantity": "100", "price": "50.00"},
            {"trade_id": "S1", "date": "2026-02-01", "symbol": "XYZ", "action": "SELL", "quantity": "100", "price": "40.00", "cost_basis_per_share": "50.00"},
            {"trade_id": "B2", "date": "2026-02-10", "symbol": "XYZ", "action": "BUY", "quantity": "30", "price": "42.00"},
        ]
        res = detect_wash_sales(txs)
        self.assertEqual(res["wash_sale_count"], 1)
        self.assertEqual(res["clean_loss_count"], 1)
        self.assertEqual(res["total_realized_loss"], "-1000.00")
        self.assertEqual(res["total_disallowed_loss"], "-300.00")
        self.assertEqual(res["net_allowable_loss"], "-700.00")

    def test_clean_loss_outside_window(self) -> None:
        txs = [
            {"trade_id": "B1", "date": "2026-01-01", "symbol": "XYZ", "action": "BUY", "quantity": "100", "price": "50.00"},
            {"trade_id": "S1", "date": "2026-02-01", "symbol": "XYZ", "action": "SELL", "quantity": "100", "price": "40.00", "cost_basis_per_share": "50.00"},
            # Buy 35 days later (outside 30-day window)
            {"trade_id": "B2", "date": "2026-03-08", "symbol": "XYZ", "action": "BUY", "quantity": "100", "price": "45.00"},
        ]
        res = detect_wash_sales(txs)
        self.assertEqual(res["wash_sale_count"], 0)
        self.assertEqual(res["clean_loss_count"], 1)
        self.assertEqual(res["total_disallowed_loss"], "0.00")
        self.assertEqual(res["net_allowable_loss"], "-1000.00")

    def test_holding_period_under_30_days_no_self_match(self) -> None:
        """Shares held for under 30 days and sold at a loss must not match against their own buy lot."""
        txs = [
            {"trade_id": "B1", "date": "2026-01-15", "symbol": "XYZ", "action": "BUY", "quantity": "100", "price": "100.00"},
            {"trade_id": "S1", "date": "2026-01-25", "symbol": "XYZ", "action": "SELL", "quantity": "100", "price": "80.00", "cost_basis_per_share": "100.00"},
        ]
        res = detect_wash_sales(txs)
        self.assertEqual(res["wash_sale_count"], 0)
        self.assertEqual(res["clean_loss_count"], 1)
        self.assertEqual(res["total_realized_loss"], "-2000.00")
        self.assertEqual(res["total_disallowed_loss"], "0.00")
        self.assertEqual(res["net_allowable_loss"], "-2000.00")

    def test_day_trade_no_self_match(self) -> None:
        """Intraday buy and sell of the same lot must not trigger a wash sale against itself."""
        txs = [
            {"trade_id": "B1", "date": "2026-01-15", "symbol": "XYZ", "action": "BUY", "quantity": "100", "price": "100.00"},
            {"trade_id": "S1", "date": "2026-01-15", "symbol": "XYZ", "action": "SELL", "quantity": "100", "price": "80.00", "cost_basis_per_share": "100.00"},
        ]
        res = detect_wash_sales(txs)
        self.assertEqual(res["wash_sale_count"], 0)
        self.assertEqual(res["clean_loss_count"], 1)
        self.assertEqual(res["total_realized_loss"], "-2000.00")
        self.assertEqual(res["total_disallowed_loss"], "0.00")
        self.assertEqual(res["net_allowable_loss"], "-2000.00")

    def test_day_trade_with_replacement_buy(self) -> None:
        """Day trade followed by a second acquisition matches the second acquisition as a wash sale."""
        txs = [
            {"trade_id": "B1", "date": "2026-01-15", "symbol": "XYZ", "action": "BUY", "quantity": "100", "price": "100.00"},
            {"trade_id": "S1", "date": "2026-01-15", "symbol": "XYZ", "action": "SELL", "quantity": "100", "price": "80.00", "cost_basis_per_share": "100.00"},
            {"trade_id": "B2", "date": "2026-01-15", "symbol": "XYZ", "action": "BUY", "quantity": "100", "price": "85.00"},
        ]
        res = detect_wash_sales(txs)
        self.assertEqual(res["wash_sale_count"], 1)
        self.assertEqual(res["clean_loss_count"], 0)
        self.assertEqual(res["wash_sales"][0]["replacement_trade_id"], "B2")
        self.assertEqual(res["total_disallowed_loss"], "-2000.00")

    def test_wash_sale_fixture_complete(self) -> None:
        fixture = _load("synthetic_wash_sale.json")
        res = detect_wash_sales(fixture["transactions"])
        self.assertEqual(res["total_realized_loss"], "-13000.00")
        self.assertEqual(res["total_disallowed_loss"], "-5200.00")
        self.assertEqual(res["net_allowable_loss"], "-7800.00")
        self.assertEqual(res["wash_sale_count"], 3)
        self.assertIn("SPY", res["replacement_etf_suggestions"])
        self.assertIn("QQQ", res["replacement_etf_suggestions"])
        self.assertEqual(res["advisory_stamp"], ADVISORY_STAMP)

    def test_float_rejection_in_wash_sales(self) -> None:
        txs = [
            {"trade_id": "B1", "date": "2026-01-01", "symbol": "XYZ", "action": "BUY", "quantity": 100.5, "price": "50.00"},
        ]
        with self.assertRaises(FloatLedgerError):
            detect_wash_sales(txs)

    def test_wash_sale_cli_execution(self) -> None:
        f = io.StringIO()
        with redirect_stdout(f):
            rc = wash_sale_main(["--json"])
        self.assertEqual(rc, 0)
        output = json.loads(f.getvalue())
        self.assertEqual(output["wash_sale_count"], 3)

        # Dry run CLI
        f_dry = io.StringIO()
        with redirect_stdout(f_dry):
            rc_dry = wash_sale_main(["--dry-run"])
        self.assertEqual(rc_dry, 0)
        output_dry = json.loads(f_dry.getvalue())
        self.assertTrue(output_dry["dry_run"])

        # Symbol filter CLI
        f_sym = io.StringIO()
        with redirect_stdout(f_sym):
            rc_sym = wash_sale_main(["--symbol", "SPY", "--json"])
        self.assertEqual(rc_sym, 0)
        output_sym = json.loads(f_sym.getvalue())
        self.assertEqual(output_sym["wash_sale_count"], 1)

        # Invalid fixture error
        f_err = io.StringIO()
        with redirect_stderr(f_err):
            rc_err = wash_sale_main(["--fixture", "nonexistent_file_xyz.json"])
        self.assertEqual(rc_err, 2)


class TestDcfCalculator(unittest.TestCase):
    def test_capm_and_wacc(self) -> None:
        with ledger_context():
            ke = capm_cost_of_equity(Decimal("0.04"), Decimal("1.2"), Decimal("0.05"))
            self.assertEqual(ke, Decimal("0.1000"))
            w = wacc(
                cost_of_equity=ke,
                equity_weight=Decimal("0.70"),
                pre_tax_cost_of_debt=Decimal("0.06"),
                debt_weight=Decimal("0.30"),
                tax_rate=Decimal("0.25"),
            )
            # 0.70 * 0.10 + 0.30 * (0.06 * 0.75) = 0.07 + 0.30 * 0.045 = 0.07 + 0.0135 = 0.0835
            self.assertEqual(w, Decimal("0.0835"))

    def test_gordon_terminal(self) -> None:
        with ledger_context():
            tv = gordon_terminal(Decimal("100"), Decimal("0.02"), Decimal("0.08"))
            # 100 * 1.02 / 0.06 = 102 / 0.06 = 1700
            self.assertEqual(tv, Decimal("1700"))
            with self.assertRaises(ValueError):
                gordon_terminal(Decimal("100"), Decimal("0.08"), Decimal("0.08"))

    def test_dcf_cli(self) -> None:
        f = io.StringIO()
        with redirect_stdout(f):
            rc = dcf_main(["--json"])
        self.assertEqual(rc, 0)
        output = json.loads(f.getvalue())
        self.assertEqual(output["issuer"], "Northwind Analytics Inc")

        # Sensitivity CLI
        f_sens = io.StringIO()
        with redirect_stdout(f_sens):
            rc_sens = dcf_main(["--sensitivity", "--json"])
        self.assertEqual(rc_sens, 0)
        output_sens = json.loads(f_sens.getvalue())
        self.assertIn("sensitivity", output_sens)

        # Dry run CLI
        f_dry = io.StringIO()
        with redirect_stdout(f_dry):
            rc_dry = dcf_main(["--dry-run"])
        self.assertEqual(rc_dry, 0)
        output_dry = json.loads(f_dry.getvalue())
        self.assertTrue(output_dry["dry_run"])


class TestMonteCarloVar(unittest.TestCase):
    def test_var_calculations(self) -> None:
        with ledger_context():
            losses = [Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4"), Decimal("5")]
            var = historical_var(losses, Decimal("0.90"))
            self.assertEqual(var, Decimal("5"))
            cvar = historical_cvar(losses, Decimal("0.90"))
            self.assertEqual(cvar, Decimal("5"))

    def test_bootstrap_paths_determinism(self) -> None:
        with ledger_context():
            returns = [Decimal("0.01"), Decimal("-0.02"), Decimal("0.03")]
            p1 = bootstrap_paths(returns, seed=123, paths=20, horizon=2)
            p2 = bootstrap_paths(returns, seed=123, paths=20, horizon=2)
            self.assertEqual(p1, p2)

    def test_var_cli(self) -> None:
        f = io.StringIO()
        with redirect_stdout(f):
            rc = var_main(["--json"])
        self.assertEqual(rc, 0)
        output = json.loads(f.getvalue())
        self.assertEqual(output["method"], "historical")

        # Parametric CLI
        f_param = io.StringIO()
        with redirect_stdout(f_param):
            rc_param = var_main(["--method", "parametric", "--json"])
        self.assertEqual(rc_param, 0)
        output_param = json.loads(f_param.getvalue())
        self.assertEqual(output_param["method"], "parametric")

        # Dry run CLI
        f_dry = io.StringIO()
        with redirect_stdout(f_dry):
            rc_dry = var_main(["--dry-run"])
        self.assertEqual(rc_dry, 0)
        output_dry = json.loads(f_dry.getvalue())
        self.assertTrue(output_dry["dry_run"])


class TestPortfolioOptimizer(unittest.TestCase):
    def test_min_variance(self) -> None:
        cov = [
            [Decimal("0.02"), Decimal("0")],
            [Decimal("0"), Decimal("0.02")],
        ]
        with ledger_context():
            w = min_variance_weights(cov)
            self.assertEqual(w, [Decimal("0.5"), Decimal("0.5")])

    def test_portfolio_cli(self) -> None:
        f = io.StringIO()
        with redirect_stdout(f):
            rc = portfolio_main(["--json"])
        self.assertEqual(rc, 0)
        output = json.loads(f.getvalue())
        self.assertEqual(output["objective"], "min-variance")

        # Max Sharpe CLI
        f_sharpe = io.StringIO()
        with redirect_stdout(f_sharpe):
            rc_sharpe = portfolio_main(["--objective", "max-sharpe", "--json"])
        self.assertEqual(rc_sharpe, 0)
        output_sharpe = json.loads(f_sharpe.getvalue())
        self.assertEqual(output_sharpe["objective"], "max-sharpe")

        # Dry run CLI
        f_dry = io.StringIO()
        with redirect_stdout(f_dry):
            rc_dry = portfolio_main(["--dry-run"])
        self.assertEqual(rc_dry, 0)
        output_dry = json.loads(f_dry.getvalue())
        self.assertTrue(output_dry["dry_run"])


class TestEdgarIngest(unittest.TestCase):
    def test_edgar_parsing(self) -> None:
        self.assertEqual(pad_cik("9876"), "0000009876")
        payload = _load("synthetic_companyfacts.json")
        res = ingest_payload(payload, ["Assets", "Liabilities"])
        self.assertEqual(res["cik"], "0001234567")
        self.assertIn("Assets", res["facts"])

    def test_edgar_cli(self) -> None:
        f = io.StringIO()
        with redirect_stdout(f):
            rc = edgar_main(["--json"])
        self.assertEqual(rc, 0)
        output = json.loads(f.getvalue())
        self.assertEqual(output["cik"], "0001234567")

        # Dry run CLI
        f_dry = io.StringIO()
        with redirect_stdout(f_dry):
            rc_dry = edgar_main(["--dry-run"])
        self.assertEqual(rc_dry, 0)
        output_dry = json.loads(f_dry.getvalue())
        self.assertTrue(output_dry["dry_run"])


if __name__ == "__main__":
    unittest.main()
