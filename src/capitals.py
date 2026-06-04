"""Preloaded country-capital dataset helpers."""
from __future__ import annotations

from typing import Any

from .config import PRELOADED_CAPITALS
from .storage import read_json

SUPPORTED_CONTINENTS = ("Africa", "Asia", "Europe", "North America", "South America", "Oceania")


def countries_for_continent(capitals: list[dict[str, Any]], continent: str | None) -> list[str]:
    """Return sorted country names represented by preloaded capitals for a continent."""
    if not continent:
        return []
    return sorted({
        str(city.get("country"))
        for city in capitals
        if city.get("country") and (city.get("continent") or city.get("region")) == continent
    })


def country_identifier(capitals: list[dict[str, Any]], country: str | None) -> dict[str, str | None]:
    """Return the display name and optional Wikidata QID for a preloaded country."""
    if not country:
        return {"country": None, "country_qid": None}
    for city in capitals:
        if city.get("country") == country:
            return {"country": country, "country_qid": city.get("country_qid")}
    return {"country": country, "country_qid": None}


def city_marker_id(city: dict[str, Any]) -> str:
    """Return a stable UI identifier even when a city lacks a Wikidata QID."""
    qid = str(city.get("qid") or "").strip()
    if qid:
        return qid
    name, country = _normal_city_key(city)
    return f"local:{country}:{name}"


def _normal_city_key(city: dict[str, Any]) -> tuple[str, str]:
    """Return a fallback duplicate key for city/country pairs."""
    return (str(city.get("name") or "").casefold().strip(), str(city.get("country") or "").casefold().strip())


def load_preloaded_capitals() -> list[dict[str, Any]]:
    """Load locally bundled country-capital records without touching the network."""
    capitals = read_json(PRELOADED_CAPITALS, default=[])
    if not isinstance(capitals, list):
        return []
    normalized: list[dict[str, Any]] = []
    for city in capitals:
        if not isinstance(city, dict):
            continue
        item = dict(city)
        item.setdefault("source", "preloaded_capitals")
        item.setdefault("extraction_status", "preloaded metadata; select city to parse Wikipedia climate table")
        item.setdefault("climate_data", [])
        item["marker_id"] = city_marker_id(item)
        # The UI treats region as the continent selector.  Keep both keys for
        # compatibility with older city records and newer labels.
        if item.get("region") and not item.get("continent"):
            item["continent"] = item["region"]
        if item.get("continent") and not item.get("region"):
            item["region"] = item["continent"]
        normalized.append(item)
    return normalized


def _merge_missing_fields(preferred: dict[str, Any], supplement: dict[str, Any]) -> dict[str, Any]:
    """Preserve the preferred record while filling useful blank metadata."""
    merged = dict(preferred)
    for key, value in supplement.items():
        if key == "source":
            continue
        current = merged.get(key)
        if current in (None, "", [], {}) and value not in (None, "", [], {}):
            merged[key] = value
    merged.setdefault("marker_id", city_marker_id(merged))
    return merged


def merge_city_datasets(capitals: list[dict[str, Any]], additional: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge capital and optional city records, preferring capital metadata on duplicates."""
    merged: list[dict[str, Any]] = []
    qid_to_index: dict[str, int] = {}
    name_to_index: dict[tuple[str, str], int] = {}

    for city in [*capitals, *additional]:
        qid = str(city.get("qid") or "").strip()
        name_key = _normal_city_key(city)
        duplicate_index = qid_to_index.get(qid) if qid else None
        if duplicate_index is None:
            duplicate_index = name_to_index.get(name_key)
        if duplicate_index is not None:
            merged[duplicate_index] = _merge_missing_fields(merged[duplicate_index], city)
            continue
        item = dict(city)
        item.setdefault("marker_id", city_marker_id(item))
        index = len(merged)
        merged.append(item)
        if qid:
            qid_to_index[qid] = index
        name_to_index[name_key] = index
    return merged
