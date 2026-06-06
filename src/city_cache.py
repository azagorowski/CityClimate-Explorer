"""Local precomputed climate and optional-city cache helpers."""
from __future__ import annotations

from typing import Any

from .capitals import city_marker_id, filter_optional_non_capital_cities
from .config import CAPITAL_CLIMATE_CACHE, OPTIONAL_CITY_CACHE
from .storage import read_json


def _cache_records(path: Any) -> list[dict[str, Any]]:
    payload = read_json(path, default={})
    records = payload.get("records", []) if isinstance(payload, dict) else payload
    return [dict(record) for record in records if isinstance(record, dict)] if isinstance(records, list) else []


def load_capital_climate_cache() -> list[dict[str, Any]]:
    """Load locally generated capital classifications without network access."""
    return _cache_records(CAPITAL_CLIMATE_CACHE)


def climate_cache_key(record: dict[str, Any]) -> tuple[str, ...]:
    """Prefer QID, then normalized city/country for cache joins."""
    qid = str(record.get("qid") or "").strip()
    if qid:
        return ("qid", qid)
    return (
        "name_country",
        str(record.get("name") or "").casefold().strip(),
        str(record.get("country") or "").casefold().strip(),
    )


def apply_capital_climate_cache(capitals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach a classification and source metadata to every startup capital."""
    cached = {climate_cache_key(record): record for record in load_capital_climate_cache()}
    enriched: list[dict[str, Any]] = []
    for capital in capitals:
        item = dict(capital)
        climate = cached.get(climate_cache_key(item), {})
        classification = climate.get("climate_classification") or "Unknown"
        label = climate.get("climate_classification_label") or classification
        priority = climate.get("source_priority") or "unavailable"
        metadata = {
            "source_name": climate.get("source_name") or "Local capital climate cache",
            "source_language": climate.get("source_language"),
            "source_page_title": climate.get("source_page_title"),
            "source_url": climate.get("source_url"),
            "source_priority": priority,
            "source_role": priority,
            "source_note": climate.get("source_note"),
            "retrieved_at": climate.get("retrieved_at"),
            "license": climate.get("license"),
            "license_url": climate.get("license_url"),
            "contributors_url": climate.get("contributors_url"),
            "attribution_notice": climate.get("attribution_notice"),
        }
        item.update(
            climate_classification=classification,
            climate_classification_label=label,
            climate_classification_source=priority,
            climate_classification_source_metadata=metadata,
            climate_source_priority=priority,
            extraction_status="preloaded climate classification; select city for monthly climate details",
        )
        item["marker_id"] = city_marker_id(item)
        enriched.append(item)
    return enriched


def load_optional_city_cache() -> list[dict[str, Any]]:
    """Load the bundled non-capital city cache without querying Wikidata."""
    return _cache_records(OPTIONAL_CITY_CACHE)


def available_optional_countries(continent: str | None) -> list[str]:
    """Return countries represented in the optional cache for a continent."""
    if not continent:
        return []
    return sorted({str(city["country"]) for city in load_optional_city_cache() if city.get("continent") == continent and city.get("country")})


def load_cached_optional_cities(
    capitals: list[dict[str, Any]], continent: str | None, country: str | None, limit: int = 10
) -> list[dict[str, Any]]:
    """Return population-ranked local non-capitals for an explicit selection."""
    if not continent:
        raise ValueError("A continent must be selected before loading additional cities.")
    if not country:
        raise ValueError("A country must be selected before loading additional cities.")
    candidates = [
        city for city in load_optional_city_cache()
        if city.get("continent") == continent and city.get("country") == country
    ]
    for city in candidates:
        # Preserve provenance and license metadata when adapting cached records.
        city.setdefault("region", city.get("continent"))
        city.setdefault("source", "local_optional_city_cache")
        city.setdefault("climate_classification", city.get("climate_type") or "Unknown")
        city.setdefault("climate_classification_label", city.get("climate_type") or "Unknown")
        metadata = city.get("climate_source_metadata") or {}
        city.setdefault("climate_classification_source", metadata.get("source_priority") or "unavailable")
        city.setdefault("climate_classification_source_metadata", metadata)
        city.setdefault("extraction_status", "preloaded optional-city metadata; select city for monthly climate details")
    return filter_optional_non_capital_cities(capitals, candidates, limit=min(10, max(0, int(limit))))
