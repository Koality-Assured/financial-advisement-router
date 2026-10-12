import os
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from financial.portfolio_optimizer import (
    solve_qp_long_only,
)


class TestPortfolioOptimizerKKT(unittest.TestCase):
    def test_solve_qp_long_only_min_variance(self):
        Q = [
            [Decimal("0.01"), Decimal(0), Decimal(0)],
            [Decimal(0), Decimal("0.04"), Decimal(0)],
            [Decimal(0), Decimal(0), Decimal("0.16")],
        ]
        c = [Decimal(0)] * 3
        A = [[Decimal(1), Decimal(1), Decimal(1)]]
        b = [Decimal(1)]

        x = solve_qp_long_only(Q, c, A, b)
        self.assertAlmostEqual(float(x[0]), 0.7619, places=4)
        self.assertAlmostEqual(float(x[1]), 0.1905, places=4)
        self.assertAlmostEqual(float(x[2]), 0.0476, places=4)


if __name__ == "__main__":
    unittest.main()
