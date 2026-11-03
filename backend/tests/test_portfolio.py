"""Mathematical reference cases and explicitly artificial portfolio integration tests."""

import copy
import json
from pathlib import Path

import cvxpy as cp
import numpy as np
import pytest
from pydantic import ValidationError

from app.schemas.portfolio import PortfolioRequest
from app.services.portfolio import (
    PortfolioError,
    candidates,
    carbon_scores,
    covariance_psd,
    estimate,
    solve,
)
from app.services.portfolio_data import prepare
from app.services.portfolio_experiment import execute
from app.services.synthetic_portfolio import dataset


def config(**kwargs):
    return PortfolioRequest(data_mode="synthetic", **kwargs)


def reference(penalty=0):
    c = config(risk_aversion=1, max_weight=0.5)
    return solve([0.2, 0, 0, 0], np.eye(4), [1, 0, 1, 0], [1, 2, 3, 4], ["SYNTHETIC"] * 4, [0, 1], [2, 3], c, penalty)


def test_analytic_reference_solution_and_units():
    # Let x=w1, w2=.5-x: derivative .2-2x+2(.5-x)=0 => x=.3.
    r = reference()
    assert r["weights"] == pytest.approx([0.3, 0.2, -0.25, -0.25], abs=1e-7)
    assert r["expected_return_annual"] == pytest.approx(0.06)
    assert r["variance_annual"] == pytest.approx(0.255)
    assert r["volatility_annual"] == pytest.approx(np.sqrt(0.255))
    assert r["objective_value"] == pytest.approx(0.06 - 0.255)
    assert r["gross_exposure"] == pytest.approx(1)
    assert r["net_exposure"] == pytest.approx(0, abs=1e-9)
    assert r["long_exposure"] == pytest.approx(0.5)
    assert r["short_exposure"] == pytest.approx(-0.5)
    assert max(abs(w) for w in r["weights"]) <= 0.5 + 1e-7


def test_penalty_direction_and_short_emissions_never_cancel():
    baseline, aware = reference(), reference(0.4)
    assert aware["weights"] == pytest.approx([0.2, 0.3, -0.25, -0.25], abs=1e-7)
    assert baseline["carbon_exposure_score"] == pytest.approx(0.3)  # not .3-.25!
    assert aware["carbon_exposure_score"] == pytest.approx(0.2)
    assert aware["objective_value"] == pytest.approx(0.04 - (0.04 + 0.09 + 0.0625 + 0.0625) - 0.4 * 0.2)


def test_estimation_independent_centered_crossproducts():
    returns = np.array([[0.01, 0.02], [-0.01, 0], [0.02, -0.01], [0, 0.01]])
    mu, covariance, _ = estimate(returns, shrinkage=0)
    expected = np.array([0.005, 0.005])
    centered = returns - expected
    assert mu == pytest.approx(expected * 252)
    assert covariance == pytest.approx(sum(np.outer(r, r) for r in centered) / 3 * 252)
    _, shrunk, _ = estimate(returns, shrinkage=1)
    assert shrunk == pytest.approx(np.diag(np.diag(covariance)))


@pytest.mark.parametrize("matrix", [np.eye(3), [[1, 2], [0, 1]], [[1, 2], [2, 1]], [[float("nan"), 0], [0, 1]]])
def test_invalid_covariance_rejected(matrix):
    with pytest.raises(PortfolioError):
        covariance_psd(matrix, 2)


def test_only_roundoff_indefiniteness_repaired():
    repaired, note = covariance_psd(np.diag([1, -1e-12]), 2)
    assert np.linalg.eigvalsh(repaired).min() >= 0
    assert note == "roundoff-only eigenvalue clipping"


@pytest.mark.parametrize("returns", [np.ones((2, 4)), [[0.01, float("nan")]] * 4, [[0.01, -1]] * 4])
def test_invalid_or_short_return_matrix_rejected(returns):
    with pytest.raises(PortfolioError):
        estimate(returns)


def test_normalization_ties_and_nonnegative_measurements():
    assert carbon_scores([0, 5, 5, 10]) == pytest.approx([0, 0.5, 0.5, 1])
    assert carbon_scores([7, 7, 7]) == pytest.approx([0.5, 0.5, 0.5])
    for values in ([0, None, 3], [0, -1, 3], [1, float("inf")]):
        with pytest.raises(PortfolioError):
            carbon_scores(values)


def test_selection_ties_manual_partition_and_feasibility():
    c = config()
    longs, shorts, _ = candidates([4, 3, 2, 1], np.zeros(4), c)
    assert longs == [3, 2] and shorts == [1, 0]
    with pytest.raises(PortfolioError, match="cap"):
        candidates([1, 2, 3, 4], np.arange(4), config(max_weight=0.1))
    with pytest.raises(PortfolioError, match="partition"):
        candidates([1, 2, 3, 4], np.arange(4), config(selection="manual", long_ids=[1], short_ids=[2]))
    with pytest.raises(ValidationError):
        config(selection="manual", long_ids=[1, 2], short_ids=[2, 3])


