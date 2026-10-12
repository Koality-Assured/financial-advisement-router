import os
import random
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from financial.portfolio_optimizer import (
    MAX_LONG_ONLY_ASSETS,
    max_sharpe_weights,
    min_variance_weights,
    portfolio_variance,
    solve_qp_long_only,
    target_return_weights,
)

TOL = Decimal("1e-9")


def _d(rows):
    return [[Decimal(str(v)) for v in row] for row in rows]


def _clipped_min_variance(cov):
    """The old (incorrect) approach: unconstrained solve, clip negatives, renormalise."""
    raw = min_variance_weights(cov, long_only=False)
    clipped = [max(w, Decimal(0)) for w in raw]
    total = sum(clipped, Decimal(0))
    return [w / total for w in clipped]


def _assert_min_variance_kkt(testcase, cov, x):
    """Stationarity, primal and dual feasibility for min x'Sx s.t. sum(x)=1, x>=0."""
    n = len(cov)
    testcase.assertLess(abs(sum(x, Decimal(0)) - 1), TOL)
    for w in x:
        testcase.assertGreaterEqual(w, -TOL)
    grad = [sum((cov[i][j] * x[j] for j in range(n)), Decimal(0)) for i in range(n)]
    support = [i for i in range(n) if x[i] > TOL]
    testcase.assertTrue(support)
    lam = grad[support[0]]
    for i in support:  # stationarity on the support
        testcase.assertLess(abs(grad[i] - lam), TOL)
    for i in range(n):  # dual feasibility off the support
        if i not in support:
            testcase.assertGreaterEqual(grad[i] - lam, -TOL)


class TestPortfolioOptimizerKKT(unittest.TestCase):
    def test_solve_qp_long_only_min_variance_diagonal(self):
        Q = _d([[0.01, 0, 0], [0, 0.04, 0], [0, 0, 0.16]])
        x = solve_qp_long_only(Q, [Decimal(0)] * 3, [[Decimal(1)] * 3], [Decimal(1)])
        self.assertAlmostEqual(float(x[0]), 0.7619, places=4)
        self.assertAlmostEqual(float(x[1]), 0.1905, places=4)
        self.assertAlmostEqual(float(x[2]), 0.0476, places=4)

    def test_constrained_optimum_beats_clipping_when_short_is_optimal(self):
        # Asset 4 is positively correlated with asset 1 and negatively with 3:
        # the unconstrained optimum shorts it, and clip-and-renormalise is
        # strictly worse than the true long-only optimum (variance gap ~0.087).
        cov = _d(
            [
                [0.9, -0.438, -0.79, 1.102],
                [-0.438, 1.228, 1.049, -0.136],
                [-0.79, 1.049, 1.625, -0.617],
                [1.102, -0.136, -0.617, 1.708],
            ]
        )
        unconstrained = min_variance_weights(cov, long_only=False)
        self.assertLess(min(unconstrained), 0, "fixture must force a short position")

        x = min_variance_weights(cov, long_only=True)
        _assert_min_variance_kkt(self, cov, x)
        clipped = _clipped_min_variance(cov)
        gap = portfolio_variance(clipped, cov) - portfolio_variance(x, cov)
        self.assertGreater(gap, Decimal("0.05"))

    def test_random_covariances_satisfy_kkt_and_beat_sampled_portfolios(self):
        rng = random.Random(20261012)
        for n in (3, 4, 5):
            for _ in range(8):
                b = [[rng.uniform(-1, 1) for _ in range(n)] for _ in range(n)]
                cov = _d(
                    [
                        [
                            round(sum(b[i][k] * b[j][k] for k in range(n)) + (0.05 if i == j else 0), 6)
                            for j in range(n)
                        ]
                        for i in range(n)
                    ]
                )
                x = min_variance_weights(cov, long_only=True)
                _assert_min_variance_kkt(self, cov, x)
                best = portfolio_variance(x, cov)
                for _ in range(200):
                    raw = [Decimal(str(rng.random())) ** 3 for _ in range(n)]
                    s = sum(raw, Decimal(0))
                    cand = [r / s for r in raw]
                    self.assertLessEqual(best, portfolio_variance(cand, cov) + TOL)

    def test_target_return_long_only_respects_constraints(self):
        cov = _d([[0.04, 0.01, 0.0], [0.01, 0.09, 0.02], [0.0, 0.02, 0.16]])
        mu = [Decimal("0.05"), Decimal("0.08"), Decimal("0.12")]
        w = target_return_weights(cov, mu, Decimal("0.09"), long_only=True)
        self.assertLess(abs(sum(w, Decimal(0)) - 1), TOL)
        self.assertLess(abs(sum((a * b for a, b in zip(w, mu)), Decimal(0)) - Decimal("0.09")), TOL)
        self.assertTrue(all(v >= -TOL for v in w))

    def test_max_sharpe_long_only_is_a_fully_invested_long_portfolio(self):
        cov = _d([[0.04, 0.01, 0.0], [0.01, 0.09, 0.02], [0.0, 0.02, 0.16]])
        mu = [Decimal("0.05"), Decimal("0.08"), Decimal("0.12")]
        w = max_sharpe_weights(cov, mu, Decimal("0.01"), long_only=True)
        self.assertLess(abs(sum(w, Decimal(0)) - 1), TOL)
        self.assertTrue(all(v >= -TOL for v in w))

    def test_unreachable_target_return_is_rejected(self):
        cov = _d([[0.04, 0.0], [0.0, 0.09]])
        mu = [Decimal("0.05"), Decimal("0.08")]
        with self.assertRaises(ValueError):
            target_return_weights(cov, mu, Decimal("0.50"), long_only=True)

    def test_universe_larger_than_exact_solver_limit_is_rejected(self):
        n = MAX_LONG_ONLY_ASSETS + 1
        cov = [[Decimal(1) if i == j else Decimal(0) for j in range(n)] for i in range(n)]
        with self.assertRaises(ValueError):
            min_variance_weights(cov, long_only=True)


if __name__ == "__main__":
    unittest.main()
