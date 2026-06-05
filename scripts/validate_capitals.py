#!/usr/bin/env python3
"""Validate that the bundled sovereign-state capital dataset stays complete.

The repository keeps a local, fast-start capital seed file.  This script checks
basic integrity constraints and reports missing entries from a maintained list of
sovereign-state/observer-state capitals represented in the current product scope.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPITALS_PATH = ROOT / "data" / "preloaded" / "country_capitals.json"
EXPECTED_PATH = ROOT / "data" / "preloaded" / "expected_sovereign_capitals.json"

# Country -> expected capital display name.  This separate manifest lets CI
# report accidental drops from the runtime seed dataset.
EXPECTED_CAPITALS = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
EXPECTED_BY_COUNTRY = {item["country"]: item["capital"] for item in EXPECTED_CAPITALS if item.get("country") and item.get("capital")}


def validate_capitals() -> list[str]:
    records = json.loads(CAPITALS_PATH.read_text(encoding="utf-8"))
    present = {(item.get("country"), item.get("name")) for item in records}
    errors: list[str] = []
    for country, capital in sorted(EXPECTED_BY_COUNTRY.items()):
        if (country, capital) not in present:
            errors.append(f"Missing capital: {capital}, {country}")
    for item in records:
        if item.get("latitude") is None or item.get("longitude") is None:
            errors.append(f"Missing coordinates: {item.get('name')}, {item.get('country')}")
    return errors


def main() -> int:
    errors = validate_capitals()
    if errors:
        print("Capital validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Capital validation passed for {len(EXPECTED_BY_COUNTRY)} sovereign-state capitals.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
