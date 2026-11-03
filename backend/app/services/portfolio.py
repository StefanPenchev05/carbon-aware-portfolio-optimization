"""Pure convex mathematics. No HTTP, database, calendar or data acquisition logic."""

import cvxpy as cp
import numpy as np
from scipy.stats import rankdata

TOLERANCE = 1e-7


class PortfolioError(ValueError):
    def __init__(self, message, status="invalid_inputs"):
        super().__init__(message)
        self.status = status


def carbon_scores(values):
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all() or np.any(values < 0):
        raise PortfolioError("Every security needs a finite nonnegative comparable carbon measurement")
    return (rankdata(values, method="average") - 1) / (len(values) - 1)


def covariance_psd(matrix, n):
    matrix = np.asarray(matrix, dtype=float)
    if matrix.shape != (n, n) or not np.isfinite(matrix).all():
        raise PortfolioError("Covariance dimensions or finite-value checks failed")
    scale = max(float(np.max(np.abs(matrix))), 1e-12)
    if not np.allclose(matrix, matrix.T, rtol=0, atol=1e-10 * scale):
        raise PortfolioError("Covariance matrix is not symmetric")
    matrix = (matrix + matrix.T) / 2
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    if eigenvalues.min() < -1e-10 * scale:
        raise PortfolioError("Materially indefinite covariance matrix; refusing automatic repair")
    repaired = bool(eigenvalues.min() < 0)
    if repaired:
        matrix = (eigenvectors * np.maximum(eigenvalues, 0)) @ eigenvectors.T
    return matrix, "roundoff-only eigenvalue clipping" if repaired else "none"


def estimate(returns, shrinkage=0.05):
    returns = np.asarray(returns, dtype=float)
    if returns.ndim != 2 or returns.shape[1] < 2 or returns.shape[0] < max(2, returns.shape[1] + 1):
        raise PortfolioError("Need a complete observations × securities matrix with T >= N+1")
    if not np.isfinite(returns).all() or np.any(returns <= -1) or not 0 <= shrinkage <= 1:
        raise PortfolioError("Invalid returns or covariance-shrinkage parameter")
    mu = returns.mean(axis=0) * 252
    sample = np.cov(returns, rowvar=False, ddof=1) * 252
    covariance = (1 - shrinkage) * sample + shrinkage * np.diag(np.diag(sample))
    covariance, repair = covariance_psd(covariance, len(mu))
    if not np.isfinite(mu).all():
        raise PortfolioError("Nonfinite expected returns")
    return mu, covariance, repair


def candidates(ids, mu, config):
    if len(ids) != len(set(ids)) or len(ids) != len(mu) or not np.isfinite(mu).all():
        raise PortfolioError("Invalid securities/expected-return vector")
    if config.selection == "manual":
        longs, shorts = config.long_ids, config.short_ids
        method = "explicit disjoint candidate groups"
    else:
        order = sorted(range(len(ids)), key=lambda i: (-mu[i], ids[i]))
        split = (len(ids) + 1) // 2
        longs, shorts = [ids[i] for i in order[:split]], [ids[i] for i in order[split:]]
        method = "descending estimation-window sample mean; ties by ascending company ID; upper half long"
    if set(longs) & set(shorts) or set(longs) | set(shorts) != set(ids):
        raise PortfolioError("Candidate groups must be disjoint and partition the selected universe")
    if min(len(longs), len(shorts)) < config.min_candidates:
        raise PortfolioError(f"Need at least {config.min_candidates} candidates in each sleeve", "infeasible")
    if (
        len(longs) * config.max_weight < config.long_gross - 1e-12
        or len(shorts) * config.max_weight < config.short_gross - 1e-12
    ):
        raise PortfolioError("Position cap × candidate count cannot fund a requested sleeve", "infeasible")
    return [ids.index(i) for i in longs], [ids.index(i) for i in shorts], method


