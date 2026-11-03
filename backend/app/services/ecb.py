"""Download the ECB's advertised XML feed once; replay imports from its hashed bundle."""

import argparse
import csv
import json
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from app.services.provenance import sha256

URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"
LICENSE = "https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html"


def parse_ecb(content, start, end, currencies):
    if start > end:
        raise ValueError("Invalid date range")
    root = ET.fromstring(content)
    rows = []
    seen = set()
    for cube in root.iter():
        if "time" not in cube.attrib:
            continue
        day = date.fromisoformat(cube.attrib["time"])
        if not start <= day <= end:
            continue
        for quote in cube:
            currency = quote.attrib.get("currency")
            if currency not in currencies:
                continue
            key = (day, currency)
            if key in seen:
                raise ValueError("Duplicate ECB rate")
            seen.add(key)
            from app.schemas.data import FXCSV

            rows.append(
                FXCSV(date=day, base_currency="EUR", quote_currency=currency, rate=quote.attrib["rate"]).model_dump()
            )
    if not rows or set(currencies) - {r["quote_currency"] for r in rows}:
        raise ValueError("Missing requested ECB currency/history")
    return sorted(rows, key=lambda r: (r["date"], r["quote_currency"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2020, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2025, 12, 31))
    parser.add_argument("--currencies", nargs="+", default=["GBP", "CHF", "DKK", "SEK", "NOK"])
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; immutable bundles must not be overwritten")
    with urlopen(Request(URL, headers={"User-Agent": "CarbonAwareAcademicPilot/0.2"}), timeout=60) as response:
        content = response.read(20_000_001)
    if len(content) > 20_000_000:
        parser.error("Unexpectedly large feed")
    rows = parse_ecb(content, args.start, args.end, args.currencies)
    args.output.mkdir(parents=True)
    raw = args.output / "ecb_reference_rates.xml"
    raw.write_bytes(content)
    csv_path = args.output / "real_fx.csv"
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["date", "base_currency", "quote_currency", "rate"])
        writer.writeheader()
        writer.writerows(rows)
    manifest = dict(
        source_name="ECB reference FX " + sha256(csv_path)[:12],
        reference=URL,
        retrieved_at=datetime.now(UTC).isoformat(),
        license_reference=LICENSE,
        usage_permission="ECB information reuse with accurate reproduction, attribution and explicit notice of modifications.",
        synthetic=False,
        notes="Source: European Central Bank. Selected dates/currencies reshaped from XML; values unchanged. Foreign currency units per EUR; reference rates, not execution prices.",
        files={csv_path.name: sha256(csv_path)},
        raw_files={raw.name: sha256(raw)},
    )
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            dict(rows=len(rows), start=str(rows[0]["date"]), end=str(rows[-1]["date"]), currencies=args.currencies)
        )
    )


if __name__ == "__main__":
    main()
