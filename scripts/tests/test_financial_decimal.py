"""Deterministic Decimal tests for financial scripts (zero binary-float drift).

tags: [tests, financial, decimal]
routing_hints: [decimal, dcf, portfolio, var, edgar]
"""

from __future__ import annotations

import json
import sys
import unittest
from decimal import Decimal, FloatOperation, localcontext
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
_FIN = _SCRIPTS / "financial"
sys.path.insert(0, str(_FIN))

from _ledger import (  # noqa: E402
    ADVISORY_STAMP,
    FloatLedgerError,
    ledger_context,
    quantize_weight,
    to_decimal,
)
from monte_carlo_var import bootstrap_paths, run_fixture  # noqa: E402
from dcf_calculator import value_from_fixture  # noqa: E402
from edgar_ingest import ingest_payload, pad_cik  # noqa: E402
from portfolio_optimizer import (  # noqa: E402
    min_variance_weights,
    optimize_from_fixture,
    portfolio_variance,
)


FIXTURES = _FIN / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class TestDecimalLedger(unittest.TestCase):
    def test_tenth_identity_is_exact(self) -> None:
        with ledger_context():
            total = Decimal("0.1") + Decimal("0.1") + Decimal("0.1") - Decimal("0.3")
        self.assertEqual(total, Decimal("0"))

    def test_float_construct_rejected(self) -> None:
        with self.assertRaises(FloatLedgerError):
            to_decimal(0.1, field="cash")  # type: ignore[arg-type]

    def test_float_operation_trap(self) -> None:
        ctx = ledger_context()
        with ctx:
            with self.assertRaises(FloatOperation):
                Decimal(0.1)


class TestStatements(unittest.TestCase):
    def test_balance_sheet_identity(self) -> None:
        sheet = _load("synthetic_balance_sheet.json")
        with ledger_context():
            assets = to_decimal(sheet["assets"]["total"], field="assets")
            liab = to_decimal(sheet["liabilities"]["total"], field="liab")
            equity = to_decimal(sheet["equity"]["total"], field="equity")
            cash = to_decimal(sheet["assets"]["cash"], field="cash")
            recv = to_decimal(sheet["assets"]["receivables"], field="recv")
            inv = to_decimal(sheet["assets"]["inventory"], field="inv")
            ppe = to_decimal(sheet["assets"]["ppe_net"], field="ppe")
        self.assertEqual(assets, liab + equity)
        self.assertEqual(assets, cash + recv + inv + ppe)
        self.assertIn("NOT INDIVIDUAL INVESTMENT ADVICE", sheet["advisory_stamp"])

    def test_cash_rollforward(self) -> None:
        cf = _load("synthetic_cash_flow.json")
        with ledger_context():
            start = to_decimal(cf["beginning_cash"], field="begin")
            end = to_decimal(cf["ending_cash"], field="end")
            rolled = (
                start
                + to_decimal(cf["cfo"], field="cfo")
                + to_decimal(cf["cfi"], field="cfi")
                + to_decimal(cf["cff"], field="cff")
            )
        self.assertEqual(end, rolled)


class TestPortfolio(unittest.TestCase):
    def test_diagonal_min_variance_closed_form(self) -> None:
        cov = [
            [Decimal("0.01"), Decimal("0"), Decimal("0")],
            [Decimal("0"), Decimal("0.04"), Decimal("0")],
            [Decimal("0"), Decimal("0"), Decimal("0.16")],
        ]
        with ledger_context():
            weights = min_variance_weights(cov, long_only=True)
            expected = [
                Decimal("16") / Decimal("21"),
                Decimal("4") / Decimal("21"),
                Decimal("1") / Decimal("21"),
            ]
            for got, want in zip(weights, expected, strict=True):
                self.assertEqual(quantize_weight(got), quantize_weight(want))
            self.assertEqual(sum(weights, Decimal("0")), Decimal("1"))
            scaled = [quantize_weight(weights[i] * cov[i][i]) for i in range(3)]
            self.assertEqual(scaled[0], scaled[1])
            self.assertEqual(scaled[1], scaled[2])

    def test_optimizer_replay_bit_identical(self) -> None:
        fixture = _load("synthetic_portfolio.json")
        first = optimize_from_fixture(fixture, objective="min-variance")
        second = optimize_from_fixture(fixture, objective="min-variance")
        self.assertEqual(first, second)
        self.assertEqual(first["advisory_stamp"], ADVISORY_STAMP)
        self.assertFalse(first["licensed_advice"])

    def test_two_asset_closed_form(self) -> None:
        cov = [
            [Decimal("0.04"), Decimal("0.01")],
            [Decimal("0.01"), Decimal("0.09")],
        ]
        with ledger_context():
            weights = min_variance_weights(cov, long_only=False)
            w0 = Decimal("8") / Decimal("11")
            w1 = Decimal("3") / Decimal("11")
            self.assertEqual(quantize_weight(weights[0]), quantize_weight(w0))
            self.assertEqual(quantize_weight(weights[1]), quantize_weight(w1))
            var = portfolio_variance(weights, cov)
            self.assertGreater(var, Decimal("0"))


