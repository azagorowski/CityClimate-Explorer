"""Local precomputed capital-climate cache helpers."""
from __future__ import annotations

from typing import Any

from .capitals import city_marker_id
from .config import CAPITAL_CLIMATE_CACHE
from .storage import read_json
from .map_view import climate_category


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


def _known(value: Any) -> bool:
    return value not in (None, "", "Unknown", "Unknown climate type")


def apply_capital_climate_cache(capitals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach the best local classification without replacing known data by Unknown."""
    cached = {climate_cache_key(record): record for record in load_capital_climate_cache()}
    enriched: list[dict[str, Any]] = []
    for capital in capitals:
        item = dict(capital)
        climate = cached.get(climate_cache_key(item), {})
        cached_classification = climate.get("climate_classification")
        cached_label = climate.get("climate_classification_label")
        classification = cached_classification if _known(cached_classification) else item.get("climate_classification")
        label = cached_label if _known(cached_label) else item.get("climate_classification_label")
        classification = classification if _known(classification) else label if _known(label) else "Unknown"
        label = label if _known(label) else classification
        use_cache_metadata = _known(cached_classification) or _known(cached_label)
        priority = climate.get("source_priority") if use_cache_metadata else item.get("climate_classification_source")
        priority = priority or ("wikidata_fallback" if classification != "Unknown" else "unavailable")
        metadata_source = climate if use_cache_metadata else item.get("climate_classification_source_metadata") or {}
        metadata = {
            "source_name": metadata_source.get("source_name") or ("Wikidata" if priority == "wikidata_fallback" else "Local capital climate cache"),
            "source_language": metadata_source.get("source_language") or ("multilingual" if priority == "wikidata_fallback" else None),
            "source_page_title": metadata_source.get("source_page_title") or item.get("qid"),
            "source_url": metadata_source.get("source_url"),
            "source_priority": priority, "source_role": priority,
            "source_note": metadata_source.get("source_note"),
            "retrieved_at": metadata_source.get("retrieved_at"),
            "license": metadata_source.get("license"),
            "license_url": metadata_source.get("license_url"),
            "contributors_url": metadata_source.get("contributors_url"),
            "attribution_notice": metadata_source.get("attribution_notice"),
        }
        group = climate.get("climate_group") if use_cache_metadata else item.get("climate_group")
        if group not in {"Tropical", "Dry / Arid", "Temperate", "Continental", "Polar", "Highland / Mountain", "Unknown"}:
            group = climate_category(str(label), str(classification))
        item.update(
            climate_classification=classification, climate_classification_label=label, climate_group=group,
            climate_classification_source=priority, climate_classification_source_metadata=metadata,
            climate_source_priority=priority,
            extraction_status=climate.get("extraction_status") or item.get("extraction_status") or "preloaded climate classification",
        )
        item["marker_id"] = city_marker_id(item)
        enriched.append(item)
    return enriched