def solve(mu, covariance, scores, ids, names, long_indices, short_indices, config, penalty):
    mu, scores = np.asarray(mu, dtype=float), np.asarray(scores, dtype=float)
    n = len(ids)
    if (
        mu.shape != (n,)
        or scores.shape != (n,)
        or len(names) != n
        or n < 2
        or len(set(ids)) != n
        or not np.isfinite(mu).all()
        or not np.isfinite(scores).all()
        or np.any(scores < 0)
        or np.any(scores > 1)
        or not np.isfinite(penalty)
        or penalty < 0
    ):
        raise PortfolioError("Invalid optimizer dimensions, expected returns, scores or penalty")
    longs, shorts = list(long_indices), list(short_indices)
    if len(set(longs + shorts)) != n or set(longs + shorts) != set(range(n)) or not longs or not shorts:
        raise PortfolioError("Optimizer sleeves must partition all securities exactly once")
    if (
        min(len(longs), len(shorts)) < config.min_candidates
        or len(longs) * config.max_weight < config.long_gross - 1e-12
        or len(shorts) * config.max_weight < config.short_gross - 1e-12
    ):
        raise PortfolioError("Infeasible sleeve sizes/position caps", "infeasible")
    covariance, _ = covariance_psd(covariance, n)
    w = cp.Variable(n)
    constraints = [
        w[longs] >= 0,
        w[longs] <= config.max_weight,
        w[shorts] <= 0,
        w[shorts] >= -config.max_weight,
        cp.sum(w[longs]) == config.long_gross,
        cp.sum(w[shorts]) == -config.short_gross,
    ]
    objective = cp.Maximize(
        mu @ w - config.risk_aversion * cp.quad_form(w, cp.psd_wrap(covariance)) - penalty * (scores[longs] @ w[longs])
    )
    problem = cp.Problem(objective, constraints)
    if not problem.is_dcp():
        raise PortfolioError("Optimization model failed DCP validation")
    try:
        problem.solve(
            solver="CLARABEL", tol_gap_abs=1e-10, tol_gap_rel=1e-10, tol_feas=1e-10, max_iter=300, warm_start=False
        )
    except cp.error.SolverError as exc:
        raise PortfolioError(f"Clarabel failed: {exc}", "solver_error") from exc
    if problem.status != cp.OPTIMAL or w.value is None:
        raise PortfolioError(f"Solver returned {problem.status}; no portfolio accepted", "solver_error")
    weights = np.asarray(w.value).reshape(-1)
    if weights.shape != (n,) or not np.isfinite(weights).all():
        raise PortfolioError("Solver returned invalid weights", "solver_error")
    violation = max(
        0.0,
        -weights[longs].min(),
        weights[shorts].max(),
        np.abs(weights).max() - config.max_weight,
        abs(weights[longs].sum() - config.long_gross),
        abs(weights[shorts].sum() + config.short_gross),
        abs(np.abs(weights).sum() - config.long_gross - config.short_gross),
        abs(weights.sum() - config.long_gross + config.short_gross),
    )
    if violation > TOLERANCE:
        raise PortfolioError("Solver weights failed independent constraint verification", "solver_error")
    expected = float(mu @ weights)
    variance = float(weights @ covariance @ weights)
    carbon = float(scores[longs] @ weights[longs])
    if variance < -TOLERANCE or carbon < -TOLERANCE:
        raise PortfolioError("Invalid variance/carbon exposure returned", "solver_error")
    variance, carbon = max(0.0, variance), max(0.0, carbon)
    result = dict(
        carbon_penalty=float(penalty),
        weights=weights.tolist(),
        expected_return_annual=expected,
        variance_annual=variance,
        volatility_annual=float(np.sqrt(variance)),
        carbon_exposure_score=carbon,
        long_exposure=float(weights[longs].sum()),
        short_exposure=float(weights[shorts].sum()),
        gross_exposure=float(np.abs(weights).sum()),
        net_exposure=float(weights.sum()),
        objective_value=expected - config.risk_aversion * variance - penalty * carbon,
        solver="CLARABEL",
        solver_status=problem.status,
        max_constraint_violation=float(violation),
    )
    if not all(np.isfinite(v) for k, v in result.items() if isinstance(v, float)):
        raise PortfolioError("Nonfinite optimization summary", "solver_error")
    return result


def compare_results(baseline, aware, ids):
    differences = np.array(aware["weights"]) - np.array(baseline["weights"])
    return dict(
        **{
            k: aware[k] - baseline[k]
            for k in (
                "expected_return_annual",
                "volatility_annual",
                "carbon_exposure_score",
                "long_exposure",
                "short_exposure",
            )
        },
        weights=dict(zip(ids, differences.tolist(), strict=True)),
        composition_l1=float(np.abs(differences).sum()),
    )
