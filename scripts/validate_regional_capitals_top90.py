#!/usr/bin/env python3
"""Validate and report completeness of the local top-90 regional-capital cache."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import REGIONAL_CAPITALS, TOP_90_COUNTRIES_BY_AREA
from src.locations import fallback_location_key, load_all_capitals
from src.map_view import CLIMATE_COLORS, climate_category

REPORT = ROOT / "data/preloaded/regional_capitals_top90_validation_report.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validation_report() -> tuple[dict, list[str]]:
    reference = _load(TOP_90_COUNTRIES_BY_AREA).get("records", [])
    payload = _load(REGIONAL_CAPITALS)
    records = payload.get("records", [])
    statuses = payload.get("country_processing_status", [])
    errors: list[str] = []
    countries = [row.get("country") for row in reference]
    status_by_country = {row.get("country"): row for row in statuses}

    if len(reference) != 90:
        errors.append(f"top-90 reference has {len(reference)} entries, expected 90")
    if [row.get("area_rank") for row in reference] != list(range(1, 91)):
        errors.append("top-90 area ranks are not exactly 1 through 90")
    if len(statuses) != 90 or set(status_by_country) != set(countries):
        errors.append("every top-90 country must have exactly one processing status")

    missing_coordinates: list[str] = []
    missing_climate: list[str] = []
    missing_fields: list[str] = []
    climate_overwrites: list[str] = []
    by_country = Counter(record.get("country") for record in records)
    for record in records:
        label = f"{record.get('name')}, {record.get('country')}"
        required = ("name", "country", "administrative_region", "record_type")
        if any(not record.get(field) for field in required) or not (record.get("id") or record.get("qid")):
            missing_fields.append(label)
        if record.get("latitude") is None or record.get("longitude") is None:
            missing_coordinates.append(label)
        classification = record.get("climate_classification") or record.get("climate_classification_label")
        if not classification or str(classification).casefold() == "unknown":
            if not record.get("climate_extraction_status"):
                missing_climate.append(label)
        expected = climate_category(classification, record.get("primary_koppen_code"))
        if expected != "Unknown" and record.get("climate_group") == "Unknown":
            climate_overwrites.append(label)
        if record.get("climate_group") not in CLIMATE_COLORS:
            errors.append(f"invalid climate group: {label}")

    no_capitals: list[str] = []
    for country in countries:
        status = status_by_country.get(country, {})
        count = by_country[country]
        if status.get("first_level_divisions_exist") and count == 0:
            errors.append(f"no regional capitals for {country}")
        if count == 0:
            reason = str(status.get("coverage_reason") or "").strip()
            if status.get("status") != "no_first_level_regional_capitals" or not reason:
                errors.append(f"incomplete country without documented reason: {country}")
            no_capitals.append(country)
        if status.get("regional_capitals_count") != count:
            errors.append(f"processing count mismatch for {country}")

    qids = [str(record["qid"]) for record in records if record.get("qid")]
    duplicate_qids = sorted(value for value, count in Counter(qids).items() if count > 1)
    fallback = [fallback_location_key(record) for record in records if not record.get("qid")]
    duplicate_fallback = sorted(key for key, count in Counter(fallback).items() if count > 1)
    errors += [f"duplicate QID: {value}" for value in duplicate_qids]
    errors += [f"duplicate record: {value}" for value in duplicate_fallback]
    errors += [f"missing required fields: {value}" for value in missing_fields]
    errors += [f"missing coordinates: {value}" for value in missing_coordinates]
    errors += [f"missing climate data/reason: {value}" for value in missing_climate]
    errors += [f"valid climate overwritten with Unknown: {value}" for value in climate_overwrites]

    countries_missing_coordinates = sorted({r.get("country") for r in records if r.get("latitude") is None or r.get("longitude") is None})
    countries_missing_climate = sorted({r.get("country") for r in records if f"{r.get('name')}, {r.get('country')}" in missing_climate})
    report = {
        "countries_complete": sorted(country for country in countries if by_country[country] and country in status_by_country),
        "countries_with_no_first_level_regional_capitals_found": no_capitals,
        "countries_with_missing_coordinates": countries_missing_coordinates,
        "countries_with_missing_climate_data": countries_missing_climate,
        "duplicate_records": {"qids": duplicate_qids, "fallback_keys": [list(key) for key in duplicate_fallback]},
        "total_countries_processed": len(statuses),
        "total_regional_capitals_found": len(records),
        "validation_errors": errors,
    }
    runtime_records = load_all_capitals()
    runtime = {record.get("name"): record for record in runtime_records}
    for expected_name in ("Kraków", "Stavanger"):
        record = runtime.get(expected_name)
        if not record:
            errors.append(f"runtime startup dataset missing {expected_name}")
        elif record.get("latitude") is None or record.get("longitude") is None or not record.get("administrative_region"):
            errors.append(f"runtime startup metadata incomplete for {expected_name}")
    bogota = runtime.get("Bogotá", {})
    if bogota.get("climate_classification") != "Tropical highland climate" or bogota.get("climate_group") != "Highland / Mountain":
        errors.append("Bogotá climate regression: expected Tropical highland climate / Highland / Mountain")
    report.update({
        "missing_expected_capitals": [name for name in ("Kraków", "Stavanger") if name not in runtime],
        "applied_curated_overrides": [name for name, record in runtime.items() if record.get("classification_source_priority") == "curated_english_override"],
        "runtime_startup_capitals": len(runtime_records),
    })
    report["validation_errors"] = errors
    return report, errors


def main() -> int:
    report, errors = validation_report()
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
