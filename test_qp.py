import sys
sys.path.insert(0, "scripts/financial")
from decimal import Decimal
from _decimal_linalg import invert, matvec
import itertools

def _solve_qp_subset(Q, c, A, b, F):
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

def _check_kkt(Q, c, A, b, F):
    x, lam = _solve_qp_subset(Q, c, A, b, F)
    if x is None:
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
    obj = sum(Decimal("0.5") * x[i] * sum(Q[i][j] * x[j] for j in range(len(Q))) + c[i] * x[i] for i in range(len(Q)))
    return x, obj

def solve_qp_long_only(Q, c, A, b):
    N = len(Q)
    best_x = None
    best_obj = None
    for r in range(N + 1):
        for F in itertools.combinations(range(N), r):
            res = _check_kkt(Q, c, A, b, list(F))
            if res is not None:
                x, obj = res
                if best_obj is None or obj < best_obj:
                    best_obj = obj
                    best_x = x
    if best_x is None:
        raise ValueError("No feasible solution found for QP")
    return best_x

Q = [[Decimal('0.01'), Decimal('0'), Decimal('0')], [Decimal('0'), Decimal('0.04'), Decimal('0')], [Decimal('0'), Decimal('0'), Decimal('0.16')]]
c = [Decimal('0')]*3
A = [[Decimal('1'), Decimal('1'), Decimal('1')]]
b = [Decimal('1')]
print("min var:", solve_qp_long_only(Q, c, A, b))

A2 = [[Decimal('1'), Decimal('1'), Decimal('1')], [Decimal('0.04'), Decimal('0.09'), Decimal('0.07')]]
b2 = [Decimal('1'), Decimal('0.085')]
print("target return:", solve_qp_long_only(Q, c, A2, b2))
