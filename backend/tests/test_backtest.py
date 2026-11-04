"""Reference accounting and explicitly SYNTHETIC walk-forward validation."""

import copy
from datetime import date

import numpy as np
import pytest

from app.schemas.backtest import BacktestRequest, BacktestResponse
from app.services.backtest_accounting import Book
from app.services.backtest_data import at_decision, membership
from app.services.backtest_engine import experiment, plan_history
from app.services.backtest_execution import construct
from app.services.backtest_metrics import financial_metrics
from app.services.backtest_schedule import windows
from app.services.portfolio import PortfolioError
from app.services.preparation import day
from app.services.synthetic_history import dataset


def config(**values):
    return BacktestRequest(data_mode="synthetic", **values)


def short_config(**values):
    return config(end_date=date(2024, 3, 29), penalties=[0, 0.1], **values)


def test_rolling_schedule_disjoint_training_and_holding_partition():
    data = dataset()
    cfg = config()
    result = windows(data["calendar"], cfg)
    assert len(result) == 24
    dates = [day(d) for d in data["calendar"]]
    all_holding = []
    for w in result:
        assert w["training_start"] < w["training_end"] < w["decision_date"] < w["holding_end"]
        assert dates.index(w["training_end"]) - dates.index(w["training_start"]) == 126
        all_holding.extend(w["holding_dates"][1:])
    assert len(set(all_holding)) == len(all_holding) == 521
    assert all_holding == [d for d in dates if cfg.start_date < d <= cfg.end_date]


def test_expanding_and_quarterly_schedule_and_insufficient_history():
    d = dataset()
    r = windows(d["calendar"], config(window="expanding", frequency="quarterly"))
    assert len(r) == 8
    assert len({w["training_start"] for w in r}) == 1
    assert r[1]["training_end"] > r[0]["training_end"]
    with pytest.raises(PortfolioError, match="prior training"):
        windows(d["calendar"], config(start_date=date(2022, 1, 3), end_date=date(2023, 12, 29)))
    with pytest.raises(PortfolioError, match="endpoints"):
        windows(d["calendar"], config(start_date=date(2024, 1, 6)))


def test_signed_self_financing_pnl_cash_weight_drift_and_turnover():
    book = Book()
    old, change, turnover = book.rebalance({1: 0.5, 2: -0.5})
    assert old == {} and turnover == 1
    assert book.cash == 1 and book.equity == 1
    first = book.advance({1: 0.1, 2: 0.2}, date(2024, 1, 3))
    assert first["equity"] == pytest.approx(0.95)
    assert first["realized_return"] == pytest.approx(-0.05)
    assert book.notionals == pytest.approx({1: 0.55, 2: -0.6})
    assert first["gross_exposure"] == pytest.approx(1.15 / 0.95)
    second = book.advance({1: -0.1, 2: -0.1}, date(2024, 1, 4))
    assert second["equity"] == pytest.approx(0.955)
    assert second["realized_return"] == pytest.approx(0.005 / 0.95)
    old, change, turnover = book.rebalance({1: 0.5, 2: -0.5})
    assert old == pytest.approx({1: 0.495 / 0.955, 2: -0.54 / 0.955})
    assert turnover == pytest.approx(abs(0.5 - 0.495 / 0.955) + abs(-0.5 + 0.54 / 0.955))
    assert book.equity == pytest.approx(0.955)  # rebalance does not create/destroy capital
    book.rebalance({1: 0.5, 3: -0.5})
    assert 2 not in book.notionals and book.equity == pytest.approx(0.955)


def test_ruin_and_missing_returns_fail_closed():
    book = Book()
    book.rebalance({1: 0.5, 2: -0.5})
    with pytest.raises(PortfolioError, match="Missing holding"):
        book.advance({1: 0.01}, date(2024, 1, 3))
    with pytest.raises(PortfolioError, match="Capital exhausted"):
        book.advance({1: 0, 2: 3}, date(2024, 1, 3))


def test_metrics_cumulative_volatility_drawdown_sharpe_and_annualization_gate():
    daily = [
        dict(
            date=date(2024, 1, i + 2),
            realized_return=r,
            equity=e,
            gross_exposure=1,
            net_exposure=0,
            long_positions=2,
            short_positions=2,
        )
        for i, (r, e) in enumerate(((0.1, 1.1), (-0.1, 0.99)))
    ]
    steps = [dict(turnover_l1=1), dict(turnover_l1=0.2)]
    m = financial_metrics(daily, steps, min_annual_observations=2)
    assert m["cumulative_return"] == pytest.approx(-0.01)
    assert m["annualized_return"] == pytest.approx(0.99**126 - 1)
    assert m["annualized_volatility"] == pytest.approx(np.sqrt(0.02) * np.sqrt(252))
    assert m["maximum_drawdown"] == pytest.approx(0.1)
    assert m["sharpe_ratio"] == pytest.approx(0)
    assert m["turnover_l1_total"] == pytest.approx(1.2)
    assert m["average_gross_exposure"] == 1
    assert financial_metrics(daily, steps)["annualized_return"] is None
    assert financial_metrics(daily, steps, min_annual_observations=2, regular=False)["annualized_volatility"] is None
    assert financial_metrics(daily, steps, min_annual_observations=2, risk_free_rate=None)["sharpe_ratio"] is None
    daily[0].update(realized_return=-0.1, equity=0.9)
    daily[1].update(realized_return=0.1, equity=0.99)
    assert financial_metrics(daily, steps)["maximum_drawdown"] == pytest.approx(0.1)  # initial capital is a peak


