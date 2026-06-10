"""Local precomputed capital-climate cache helpers."""
from __future__ import annotations

import logging
from typing import Any

from .capitals import city_marker_id
from .config import CAPITAL_CLIMATE_CACHE, CLIMATE_CLASSIFICATION_OVERRIDES
from .normalize import normalized_search_key
from .storage import read_json
from .map_view import climate_category

LOGGER = logging.getLogger(__name__)
CLIMATE_GROUPS = {"Tropical", "Dry / Arid", "Temperate", "Continental", "Polar", "Highland / Mountain", "Unknown"}


def _cache_records(path: Any) -> list[dict[str, Any]]:
    payload = read_json(path, default={})
    records = payload.get("records", []) if isinstance(payload, dict) else payload
    return [dict(record) for record in records if isinstance(record, dict)] if isinstance(records, list) else []


def load_capital_climate_cache() -> list[dict[str, Any]]:
    """Load locally generated capital classifications without network access."""
    return _cache_records(CAPITAL_CLIMATE_CACHE)


def _normalized_identity(value: Any) -> str:
    """Normalize names for resilient city/country fallback joins."""
    return normalized_search_key(value)


def climate_cache_key(record: dict[str, Any]) -> tuple[str, ...]:
    """Prefer QID, then normalized city/country for cache joins."""
    qid = str(record.get("qid") or "").strip()
    if qid:
        return ("qid", qid)
    return (
        "name_country",
        _normalized_identity(record.get("name")),
        _normalized_identity(record.get("country")),
    )


def _known(value: Any) -> bool:
    return value not in (None, "", "Unknown", "Unknown climate type")


def load_climate_classification_overrides() -> list[dict[str, Any]]:
    """Load documented, reviewed classification corrections from local data."""
    return _cache_records(CLIMATE_CLASSIFICATION_OVERRIDES)


def _override_for(record: dict[str, Any]) -> dict[str, Any] | None:
    qid = str(record.get("qid") or "").strip()
    fallback = (_normalized_identity(record.get("name")), _normalized_identity(record.get("country")))
    for override in load_climate_classification_overrides():
        override_qid = str(override.get("qid") or "").strip()
        if qid and override_qid and qid == override_qid:
            return override
        if fallback == (_normalized_identity(override.get("city")), _normalized_identity(override.get("country"))):
            return override
    return None


def apply_climate_classification_override(record: dict[str, Any]) -> dict[str, Any]:
    """Apply a verified correction while retaining complete source attribution."""
    item = dict(record)
    override = _override_for(item)
    if not override:
        return item
    classification = override["climate_classification"]
    source_url = override.get("source_url")
    metadata = {
        "source_name": "English Wikipedia" if override.get("source_language") == "en" else "Wikipedia",
        "source_language": override.get("source_language"),
        "source_page_title": override.get("source_page_title") or item.get("wikipedia_title") or item.get("name"),
        "source_url": source_url,
        "source_priority": "english_primary",
        "source_role": "verified correction after automatic source conflict",
        "source_note": override.get("reason"),
        "retrieved_at": override.get("date_added"),
        "license": override.get("license") or "CC BY-SA 4.0",
        "license_url": override.get("license_url") or "https://creativecommons.org/licenses/by-sa/4.0/",
        "contributors_url": f"{source_url}?action=history" if source_url else None,
        "attribution_notice": "See the source page history for contributor attribution.",
    }
    item.update(
        climate_classification=classification,
        climate_classification_label=classification,
        climate_group=override["climate_group"],
        primary_koppen_code=override.get("primary_koppen_code") or item.get("primary_koppen_code"),
        secondary_koppen_codes=override.get("secondary_koppen_codes", item.get("secondary_koppen_codes") or []),
        climate_classification_source="curated_english_override",
        classification_source_priority="curated_english_override",
        climate_source_priority="english_primary",
        climate_classification_source_metadata=metadata,
        climate_source_name=metadata["source_name"],
        climate_source_language=metadata["source_language"],
        climate_source_title=metadata["source_page_title"],
        climate_source_url=metadata["source_url"],
        climate_extraction_status="curated override applied after English Wikipedia review",
        extraction_status="curated override applied after English Wikipedia review",
    )
    return item


def apply_capital_climate_cache(capitals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach the best local classification without replacing known data by Unknown."""
    cache_records = load_capital_climate_cache()
    cached_by_qid = {
        str(record["qid"]).strip(): record for record in cache_records if str(record.get("qid") or "").strip()
    }
    cached_by_name_country = {
        ("name_country", _normalized_identity(record.get("name")), _normalized_identity(record.get("country"))): record
        for record in cache_records
    }
    enriched: list[dict[str, Any]] = []
    for capital in capitals:
        item = dict(capital)
        qid = str(item.get("qid") or "").strip()
        climate = cached_by_qid.get(qid) if qid else None
        climate = climate or cached_by_name_country.get(
            ("name_country", _normalized_identity(item.get("name")), _normalized_identity(item.get("country")))
        ) or {}
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
        if group not in CLIMATE_GROUPS or (group == "Unknown" and classification != "Unknown"):
            group = climate_category(str(label), str(classification))
        extraction_status = climate.get("extraction_status") or item.get("extraction_status") or "preloaded climate classification"
        item.update(
            climate_classification=classification, climate_classification_label=label, climate_group=group,
            primary_koppen_code=climate.get("primary_koppen_code") or item.get("primary_koppen_code"),
            secondary_koppen_codes=climate.get("secondary_koppen_codes") or item.get("secondary_koppen_codes") or [],
            climate_source_excerpt=climate.get("climate_source_excerpt") or item.get("climate_source_excerpt"),
            climate_classification_source=priority, climate_classification_source_metadata=metadata,
            climate_source_priority=priority,
            climate_source_name=metadata["source_name"], climate_source_language=metadata["source_language"],
            climate_source_title=metadata["source_page_title"], climate_source_url=metadata["source_url"],
            climate_extraction_status=extraction_status, extraction_status=extraction_status,
        )
        if classification == "Unknown":
            LOGGER.warning(
                "Unresolved startup climate for %s, %s (%s): %s",
                item.get("name"), item.get("country"), item.get("qid") or "no QID",
                metadata.get("source_note") or extraction_status,
            )
        item = apply_climate_classification_override(item)
        item["marker_id"] = city_marker_id(item)
        enriched.append(item)
    return enriched
