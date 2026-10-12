import re
from pathlib import Path

file_path = Path("scripts/financial/portfolio_optimizer.py")
content = file_path.read_text(encoding="utf-8")

content = content.replace("import json", "import itertools\nimport json")
content = re.sub(r'def _clip_long_only\(weights: list\[Decimal\]\) -> list\[Decimal\]:.*?return _normalize\(clipped\)\n\n\n', '', content, flags=re.DOTALL)

qp_solver_code = '''def _solve_qp_subset(Q: list[list[Decimal]], c: list[Decimal], A: list[list[Decimal]], b: list[Decimal], F: list[int]) -> tuple[list[Decimal] | None, list[Decimal] | None]:
    n_F = len(F)
    m = len(b)
    size = n_F + m
    mat = [[Decimal("0")] * size for _ in range(size)]
    for i in range(n_F):
        for j in range(n_F):
            mat[i][j] = Q[F[i]][F[j]]
    for i in range(n_F):
        for j in range(m):
            mat[i][n_F + j] = A[j][F[i]]
            mat[n_F + j][i] = A[j][F[i]]
    rhs = []
    for i in range(n_F):
        rhs.append(-c[F[i]])
    for j in range(m):
        rhs.append(b[j])
    try:
        inv_mat = invert(mat)
    except ValueError:
        return None, None
    sol = matvec(inv_mat, rhs)
    x_F = sol[:n_F]
    lam = sol[n_F:]
    x = [Decimal("0")] * len(Q)
    for i in range(n_F):
        x[F[i]] = x_F[i]
    return x, lam


def _check_kkt(Q: list[list[Decimal]], c: list[Decimal], A: list[list[Decimal]], b: list[Decimal], F: list[int]) -> tuple[list[Decimal], Decimal] | None:
    x, lam = _solve_qp_subset(Q, c, A, b, F)
    if x is None or lam is None:
        return None
    for i in F:
        if x[i] < Decimal("-1e-10"):
            return None
    nu = [Decimal("0")] * len(Q)
    for i in range(len(Q)):
        val = c[i]
        for j in range(len(Q)):
            val += Q[i][j] * x[j]
        for j in range(len(b)):
            val += A[j][i] * lam[j]
        nu[i] = val
    for i in range(len(Q)):
        if i not in F:
            if nu[i] < Decimal("-1e-10"):
                return None
    obj = sum((Decimal("0.5") * x[i] * sum((Q[i][j] * x[j] for j in range(len(Q))), Decimal("0")) + c[i] * x[i] for i in range(len(Q))), Decimal("0"))
    return x, obj


def solve_qp_long_only(Q: list[list[Decimal]], c: list[Decimal], A: list[list[Decimal]], b: list[Decimal]) -> list[Decimal]:
    N = len(Q)
    best_x = None
    best_obj = None
    for r in range(N + 1):
        for F_tuple in itertools.combinations(range(N), r):
            res = _check_kkt(Q, c, A, b, list(F_tuple))
            if res is not None:
                x, obj = res
                if best_obj is None or obj < best_obj:
                    best_obj = obj
                    best_x = x
    if best_x is None:
        raise ValueError("No feasible solution found for QP")
    return best_x


'''

min_var_orig = '''def min_variance_weights(
    covariance: list[list[Decimal]], *, long_only: bool = True
) -> list[Decimal]:
    inv = invert(covariance)
    raw = matvec(inv, _ones(len(covariance)))
    weights = _normalize(raw)
    return _clip_long_only(weights) if long_only else weights'''

min_var_new = '''def min_variance_weights(
    covariance: list[list[Decimal]], *, long_only: bool = True
) -> list[Decimal]:
    if not long_only:
        inv = invert(covariance)
        raw = matvec(inv, _ones(len(covariance)))
        return _normalize(raw)
    n = len(covariance)
    c = [Decimal("0")] * n
    A = [[Decimal("1")] * n]
    b = [Decimal("1")]
    return solve_qp_long_only(covariance, c, A, b)'''

max_sharpe_orig = '''def max_sharpe_weights(
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
    return _clip_long_only(weights) if long_only else weights'''

max_sharpe_new = '''def max_sharpe_weights(
    covariance: list[list[Decimal]],
    expected_returns: list[Decimal],
    risk_free: Decimal,
    *,
    long_only: bool = True,
) -> list[Decimal]:
    excess = [mu - risk_free for mu in expected_returns]
    if not long_only:
        inv = invert(covariance)
        raw = matvec(inv, excess)
        return _normalize(raw)
    n = len(covariance)
    c = [Decimal("0")] * n
    if all(e <= 0 for e in excess):
        raise ValueError("No positive excess return available")
    A = [excess]
    b = [Decimal("1")]
    x = solve_qp_long_only(covariance, c, A, b)
    return _normalize(x)'''

target_return_orig = '''def target_return_weights(
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
    return _clip_long_only(weights) if long_only else weights'''

target_return_new = '''def target_return_weights(
    covariance: list[list[Decimal]],
    expected_returns: list[Decimal],
    target: Decimal,
    *,
    long_only: bool = True,
) -> list[Decimal]:
    """Two-constraint analytic weights, then optional long-only active set solver."""
    n = len(expected_returns)
    if not long_only:
        inv = invert(covariance)
        ones = _ones(n)
        a = decimal_sum(matvec(inv, ones))
        b_val = decimal_sum(matvec(inv, expected_returns))
        c_vec = matvec(inv, expected_returns)
        c_val = sum((expected_returns[i] * c_vec[i] for i in range(n)), Decimal("0"))
        delta = a * c_val - b_val * b_val
        if delta == 0:
            raise ValueError("target-return system is singular")
        lam = (c_val - b_val * target) / delta
        gam = (a * target - b_val) / delta
        raw = [
            lam * matvec(inv, ones)[i] + gam * c_vec[i] for i in range(n)
        ]
        return _normalize(raw)
        
    c_vec2 = [Decimal("0")] * n
    A = [[Decimal("1")] * n, expected_returns]
    b_vec = [Decimal("1"), target]
    return solve_qp_long_only(covariance, c_vec2, A, b_vec)'''

content = content.replace(min_var_orig, qp_solver_code + min_var_new)
content = content.replace(max_sharpe_orig, max_sharpe_new)
content = content.replace(target_return_orig, target_return_new)

file_path.write_text(content, encoding="utf-8")