def test_future_and_decision_close_prices_cannot_change_first_construction():
    d = dataset()
    c = short_config()
    w = windows(d["calendar"], c)[0]
    first = at_decision(d, c, w)
    modified = copy.deepcopy(d)
    for p in modified["prices"]:
        if day(p["date"]) >= w["decision_date"]:
            p["adjusted_close"] *= 1.5 + (p["company_id"] % 3) / 10
            p["close"] = p["adjusted_close"]
    changed = at_decision(modified, c, w)
    assert first["prepared"]["ids"] == changed["prepared"]["ids"]
    assert np.array_equal(first["prepared"]["mu"], changed["prepared"]["mu"])
    assert np.array_equal(first["prepared"]["covariance"], changed["prepared"]["covariance"])
    assert construct(first, 0.1) == construct(changed, 0.1)


def test_future_disclosures_and_later_vintages_not_retroactively_used():
    d = dataset()
    c = short_config()
    ws = windows(d["calendar"], c)
    future = copy.deepcopy(d["emissions"][0])
    future.update(year=2023, disclosure_date="2024-01-03", scope1=1e9)
    d["emissions"].append(future)
    before = at_decision(d, c, ws[0])
    after = at_decision(d, c, ws[1])
    assert before["prepared"]["estimates"]["assets"][0]["disclosure_year"] == 2022
    assert after["prepared"]["estimates"]["assets"][0]["disclosure_year"] == 2023
    future["disclosure_date"] = "2024-01-02"  # same day still excluded
    assert at_decision(d, c, ws[0])["prepared"]["estimates"]["assets"][0]["disclosure_year"] == 2022


def test_dated_membership_not_future_announcements():
    d = dataset()
    assert not membership(d, 20008, date(2024, 1, 2))
    assert membership(d, 20008, date(2024, 7, 1))
    assert membership(d, 20007, date(2025, 6, 2))
    assert not membership(d, 20007, date(2025, 7, 1))
    d["membership_events"].append(dict(company_id=20008, effective="2024-01-02", published="2024-01-03", active=True))
    assert not membership(d, 20008, date(2024, 1, 2))


@pytest.mark.parametrize("flag", ["membership_history_verified", "historical_classification_verified"])
def test_missing_historical_evidence_fails_readiness(flag):
    d = dataset()
    d[flag] = False
    plans, r = plan_history(d, short_config())
    assert plans is None and r["status"] == "insufficient"


def test_missing_future_holding_data_fails_whole_experiment_not_survivor_selection():
    d = dataset()
    c = short_config()
    w = windows(d["calendar"], c)[0]
    first = at_decision(d, c, w)
    d["prices"] = [p for p in d["prices"] if not (p["company_id"] == 20001 and p["date"] == "2024-01-15")]
    still = at_decision(d, c, w)
    assert first["prepared"]["ids"] == still["prepared"]["ids"]
    assert np.array_equal(first["prepared"]["mu"], still["prepared"]["mu"])
    r = experiment(d, c)
    assert r["status"] == "insufficient" and r["strategies"] == []


def test_full_comparison_dynamic_universe_drift_and_paired_carbon():
    c = config(penalties=[0, 0.1])
    r = experiment(dataset(), c)
    BacktestResponse.model_validate(r)
    assert r["status"] == "success"
    baseline, aware = r["strategies"]
    assert baseline["financial"]["daily_observations"] == 521
    assert baseline["financial"]["annualized_return"] is not None
    assert baseline["financial"]["evaluation_periods"] == 24
    assert 20008 not in baseline["rebalances"][0]["eligible_ids"]
    assert 20008 in baseline["rebalances"][6]["eligible_ids"]
    assert 20007 not in baseline["rebalances"][18]["eligible_ids"]
    assert 20007 in baseline["rebalances"][18]["weight_changes"]  # exited position closed
    assert baseline["carbon"]["score_definition_changed"]
    assert aware["carbon"]["average_paired_difference_from_baseline"] <= 1e-7
    for a, b in zip(baseline["rebalances"], aware["rebalances"], strict=True):
        assert a["eligible_ids"] == b["eligible_ids"] and a["in_sample"] == b["in_sample"]
        assert a["target_portfolio"]["long_exposure"] == pytest.approx(b["target_portfolio"]["long_exposure"], abs=1e-7)
        assert a["target_portfolio"]["short_exposure"] == pytest.approx(
            b["target_portfolio"]["short_exposure"], abs=1e-7
        )
        assert a["target_portfolio"]["carbon_exposure_score"] >= b["target_portfolio"]["carbon_exposure_score"] - 1e-7
    assert any(abs(x["net_exposure"]) > 1e-6 for x in baseline["daily"])
    compounded = np.prod([1 + d["realized_return"] for d in baseline["daily"]]) - 1
    assert compounded == pytest.approx(baseline["financial"]["cumulative_return"])


