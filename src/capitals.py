"""Preloaded country-capital dataset helpers."""
from __future__ import annotations

from typing import Any

from .config import PRELOADED_CAPITALS
from .storage import read_json

SUPPORTED_CONTINENTS = ("Africa", "Asia", "Europe", "North America", "South America", "Oceania")


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
        if not qid and name_key in seen_names:
            continue
        if qid:
            seen_qids.add(qid)
        seen_names.add(name_key)
        merged.append(city)
    return merged
