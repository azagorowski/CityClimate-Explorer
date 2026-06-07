#!/usr/bin/env python3
"""Validate the bundled capital seed and authoritative startup climate cache."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.capitals import load_preloaded_capitals  # noqa: E402
from src.map_view import CLIMATE_COLORS, classification_value  # noqa: E402

EXPECTED_PATH = ROOT / "data" / "preloaded" / "expected_sovereign_capitals.json"
EXPECTED_CAPITALS = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
EXPECTED_BY_COUNTRY = {item["country"]: item["capital"] for item in EXPECTED_CAPITALS if item.get("country") and item.get("capital")}
KNOWN_ENGLISH_CLIMATES = {
    "Tirana", "Bratislava", "Budapest", "Bogotá", "Warsaw", "Vienna", "Prague", "Madrid", "Rome",
    "Paris", "Berlin", "London", "Cairo", "Nairobi", "Tokyo", "Seoul", "Canberra", "Wellington",
}
REQUIRED_METADATA = {"source_name", "source_priority"}
REQUIRED_CLIMATE_FIELDS = {
    "climate_classification", "climate_group", "climate_source_name", "climate_source_language",
    "climate_source_title", "climate_source_url", "climate_source_priority", "climate_extraction_status",
}


def validate_capitals(records: list[dict[str, Any]] | None = None) -> list[str]:
    """Return hard validation errors; unresolved non-regression cities are reported separately."""
    capitals = records if records is not None else load_preloaded_capitals()
    present = {(item.get("country"), item.get("name")) for item in capitals}
    errors: list[str] = []
    for country, capital in sorted(EXPECTED_BY_COUNTRY.items()):
        if (country, capital) not in present:
            errors.append(f"Missing capital: {capital}, {country}")
    for item in capitals:
        identity = f"{item.get('name')}, {item.get('country')}"
        for field in ("name", "country", "continent", "latitude", "longitude", "climate_classification", "climate_group"):
            if item.get(field) in (None, ""):
                errors.append(f"Missing {field}: {identity}")
        if item.get("climate_group") not in CLIMATE_COLORS:
            errors.append(f"Invalid climate_group: {identity} ({item.get('climate_group')!r})")
        metadata = item.get("climate_classification_source_metadata")
        if not isinstance(metadata, dict) or not REQUIRED_METADATA.issubset(metadata):
            errors.append(f"Missing climate source metadata: {identity}")
        missing_fields = REQUIRED_CLIMATE_FIELDS - item.keys()
        if missing_fields:
            errors.append(f"Missing startup climate fields for {identity}: {sorted(missing_fields)}")
        if item.get("name") in KNOWN_ENGLISH_CLIMATES:
            if classification_value(item) == "Unknown":
                errors.append(f"Known English Wikipedia climate is unresolved: {identity}")
            elif metadata.get("source_priority") != "english_primary":
                errors.append(f"Regression capital is not English-primary: {identity}")
    return errors


def unknown_capitals(records: list[dict[str, Any]] | None = None) -> list[str]:
    capitals = records if records is not None else load_preloaded_capitals()
    return [f"{item.get('name')}, {item.get('country')}" for item in capitals if classification_value(item) == "Unknown"]


def main() -> int:
    capitals = load_preloaded_capitals()
    errors = validate_capitals(capitals)
    unknown = unknown_capitals(capitals)
    if unknown:
        print(f"WARNING: {len(unknown)} capital climate classifications remain Unknown:")
        for identity in unknown:
            print(f"- {identity}")
    if errors:
        print("Capital validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Capital validation passed for {len(capitals)} preloaded capitals.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
