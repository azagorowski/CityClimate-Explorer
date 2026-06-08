#!/usr/bin/env python3
"""Validate local top-90 regional-capital and climate-zone startup assets."""
from __future__ import annotations

from collections import Counter
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.locations import (fallback_location_key, load_climate_zones, load_polar_border_capitals,
                           load_regional_capitals, load_top90_country_reference,
                           load_top90_regional_capitals, validate_climate_zone_groups)
from src.map_view import CLIMATE_COLORS, climate_category

REPORT = ROOT / "data/preloaded/regional_capitals_top90_validation_report.json"


def validation_report() -> tuple[dict, list[str]]:
    errors: list[str] = []
    top90 = load_top90_country_reference()
    records = load_regional_capitals()
    top90_records = load_top90_regional_capitals()
    polar_records = load_polar_border_capitals()
    country_names = [row.get("country") for row in top90]
    if len(top90) != 90:
        errors.append(f"top-90 reference has {len(top90)} entries, expected 90")
    if [row.get("area_rank") for row in top90] != list(range(1, 91)):
        errors.append("top-90 area ranks are not exactly 1 through 90")
    covered = {record.get("country") for record in top90_records}
    missing_countries = sorted(set(country_names) - covered)
    errors.extend(f"no regional capitals for {country}" for country in missing_countries)

    required_polar = {"Greenland", "Norway", "Sweden", "Finland", "Iceland", "Canada", "United States", "Russia", "Argentina", "Chile"}
    polar_countries = {record.get("country") for record in polar_records}
    errors.extend(f"no polar-border administrative capitals for {country}" for country in sorted(required_polar - polar_countries))

    qids = [str(record["qid"]) for record in records if record.get("qid")]
    duplicate_qids = sorted(qid for qid, count in Counter(qids).items() if count > 1)
    fallback = [fallback_location_key(record) for record in records if not record.get("qid")]
    duplicate_fallback = [key for key, count in Counter(fallback).items() if count > 1]
    errors.extend(f"duplicate city QID: {qid}" for qid in duplicate_qids)
    errors.extend(f"duplicate fallback record: {key}" for key in duplicate_fallback)

    missing_coordinates: list[str] = []
    missing_admin: list[str] = []
    missing_climate: list[str] = []
    suspicious: list[str] = []
    for record in top90_records:
        label = f"{record.get('name')}, {record.get('country')}"
        if not record.get("id") and not record.get("marker_id"):
            errors.append(f"missing stable ID: {label}")
        if record.get("latitude") is None or record.get("longitude") is None:
            missing_coordinates.append(label)
        if not record.get("country") or not record.get("administrative_region") or not record.get("administrative_region_type"):
            missing_admin.append(label)
        classification = record.get("climate_classification") or record.get("climate_classification_label")
        if not classification or str(classification).casefold() == "unknown":
            if not record.get("climate_extraction_status"):
                missing_climate.append(label)
        expected_group = climate_category(classification, record.get("primary_koppen_code"))
        if record.get("climate_group") not in CLIMATE_COLORS or record.get("climate_group") != expected_group:
            suspicious.append(label)
        if not record.get("climate_classification_source_metadata") or not record.get("provenance"):
            errors.append(f"missing source/provenance metadata: {label}")
    errors.extend(f"missing coordinates: {label}" for label in missing_coordinates)
    errors.extend(f"missing administrative metadata: {label}" for label in missing_admin)
    errors.extend(f"missing climate classification and logged reason: {label}" for label in missing_climate)
    errors.extend(f"suspicious climate mapping: {label}" for label in suspicious)

    zones = load_climate_zones()
    if not zones.get("features"):
        errors.append("climate-zone GeoJSON has no features")
    errors.extend(f"invalid climate-zone group: {group}" for group in validate_climate_zone_groups(zones))
    report = {
        "total_countries_processed": len(top90),
        "total_regional_capitals_found": len(top90_records),
        "missing_countries": missing_countries,
        "missing_coordinates": missing_coordinates,
        "missing_administrative_metadata": missing_admin,
        "missing_climate_classifications_without_reason": missing_climate,
        "duplicate_records": {"qids": duplicate_qids, "fallback_keys": [list(key) for key in duplicate_fallback]},
        "suspicious_climate_mappings": suspicious,
        "validation_errors": errors,
    }
    return report, errors


def validate_regional_capitals() -> list[str]:
    return validation_report()[1]


def main() -> int:
    report, errors = validation_report()
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in {"validation_errors"}}, ensure_ascii=False, indent=2))
    if errors:
        print("Regional-capital validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Regional-capital validation passed; report written to {REPORT}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
