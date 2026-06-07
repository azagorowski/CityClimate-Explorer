#!/usr/bin/env python3
"""Validate local regional-capital and climate-zone startup assets."""
from __future__ import annotations

from collections import Counter
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.locations import TOP_15_COUNTRIES, fallback_location_key, load_climate_zones, load_polar_border_capitals, load_regional_capitals, load_top15_regional_capitals, validate_climate_zone_groups
from src.map_view import CLIMATE_COLORS


def validate_regional_capitals() -> list[str]:
    errors: list[str] = []
    records = load_regional_capitals()
    top15_records = load_top15_regional_capitals()
    polar_records = load_polar_border_capitals()
    countries = {record.get("country") for record in top15_records}
    for country in TOP_15_COUNTRIES:
        if country not in countries:
            errors.append(f"no regional capitals for {country}")
    required_polar = {"Greenland", "Norway", "Sweden", "Finland", "Iceland", "Canada", "United States", "Russia", "Argentina", "Chile"}
    polar_countries = {record.get("country") for record in polar_records}
    for country in sorted(required_polar - polar_countries):
        errors.append(f"no polar-border administrative capitals for {country}")
    qids = [str(record["qid"]) for record in records if record.get("qid")]
    for qid, count in Counter(qids).items():
        if count > 1:
            errors.append(f"duplicate city QID: {qid}")
    fallback = [fallback_location_key(record) for record in records if not record.get("qid")]
    for key, count in Counter(fallback).items():
        if count > 1:
            errors.append(f"duplicate fallback record: {key}")
    for record in records:
        label = f"{record.get('name')}, {record.get('country')}"
        if record.get("latitude") is None or record.get("longitude") is None:
            errors.append(f"missing coordinates: {label}")
        if not record.get("country") or not record.get("administrative_region") or not record.get("administrative_region_type"):
            errors.append(f"missing administrative metadata: {label}")
        if not record.get("climate_classification") and not record.get("climate_extraction_status"):
            errors.append(f"missing climate classification and reason: {label}")
        if record.get("climate_group") not in CLIMATE_COLORS:
            errors.append(f"invalid climate group: {label}")
        if record.get("record_scope") not in {"top15_country_regional_capital", "polar_border_regional_capital"}:
            errors.append(f"invalid record scope: {label}")
        if not record.get("climate_classification_source_metadata"):
            errors.append(f"missing climate source metadata: {label}")
        if not record.get("provenance"):
            errors.append(f"missing provenance: {label}")
    zones = load_climate_zones()
    if not zones.get("features"):
        errors.append("climate-zone GeoJSON has no features")
    errors.extend(f"invalid climate-zone group: {group}" for group in validate_climate_zone_groups(zones))
    return errors


def main() -> int:
    errors = validate_regional_capitals()
    if errors:
        print("Regional-capital validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Regional-capital and climate-zone validation passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