def test_non_neutral_allocations_are_reported_correctly():
    c = config(long_gross=0.6, short_gross=0.4, max_weight=0.5)
    r = solve(np.zeros(4), np.eye(4), np.zeros(4), [1, 2, 3, 4], ["SYNTHETIC"] * 4, [0, 1], [2, 3], c, 0)
    assert r["net_exposure"] == pytest.approx(0.2)
    assert r["gross_exposure"] == pytest.approx(1)


def test_solver_failure_and_invalid_weights_are_never_success(monkeypatch):
    def fail(*args, **kwargs):
        raise cp.error.SolverError("forced test failure")

    monkeypatch.setattr(cp.Problem, "solve", fail)
    with pytest.raises(PortfolioError, match="Clarabel failed") as exc:
        reference()
    assert exc.value.status == "solver_error"

    def invalid(problem, **kwargs):
        problem._status = cp.OPTIMAL
        problem.variables()[0].value = np.zeros(4)

    monkeypatch.setattr(cp.Problem, "solve", invalid)
    with pytest.raises(PortfolioError, match="verification"):
        reference()


def test_unsuccessful_solver_status_rejected(monkeypatch):
    def inaccurate(problem, **kwargs):
        problem._status = cp.OPTIMAL_INACCURATE
        problem.variables()[0].value = np.array([0.3, 0.2, -0.25, -0.25])

    monkeypatch.setattr(cp.Problem, "solve", inaccurate)
    with pytest.raises(PortfolioError, match="optimal_inaccurate"):
        reference()


def test_fixture_reproduces_stored_artifact_and_no_mutation():
    original = dataset()
    path = Path(__file__).resolve().parents[2] / "data/synthetic/portfolio-v1.json"
    assert original == json.loads(path.read_text())
    snapshot = copy.deepcopy(original)
    p, r = prepare(original, config())
    assert r["status"] == "ready" and r["aligned_observations"] == 260
    assert p["estimates"]["assets"][0]["expected_return_annual"] == pytest.approx(0.22)
    assert p["estimates"]["assets"][0]["emissions_tco2e"] == 900000
    assert 0 <= p["estimates"]["assets"][0]["carbon_score"] <= 1
    assert original == snapshot


@pytest.mark.parametrize(
    "change",
    [
        "missing-price",
        "missing-adjustment",
        "sparse",
        "missing-emissions",
        "location-basis",
        "missing-date",
        "same-day",
        "future-date",
        "boundary",
        "currency",
    ],
)
def test_ineligible_inputs_fail_closed(change):
    d = dataset()
    cid = 10001
    if change == "missing-price":
        d["prices"].pop(10)
    elif change in ("missing-adjustment", "sparse", "currency"):
        if change == "sparse":
            d["prices"] = [p for i, p in enumerate(d["prices"]) if p["company_id"] != cid or i < 7]
        else:
            for p in d["prices"]:
                if p["company_id"] == cid:
                    p["adjusted_close"] = None if change == "missing-adjustment" else p["adjusted_close"]
                    if change == "currency":
                        p["currency"] = "CHF"
    elif change == "missing-emissions":
        d["emissions"][0]["scope1"] = None
    elif change == "location-basis":
        d["emissions"][0]["scope2_basis"] = "location-based"
    elif change in ("missing-date", "same-day", "future-date"):
        d["emissions"][0]["disclosure_date"] = {
            "missing-date": None,
            "same-day": "2025-01-02",
            "future-date": "2025-01-03",
        }[change]
    elif change == "boundary":
        d["reviews"][str(cid)]["comparability_group"] = "incompatible test boundary"
    p, r = prepare(d, config())
    assert p is None and r["status"] == "insufficient" and r["blockers"]


def test_common_return_intervals_align_both_endpoints_without_imputation():
    d = dataset()
    removed = d["reviews"]["10001"]["expected_dates"][10]
    d["reviews"]["10001"]["expected_dates"].remove(removed)
    d["prices"] = [p for p in d["prices"] if not (p["company_id"] == 10001 and p["date"] == removed)]
    p, r = prepare(d, config())
    assert r["status"] == "ready"
    assert r["aligned_observations"] == 258
    assert p["estimates"]["assets"][0]["dropped_return_intervals"] == 1
    assert p["estimates"]["assets"][1]["dropped_return_intervals"] == 2


def test_later_vintage_not_backdated_and_estimation_window_changes_mean():
    d = dataset()
    future = copy.deepcopy(d["emissions"][0])
    future.update(year=2024, scope1=1e9, disclosure_date="2025-01-03")
    d["emissions"].append(future)
    p, r = prepare(d, config())
    assert r["status"] == "ready"
    assert p["estimates"]["assets"][0]["disclosure_year"] == 2023
    altered = copy.deepcopy(d)
    # Outside selected estimation window: future prices cannot change estimates or automatic sleeves.
    future_price = copy.deepcopy(d["prices"][0])
    future_price.update(date="2025-01-03", adjusted_close=1e10)
    altered["prices"].append(future_price)
    p2, _ = prepare(altered, config())
    assert np.array_equal(p["mu"], p2["mu"])
    assert p["longs"] == p2["longs"]


