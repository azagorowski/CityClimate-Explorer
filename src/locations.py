"""Local national/regional-capital and climate-zone dataset helpers."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .capitals import city_marker_id, load_preloaded_capitals
from .config import CLIMATE_ZONES, KOPPEN_CLIMATE_ZONES, POLAR_BORDER_CAPITALS, REGIONAL_CAPITALS
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


def _load_regional_file(path: Path, default_scope: str) -> list[dict[str, Any]]:
    payload = read_json(path, default={})
    records = payload.get("records", []) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        return []
    result: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        city = dict(record)
        city.setdefault("record_type", "regional_capital")
        city.setdefault("record_scope", default_scope)
        city.setdefault("primary_koppen_code", None)
        city.setdefault("secondary_koppen_codes", [])
        city.setdefault("climate_data", [])
        city.setdefault("extraction_status", city.get("climate_extraction_status", "preloaded regional-capital metadata"))
        city.setdefault("continent", city.get("region"))
        city.setdefault("region", city.get("continent"))
        city.setdefault("climate_classification", "Unknown")
        city.setdefault("climate_classification_label", city["climate_classification"])
        city.setdefault("climate_group", climate_category(city.get("climate_classification_label"), city.get("primary_koppen_code")))
        city["marker_id"] = city_marker_id(city)
        result.append(city)
    return result


def load_top15_regional_capitals() -> list[dict[str, Any]]:
    """Load first-level capitals for the 15 largest countries."""
    return _load_regional_file(REGIONAL_CAPITALS, "top15_country_regional_capital")


def load_polar_border_capitals() -> list[dict[str, Any]]:
    """Load curated polar-border regional/local administrative centers."""
    return _load_regional_file(POLAR_BORDER_CAPITALS, "polar_border_regional_capital")


def load_regional_capitals() -> list[dict[str, Any]]:
    """Load and deduplicate both generated regional-capital snapshots locally."""
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    # Polar records are more specific and therefore win overlaps with top-15 rows.
    for city in load_polar_border_capitals() + load_top15_regional_capitals():
        key = (_text_key(city.get("name")), _text_key(city.get("country")))
        if key in seen:
            continue
        seen.add(key)
        output.append(city)
    return output

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
        city.setdefault("record_scope", "world_national_capital")
        city.setdefault("primary_koppen_code", None)
        city.setdefault("secondary_koppen_codes", [])
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


def load_koppen_climate_zones() -> dict[str, Any]:
    """Load the precomputed detailed Köppen GeoJSON without network access."""
    try:
        payload = json.loads(Path(KOPPEN_CLIMATE_ZONES).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"type": "FeatureCollection", "features": []}
    if payload.get("type") != "FeatureCollection":
        return {"type": "FeatureCollection", "features": []}
    return payload


def validate_koppen_zone_features(payload: dict[str, Any]) -> list[str]:
    """Return validation errors for detailed Köppen feature metadata."""
    errors = []
    valid_groups = set(CLIMATE_COLORS) - {"Unknown"}
    code_pattern = re.compile(r"^(?:A[fmsw]|B[WS][hk]|C[fsw][abc]|D[fsw][abcd]|E[TF]|H)$", re.I)
    for index, feature in enumerate(payload.get("features", [])):
        properties = feature.get("properties", {})
        code = str(properties.get("koppen_code") or "")
        if not code_pattern.fullmatch(code):
            errors.append(f"feature {index}: invalid Köppen code {code!r}")
        if properties.get("climate_group") not in valid_groups:
            errors.append(f"feature {index}: invalid climate group {properties.get('climate_group')!r}")
        if not properties.get("koppen_name"):
            errors.append(f"feature {index}: missing Köppen name")
    return errors


def validate_climate_zone_groups(payload: dict[str, Any]) -> list[str]:
    """Return invalid climate-group labels found in a GeoJSON payload."""
    return sorted({
        str(feature.get("properties", {}).get("climate_group"))
        for feature in payload.get("features", [])
        if feature.get("properties", {}).get("climate_group") not in CLIMATE_COLORS
    })
