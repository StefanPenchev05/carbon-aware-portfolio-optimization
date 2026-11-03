"""Read-only HTTP smoke checks against the documented synthetic demo deployment."""
import json
from urllib.error import HTTPError
from urllib.request import urlopen

BASE = "http://localhost:8000"


def get(path):
    with urlopen(BASE + path, timeout=10) as response:
        return json.load(response)


assert get("/api/health")["database"] == "connected"
companies = get("/api/companies")
assert len(companies) == 3
assert all(c["source"]["synthetic"] for c in companies)
for sector in ("Energy", "Industrials", "Pharmaceuticals"):
    rows = get("/api/companies?sector=" + sector)
    assert len(rows) == 1 and rows[0]["sector"] == sector
for company in companies:
    company_id = company["id"]
    assert get(f"/api/companies/{company_id}")["isin"] == company["isin"]
    prices = get(f"/api/companies/{company_id}/prices")
    emissions = get(f"/api/companies/{company_id}/emissions")
    assert all(p["source"]["synthetic"] for p in prices + emissions)
    if company["sector"] == "Energy":
        assert len(get(f"/api/companies/{company_id}/prices?start=2025-01-03&end=2025-01-03")) == 1
        assert len(get(f"/api/companies/{company_id}/emissions?start_year=2024&end_year=2024")) == 1
        assert emissions[0]["scope3"] is None
    if company["sector"] == "Pharmaceuticals":
        assert emissions == []
for path, expected in (("/api/companies/999999", 404), ("/api/companies/1/prices?start=bad", 422)):
    try:
        get(path)
        raise AssertionError("Expected HTTP error")
    except HTTPError as exc:
        assert exc.code == expected
coverage = get("/api/data/coverage")
assert sum(c["price_count"] for c in coverage) == 7
assert sum(c["emission_count"] for c in coverage) == 3
assert get("/openapi.json")["info"]["version"] == "0.1.0"
print("Live PostgreSQL API smoke checks passed")
