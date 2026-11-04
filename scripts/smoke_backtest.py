"""Read-only live historical-evaluation checks. Never import synthetic observations."""

import json
from urllib.request import Request, urlopen

BASE = "http://localhost:8000/api/backtest/"


def call(path, body=None):
    request = Request(
        BASE + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=60) as response:
        return json.load(response)


real = call("readiness")
assert not real["synthetic"]
if real["status"] != "ready":
    r = call("compare", {})
    assert r["status"] != "success" and r["strategies"] == []
r = call("compare", dict(data_mode="synthetic", penalties=[0, 0.1]))
assert r["status"] == "success", r["message"]
baseline, aware = r["strategies"]
assert baseline["financial"]["evaluation_periods"] == 24
assert baseline["financial"]["daily_observations"] == 521
assert len({d["date"] for d in baseline["daily"]}) == 521
for a, b in zip(baseline["rebalances"], aware["rebalances"], strict=True):
    assert a["training_end"] < a["decision_date"]
    assert a["eligible_ids"] == b["eligible_ids"] and a["in_sample"] == b["in_sample"]
    assert a["target_portfolio"]["carbon_exposure_score"] >= b["target_portfolio"]["carbon_exposure_score"] - 1e-7
assert 20008 not in baseline["rebalances"][0]["eligible_ids"]
assert 20008 in baseline["rebalances"][6]["eligible_ids"]
assert 20007 not in baseline["rebalances"][18]["eligible_ids"]
print(
    json.dumps(
        {
            "real_status": real["status"],
            "real_securities": real["company_count"],
            "real_prices": real["price_count"],
            "synthetic_periods": 24,
            "synthetic_daily_returns": 521,
            "synthetic_results": [
                {
                    "lambda": s["carbon_penalty"],
                    "cumulative_signed_return": s["financial"]["cumulative_return"],
                    "max_drawdown": s["financial"]["maximum_drawdown"],
                    "mean_carbon_proxy": s["carbon"]["average_rebalance_score"],
                }
                for s in r["strategies"]
            ],
        },
        indent=2,
    )
)
