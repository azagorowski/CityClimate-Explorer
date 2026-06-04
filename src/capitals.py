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


def merge_city_datasets(capitals: list[dict[str, Any]], additional: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge capital and optional city records, preferring capital metadata on duplicates."""
    merged: list[dict[str, Any]] = []
    seen_qids: set[str] = set()
    seen_names: set[tuple[str, str]] = set()

    for city in [*capitals, *additional]:
        qid = str(city.get("qid") or "").strip()
        name_key = _normal_city_key(city)
        if qid and qid in seen_qids:
            continue
        if name_key in seen_names:
            continue
        if qid:
            seen_qids.add(qid)
        seen_names.add(name_key)
        item = dict(city)
        item.setdefault("marker_id", city_marker_id(item))
        merged.append(item)
    return merged
