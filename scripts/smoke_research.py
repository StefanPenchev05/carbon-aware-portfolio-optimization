"""Read-only checks for the saved ECB bundle plus the preserved synthetic demo."""
import json
from urllib.request import urlopen


def get(path):
    with urlopen("http://localhost:8000/api" + path, timeout=15) as response:
        return json.load(response)


real = get("/data/quality")
assert real["synthetic"] is False
assert real["company_count"] == 0
assert real["companies_by_sector"] == {"Energy": 0, "Industrials": 0, "Pharmaceuticals": 0}
assert real["fx_observations"] == 7690
assert real["fx_currency_distribution"] == {currency: 1538 for currency in ("GBP", "CHF", "DKK", "SEK", "NOK")}
assert real["fx_start"] == "2020-01-02" and real["fx_end"] == "2025-12-31"
assert real["usable_matched_observations"] == 0
assert real["reported_percent"] is None and real["estimated_percent"] is None
synthetic = get("/data/quality?synthetic=true")
assert synthetic["company_count"] == 3 and synthetic["fx_observations"] == 0
assert synthetic["price_observations"] == 7 and synthetic["emission_observations"] == 3
assert synthetic["missing_publication_dates"] == 3
for company in get("/companies"):
    for emission in get(f'/companies/{company["id"]}/emissions'):
        assert emission["source"]["synthetic"] is True
        assert emission["scope1_status"] == "unknown"
        assert emission["disclosure_date"] is None
        assert emission["normalized_units"] == "tCO2e"
        assert emission["normalized_scopes"]["scope1"] == emission["scope1"]
print("Research API regression passed: real FX and synthetic corporate data remain separate")
