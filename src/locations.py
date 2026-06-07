"""Local national/regional-capital and climate-zone dataset helpers."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .capitals import city_marker_id, load_preloaded_capitals
from .config import CLIMATE_ZONES, REGIONAL_CAPITALS
from .map_view import CLIMATE_COLORS, climate_category
from .storage import read_json

TOP_15_COUNTRIES = (
    "Russia", "Canada", "China", "United States", "Brazil", "Australia", "India",
    "Argentina", "Kazakhstan", "Algeria", "Democratic Republic of the Congo",
    "Saudi Arabia", "Mexico", "Indonesia", "Sudan",
)


def _text_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def fallback_location_key(city: dict[str, Any]) -> tuple[str, str, str]:
    """Return the documented non-QID regional-capital duplicate key."""
    return (_text_key(city.get("name")), _text_key(city.get("country")), _text_key(city.get("administrative_region")))


def load_regional_capitals() -> list[dict[str, Any]]:
    """Load the generated regional-capital snapshot without network access."""
    payload = read_json(REGIONAL_CAPITALS, default={})
    records = payload.get("records", []) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        return []
    result: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        city = dict(record)
        city.setdefault("record_type", "regional_capital")
        city.setdefault("climate_data", [])
        city.setdefault("extraction_status", city.get("climate_extraction_status", "preloaded regional-capital metadata"))
        city.setdefault("continent", city.get("region"))
        city.setdefault("region", city.get("continent"))
        city.setdefault("climate_classification", "Unknown")
        city.setdefault("climate_classification_label", city["climate_classification"])
        city.setdefault("climate_group", climate_category(city.get("climate_classification_label"), city.get("climate_classification")))
        city["marker_id"] = city_marker_id(city)
        result.append(city)
    return result


def deduplicate_locations(national: list[dict[str, Any]], regional: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge locations, retaining national-capital records when a city overlaps."""
    output: list[dict[str, Any]] = []
    seen_qids: set[str] = set()
    seen_city_country: set[tuple[str, str]] = set()
    seen_fallback: set[tuple[str, str, str]] = set()
    tagged_records = [(record, "national_capital") for record in national]
    tagged_records.extend((record, "regional_capital") for record in regional)
    for record, default_type in tagged_records:
        city = dict(record)
        city.setdefault("record_type", default_type)
        qid = str(city.get("qid") or "").strip()
        city_country = (_text_key(city.get("name")), _text_key(city.get("country")))
        fallback = fallback_location_key(city)
        if qid and qid in seen_qids:
            continue
        # National capitals are authoritative even when regional records use a
        # different/missing QID for the same physical city.
        if city.get("record_type") == "regional_capital" and city_country in seen_city_country:
            continue
        if not qid and fallback in seen_fallback:
            continue
        if qid:
            seen_qids.add(qid)
        seen_city_country.add(city_country)
        seen_fallback.add(fallback)
        output.append(city)
    return output


def load_all_capitals() -> list[dict[str, Any]]:
    """Load and merge both preloaded datasets, with no runtime HTTP work."""
    national = load_preloaded_capitals()
    for city in national:
        city["record_type"] = "national_capital"
        city.setdefault("administrative_region", None)
        city.setdefault("administrative_region_type", None)
        city.setdefault("administrative_region_qid", None)
    return deduplicate_locations(national, load_regional_capitals())


def load_climate_zones() -> dict[str, Any]:
    """Load the lightweight local climate-zone GeoJSON."""
    try:
        payload = json.loads(Path(CLIMATE_ZONES).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"type": "FeatureCollection", "features": []}
    if payload.get("type") != "FeatureCollection":
        return {"type": "FeatureCollection", "features": []}
    return payload


def validate_climate_zone_groups(payload: dict[str, Any]) -> list[str]:
    """Return invalid climate-group labels found in a GeoJSON payload."""
    return sorted({
        str(feature.get("properties", {}).get("climate_group"))
        for feature in payload.get("features", [])
        if feature.get("properties", {}).get("climate_group") not in CLIMATE_COLORS
    })