class TestDcf(unittest.TestCase):
    def test_single_stage_exact(self) -> None:
        fixture = {
            "issuer": "Exact Co",
            "capm": {"risk_free": "0.10", "beta": "0", "equity_risk_premium": "0"},
            "capital_structure": {
                "equity_weight": "1",
                "debt_weight": "0",
                "pre_tax_cost_of_debt": "0",
                "tax_rate": "0",
            },
            "fcf": ["10"],
            "terminal_growth": "0",
            "long_run_gdp_growth_cap": "0.03",
            "net_debt": "0",
            "shares_outstanding": "1",
        }
        result = value_from_fixture(fixture)
        self.assertEqual(result["wacc"], "0.10000000")
        self.assertEqual(result["enterprise_value"], "100.00")
        self.assertEqual(result["equity_value"], "100.00")
        self.assertEqual(result["advisory_stamp"], ADVISORY_STAMP)

    def test_dcf_replay_bit_identical(self) -> None:
        fixture = _load("synthetic_dcf.json")
        self.assertEqual(value_from_fixture(fixture), value_from_fixture(fixture))


class TestVar(unittest.TestCase):
    def test_bootstrap_seed_replay(self) -> None:
        fixture = _load("synthetic_returns.json")
        a = run_fixture(
            fixture, method="bootstrap", confidence=Decimal("0.95"), seed=42, paths=200, horizon=1
        )
        b = run_fixture(
            fixture, method="bootstrap", confidence=Decimal("0.95"), seed=42, paths=200, horizon=1
        )
        self.assertEqual(a, b)
        returns = [Decimal(x) for x in fixture["returns"]]
        paths_a = bootstrap_paths(returns, seed=42, paths=50, horizon=3)
        paths_b = bootstrap_paths(returns, seed=42, paths=50, horizon=3)
        paths_c = bootstrap_paths(returns, seed=43, paths=50, horizon=3)
        self.assertEqual(paths_a, paths_b)
        self.assertNotEqual(paths_a, paths_c)
        self.assertIn("hypothetical", a["finra_2214_legend"].lower())

    def test_historical_known_quantile(self) -> None:
        fixture = {"returns": ["0.10", "0.00", "-0.10", "0.02", "-0.04"]}
        result = run_fixture(
            fixture, method="historical", confidence=Decimal("0.95"), seed=1, paths=1, horizon=1
        )
        self.assertEqual(result["advisory_stamp"], ADVISORY_STAMP)
        self.assertTrue(Decimal(result["cvar"]) >= Decimal(result["var"]))


class TestEdgar(unittest.TestCase):
    def test_pad_and_extract(self) -> None:
        self.assertEqual(pad_cik("1234567"), "0001234567")
        payload = _load("synthetic_companyfacts.json")
        result = ingest_payload(
            payload, ["Assets", "Liabilities", "StockholdersEquity"]
        )
        assets = Decimal(result["facts"]["Assets"]["val"])
        liab = Decimal(result["facts"]["Liabilities"]["val"])
        equity = Decimal(result["facts"]["StockholdersEquity"]["val"])
        self.assertEqual(assets, liab + equity)
        self.assertEqual(result["advisory_stamp"], ADVISORY_STAMP)


if __name__ == "__main__":
    unittest.main()
