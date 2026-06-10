"""Local national/regional-capital and climate-zone dataset helpers."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .capitals import city_marker_id, load_preloaded_capitals
from .config import (CLIMATE_ZONES, COUNTRY_BOUNDARIES, KOPPEN_CLIMATE_ZONES, POLAR_BORDER_CAPITALS,
                     REGIONAL_CAPITALS, TOP_90_COUNTRIES_BY_AREA)
from .city_cache import apply_climate_classification_override
from .map_view import CLIMATE_COLORS, climate_category
from .normalize import normalized_search_key
from .storage import read_json

TOP_15_COUNTRIES = (
    "Russia", "Canada", "China", "United States", "Brazil", "Australia", "India",
    "Argentina", "Kazakhstan", "Algeria", "Democratic Republic of the Congo",
    "Saudi Arabia", "Mexico", "Indonesia", "Sudan",
)


def load_top90_country_reference() -> list[dict[str, Any]]:
    """Load the deterministic local top-90 country-by-area reference."""
    payload = read_json(TOP_90_COUNTRIES_BY_AREA, default={})
    records = payload.get("records", []) if isinstance(payload, dict) else []
    return [record for record in records if isinstance(record, dict)]


def top90_country_names() -> tuple[str, ...]:
    """Return top-90 countries in documented area-rank order."""
    return tuple(str(record.get("country")) for record in load_top90_country_reference() if record.get("country"))


def _text_key(value: Any) -> str:
    return normalized_search_key(value)


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
        source_metadata = city.get("climate_classification_source_metadata") or {}
        city.setdefault("climate_source_priority", source_metadata.get("source_priority") or city.get("climate_classification_source"))
        city.setdefault("classification_source_priority", city.get("climate_source_priority"))
        aliases = [str(alias) for alias in city.get("aliases", []) if alias]
        canonical_key = normalized_search_key(city.get("name"))
        city["aliases"] = list(dict.fromkeys(aliases))
        city["search_keys"] = list(dict.fromkeys([canonical_key, *(normalized_search_key(alias) for alias in aliases)]))
        city = apply_climate_classification_override(city)
        city["marker_id"] = city_marker_id(city)
        result.append(city)
    return result


def load_top90_regional_capitals() -> list[dict[str, Any]]:
    """Load first-level capitals for the 90 largest countries by area."""
    return _load_regional_file(REGIONAL_CAPITALS, "top90_country_regional_capital")


def load_top15_regional_capitals() -> list[dict[str, Any]]:
    """Compatibility loader returning top-90 records for the original top-15 countries."""
    top15 = set(TOP_15_COUNTRIES)
    return [record for record in load_top90_regional_capitals() if record.get("country") in top15]


def load_polar_border_capitals() -> list[dict[str, Any]]:
    """Load curated polar-border regional/local administrative centers."""
    return _load_regional_file(POLAR_BORDER_CAPITALS, "polar_border_regional_capital")


def load_regional_capitals() -> list[dict[str, Any]]:
    """Load and deduplicate both generated regional-capital snapshots locally."""
    output: list[dict[str, Any]] = []
    seen_qids: set[str] = set()
    seen_fallback: set[tuple[str, str, str]] = set()
    # Polar records are more specific and therefore win overlaps with top-90 rows.
    for city in load_polar_border_capitals() + load_top90_regional_capitals():
        qid = str(city.get("qid") or "").strip()
        fallback = fallback_location_key(city)
        if (qid and qid in seen_qids) or (not qid and fallback in seen_fallback):
            continue
        if qid:
            seen_qids.add(qid)
        seen_fallback.add(fallback)
        output.append(city)
    return output

def _merge_known_fields(preferred: dict[str, Any], duplicate: dict[str, Any]) -> dict[str, Any]:
    """Merge duplicate records without replacing useful values by empty/Unknown ones."""
    merged = dict(preferred)
    for key, value in duplicate.items():
        current = merged.get(key)
        if current in (None, "", "Unknown", [], {}) and value not in (None, "", "Unknown", [], {}):
            merged[key] = value
    scopes = [scope for scope in [preferred.get("record_scope"), duplicate.get("record_scope")] if scope]
    if scopes:
        merged["record_scopes"] = list(dict.fromkeys(scopes))
    return merged


def deduplicate_locations(national: list[dict[str, Any]], regional: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge locations QID-first, using name/country/region only when QID is absent."""
    output: list[dict[str, Any]] = []
    index_by_qid: dict[str, int] = {}
    index_by_fallback: dict[tuple[str, str, str], int] = {}
    national_by_city_country: dict[tuple[str, str], int] = {}
    tagged_records = [(record, "national_capital") for record in national]
    tagged_records.extend((record, "regional_capital") for record in regional)
    for record, default_type in tagged_records:
        city = dict(record)
        city.setdefault("record_type", default_type)
        qid = str(city.get("qid") or "").strip()
        fallback = fallback_location_key(city)
        duplicate_index = index_by_qid.get(qid) if qid else index_by_fallback.get(fallback)
        city_country = (_text_key(city.get("name")), _text_key(city.get("country")))
        if duplicate_index is None and city.get("record_type") != "national_capital":
            duplicate_index = national_by_city_country.get(city_country)
        if duplicate_index is not None:
            output[duplicate_index] = _merge_known_fields(output[duplicate_index], city)
            continue
        if qid:
            index_by_qid[qid] = len(output)
        index_by_fallback[fallback] = len(output)
        if city.get("record_type") == "national_capital":
            national_by_city_country[city_country] = len(output)
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


def load_country_boundaries() -> dict[str, Any]:
    """Load simplified country boundaries from the bundled local GeoJSON."""
    payload = read_json(COUNTRY_BOUNDARIES, default={})
    return payload if isinstance(payload, dict) else {}
