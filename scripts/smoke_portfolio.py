"""Read-only live portfolio regression. Synthetic observations never enter the DB."""

import json
from urllib.request import Request, urlopen

BASE = "http://localhost:8000/api/portfolio/"


def fetch(path, body=None):
    request = Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


real = fetch("readiness")
assert not real["synthetic"]
if real["status"] != "ready":
    result = fetch("compare", {})
    assert result["status"] != "success" and result["comparison"] is None
synthetic = fetch("readiness?data_mode=synthetic")
assert synthetic["synthetic"] and synthetic["selected_count"] == 8 and synthetic["aligned_observations"] == 260
comparison = fetch("compare", {"data_mode": "synthetic"})
assert comparison["status"] == "success"
baseline, aware = (comparison["comparison"][k] for k in ("traditional", "carbon_aware"))
for p in (baseline, aware):
    assert abs(p["net_exposure"]) < 1e-7 and abs(p["gross_exposure"] - 1) < 1e-7
    assert p["solver_status"] == "optimal" and p["max_constraint_violation"] <= 1e-7
assert aware["carbon_exposure_score"] < baseline["carbon_exposure_score"]
zero = fetch("compare", {"data_mode": "synthetic", "carbon_penalty": 0})
assert zero["comparison"]["traditional"] == zero["comparison"]["carbon_aware"]
sensitivity = fetch("sensitivity", {"data_mode": "synthetic"})["sensitivity"]
assert sensitivity["carbon_nonincreasing"] and sensitivity["carbon_reduced"]
assert sensitivity["portfolios"][0] == baseline
print(
    json.dumps(
        {
            "real_status": real["status"],
            "real_securities": real["selected_count"],
            "real_prices": real["price_count"],
            "real_adjusted_prices": real["adjusted_price_count"],
            "real_aligned_observations": real["aligned_observations"],
            "synthetic_observations": synthetic["aligned_observations"],
            "synthetic_baseline": {
                k: baseline[k] for k in ("expected_return_annual", "volatility_annual", "carbon_exposure_score")
            },
            "synthetic_carbon_aware": {
                k: aware[k] for k in ("expected_return_annual", "volatility_annual", "carbon_exposure_score")
            },
        },
        indent=2,
    )
)