def test_zero_penalty_run_matches_comparison_baseline_and_no_input_mutation():
    data = dataset()
    snapshot = copy.deepcopy(data)
    c = short_config(carbon_penalty=0)
    run = experiment(data, c, "run")
    comparison = experiment(data, c, "compare")
    assert run["status"] == comparison["status"] == "success"
    assert run["strategies"][0] == comparison["strategies"][0]
    assert run["strategies"][0]["financial"]["annualized_return"] is None
    assert data == snapshot


@pytest.mark.parametrize("endpoint", ["run", "compare"])
def test_historical_api_synthetic_and_real_separation(client, endpoint):
    r = client.post(
        f"/api/backtest/{endpoint}", json={"data_mode": "synthetic", "end_date": "2024-03-29", "penalties": [0, 0.1]}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success" and body["readiness"]["synthetic"]
    assert "SYNTHETIC" in body["warnings"][0]
    assert body["strategies"][0]["rebalances"][0]["training_end"] < body["strategies"][0]["initial_date"]
    real = client.post(f"/api/backtest/{endpoint}", json={}).json()
    assert real["status"] == "insufficient" and real["strategies"] == []
    assert any("2026" in b for b in real["readiness"]["blockers"])


@pytest.mark.parametrize(
    "body",
    [
        {"training_sessions": 10},
        {"risk_aversion": -1},
        {"frequency": "weekly"},
        {"start_date": "2025-01-01", "end_date": "2024-01-01"},
        {"data_mode": "bad"},
        {"penalties": [-1]},
        {"unknown": 1},
        {"company_ids": [1, 1]},
        {"risk_free_rate": -1},
    ],
)
def test_api_invalid_protocols(client, body):
    assert client.post("/api/backtest/compare", json=body).status_code == 422


def test_readiness_query_and_nonfinite_json_and_unknown_ids(client):
    assert client.get("/api/backtest/readiness").json()["status"] == "insufficient"
    r = client.get("/api/backtest/readiness?data_mode=synthetic&end_date=2024-03-29")
    assert r.status_code == 200 and r.json()["scheduled_periods"] == 3
    assert (
        client.post(
            "/api/backtest/run", content='{"risk_aversion":NaN}', headers={"Content-Type": "application/json"}
        ).status_code
        == 422
    )
    r = client.post("/api/backtest/run", json={"data_mode": "synthetic", "company_ids": [1, 2, 3, 4]}).json()
    assert r["status"] == "insufficient" and not r["strategies"]


def test_historical_review_file_fails_closed(client, monkeypatch, tmp_path):
    path = tmp_path / "invalid-history.json"
    path.write_text('{"calendar":[]}')
    monkeypatch.setenv("BACKTEST_REVIEW_FILE", str(path))
    r = client.get("/api/backtest/readiness").json()
    assert r["status"] == "invalid_inputs"
    assert "no point-in-time approval" in r["blockers"][0]


def test_solver_failure_aborts_entire_historical_comparison(monkeypatch):
    import app.services.portfolio_experiment as execution

    def fail(*args, **kwargs):
        raise PortfolioError("Forced historical solver failure", "solver_error")

    monkeypatch.setattr(execution, "solve", fail)
    result = experiment(dataset(), short_config())
    assert result["status"] == "solver_error" and result["strategies"] == []


def test_deterministic_recipe_and_both_signs_and_covariance_regimes():
    import json
    from pathlib import Path

    from app.services.synthetic_history import SEED

    recipe = json.loads((Path(__file__).resolve().parents[2] / "data/synthetic/evaluation-v1.json").read_text())
    assert recipe["seed"] == SEED
    d = dataset()
    assert d == dataset()
    series = []
    for cid in (20001, 20002):
        values = np.array([p["adjusted_close"] for p in d["prices"] if p["company_id"] == cid])
        returns = values[1:] / values[:-1] - 1
        assert np.any(returns > 0) and np.any(returns < 0)
        series.append(returns)
    assert np.corrcoef([s[:400] for s in series])[0, 1] < np.corrcoef([s[530:690] for s in series])[0, 1]