def test_sensitivity_and_zero_penalty_baseline_equality():
    c = config(carbon_penalty=0)
    p, r = prepare(dataset(), c)
    comparison = execute(p, r, c, "compare")["comparison"]
    assert comparison["traditional"] == comparison["carbon_aware"]
    sensitivity = execute(p, r, c, "sensitivity")["sensitivity"]
    assert sensitivity["carbon_nonincreasing"] and sensitivity["carbon_reduced"]
    assert sensitivity["portfolios"][0] == comparison["traditional"]
    c = config(max_weight=0.125)
    p, r = prepare(dataset(), c)
    frozen = execute(p, r, c, "sensitivity")["sensitivity"]
    assert frozen["carbon_nonincreasing"] and not frozen["carbon_reduced"]


@pytest.mark.parametrize("endpoint", ["optimize", "compare", "sensitivity"])
def test_api_synthetic_success_and_real_insufficiency(client, endpoint):
    response = client.post(f"/api/portfolio/{endpoint}", json={"data_mode": "synthetic"})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "success"
    assert result["readiness"]["synthetic"] is True
    assert result["estimates"]["observations"] == 260
    assert "SYNTHETIC" in result["warnings"][0]
    real = client.post(f"/api/portfolio/{endpoint}", json={}).json()
    assert real["status"] == "insufficient" and real["estimates"] is None
    assert real["portfolio"] is None and real["comparison"] is None and real["sensitivity"] is None


def test_readiness_and_infeasible_and_solver_api(client, monkeypatch):
    assert client.get("/api/portfolio/readiness").json()["status"] == "insufficient"
    assert client.get("/api/portfolio/readiness?data_mode=synthetic").json()["status"] == "ready"
    response = client.post("/api/portfolio/compare", json={"data_mode": "synthetic", "max_weight": 0.01}).json()
    assert response["status"] == "infeasible" and response["comparison"] is None

    def fail(*args, **kwargs):
        raise cp.error.SolverError("forced integration failure")

    monkeypatch.setattr(cp.Problem, "solve", fail)
    response = client.post("/api/portfolio/compare", json={"data_mode": "synthetic"}).json()
    assert response["status"] == "solver_error" and response["comparison"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"risk_aversion": -1},
        {"carbon_penalty": -1},
        {"penalties": [0, -1]},
        {"data_mode": "bad"},
        {"company_ids": [1, 1]},
        {"unknown": 1},
        {"start_date": "2025-01-02"},
        {"as_of": "2024-12-31"},
        {"selection": "manual", "long_ids": [1, 2], "short_ids": [2, 3]},
    ],
)
def test_api_invalid_parameters(client, body):
    assert client.post("/api/portfolio/optimize", json=body).status_code == 422


def test_unknown_or_wrong_mode_company_ids_do_not_silently_drop(client):
    r = client.post(
        "/api/portfolio/compare", json={"data_mode": "synthetic", "company_ids": [10001, 10002, 10003, 99999]}
    ).json()
    assert r["status"] == "insufficient" and r["comparison"] is None
    assert any("unavailable" in b for b in r["readiness"]["blockers"])


def test_manual_subset_uses_same_universe_and_financial_inputs(client):
    ids = [10001, 10002, 10007, 10008]
    body = dict(
        data_mode="synthetic", company_ids=ids, selection="manual", long_ids=ids[:2], short_ids=ids[2:], max_weight=0.3
    )
    r = client.post("/api/portfolio/compare", json=body).json()
    assert r["status"] == "success"
    assert r["readiness"]["long_ids"] == ids[:2]
    assert r["readiness"]["short_ids"] == ids[2:]
    assert [a["company_id"] for a in r["estimates"]["assets"]] == ids
    assert [p["company_id"] for p in r["comparison"]["traditional"]["positions"]] == ids
    assert [p["company_id"] for p in r["comparison"]["carbon_aware"]["positions"]] == ids
    assert r["comparison"]["difference"]["long_exposure"] == pytest.approx(0, abs=1e-7)
    assert r["comparison"]["difference"]["short_exposure"] == pytest.approx(0, abs=1e-7)


def test_review_failure_closed_and_post_cors(client, monkeypatch, tmp_path):
    path = tmp_path / "invalid-review.json"
    path.write_text('{"real":{"4":{"adjustment_verified":true}}}')
    monkeypatch.setenv("PORTFOLIO_REVIEW_FILE", str(path))
    r = client.get("/api/portfolio/readiness").json()
    assert r["status"] == "invalid_inputs"
    assert "verification refused" in r["blockers"][0]
    response = client.options(
        "/api/portfolio/compare",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert "POST" in response.headers["access-control-allow-methods"]


@pytest.mark.parametrize(
    "body",
    [
        '{"risk_aversion":NaN}',
        '{"carbon_penalty":Infinity}',
        '{"long_gross":-Infinity}',
        '{"penalties":[0,NaN]}',
        '{"max_weight":1e999}',
    ],
)
def test_nonfinite_http_values_return_validation_errors_not_server_errors(client, body):
    r = client.post("/api/portfolio/optimize", content=body, headers={"Content-Type": "application/json"})
    assert r.status_code == 422, r.text
    assert r.json()["detail"][0]["msg"]
