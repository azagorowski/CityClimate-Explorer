#!/usr/bin/env python3
"""Refresh the local startup classification cache from Wikimedia sources.

This developer/admin script is intentionally separate from the Streamlit runtime.
It fetches classification prose only; monthly climate tables remain on demand.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.climate_parser import parse_climate_classification  # noqa: E402
from src.config import (  # noqa: E402
    CAPITAL_CLIMATE_CACHE,
    PRELOADED_CAPITALS,
    WIKIDATA_LICENSE,
    WIKIDATA_LICENSE_URL,
    WIKIPEDIA_LICENSE,
    WIKIPEDIA_LICENSE_URL,
)
from src.storage import read_json  # noqa: E402
from src.map_view import climate_category  # noqa: E402
from src.wikipedia import fetch_article, resolve_native_article  # noqa: E402


def _metadata(city: dict[str, Any], article: dict[str, Any] | None, priority: str, note: str | None = None) -> dict[str, Any]:
    language = article.get("language") if article else None
    source_url = article.get("url") if article else (f"https://www.wikidata.org/wiki/{city['qid']}" if city.get("qid") and priority == "wikidata_fallback" else None)
    wikipedia_derived = priority in {"english_primary", "native_fallback"}
    wikidata_derived = priority == "wikidata_fallback"
    return {
        "qid": city.get("qid"),
        "name": city.get("name"),
        "country": city.get("country"),
        "source_name": ("English Wikipedia" if language == "en" else "Wikipedia") if article else ("Wikidata" if wikidata_derived else "Local capital climate cache"),
        "source_language": language or ("multilingual" if wikidata_derived else None),
        "source_page_title": article.get("title") if article else city.get("qid"),
        "source_url": source_url,
        "source_priority": priority,
        "source_note": note,
        "retrieved_at": article.get("retrieved_at") if article else None,
        "license": WIKIPEDIA_LICENSE if wikipedia_derived else (WIKIDATA_LICENSE if wikidata_derived else None),
        "license_url": WIKIPEDIA_LICENSE_URL if wikipedia_derived else (WIKIDATA_LICENSE_URL if wikidata_derived else None),
        "contributors_url": f"{source_url}?action=history" if wikipedia_derived and source_url else None,
        "attribution_notice": "See the source page history for contributor attribution." if wikipedia_derived else None,
    }


def build_record(city: dict[str, Any], force: bool = False) -> dict[str, Any]:
    """Resolve English Wikipedia, native Wikipedia, then bundled Wikidata fallback."""
    candidates: list[tuple[str, str, str]] = []
    if city.get("wikipedia_title"):
        candidates.append(("en", str(city["wikipedia_title"]), "english_primary"))
    native = resolve_native_article(city)
    if native:
        candidates.append((native[0], native[1], "native_fallback"))
    errors: list[str] = []
    for language, title, priority in candidates:
        try:
            article = fetch_article(title, force_refresh=force, language=language)
            parsed = parse_climate_classification(article.get("wikitext", ""), article.get("html", ""))
            if parsed:
                record = _metadata(city, article, priority)
                record["climate_classification"] = parsed.get("code") or parsed.get("description")
                record["climate_classification_label"] = parsed.get("description") or parsed.get("code")
                record["climate_group"] = climate_category(record["climate_classification_label"], record["climate_classification"])
                record["extraction_status"] = "parsed_climate_text"
                return record
        except Exception as exc:  # continue through documented fallbacks
            errors.append(f"{language}:{title}: {exc}")
    fallback = city.get("wikidata_climate_classification") or city.get("climate_classification")
    fallback_label = city.get("wikidata_climate_classification_label") or city.get("climate_classification_label")
    if fallback or fallback_label:
        record = _metadata(city, None, "wikidata_fallback")
        record["climate_classification"] = fallback or fallback_label
        record["climate_classification_label"] = fallback_label or fallback
        record["climate_group"] = climate_category(record["climate_classification_label"], record["climate_classification"])
        record["extraction_status"] = "fallback_wikidata"
        return record
    note = "No usable Wikipedia classification or Wikidata fallback was found."
    if errors:
        note += " Fetch errors: " + " | ".join(errors)
    record = _metadata(city, None, "unavailable", note)
    record["climate_classification"] = "Unknown"
    record["climate_classification_label"] = "Unknown"
    record["climate_group"] = "Unknown"
    record["extraction_status"] = "unavailable"
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Ignore cached Wikipedia articles.")
    parser.add_argument("--limit", type=int, help="Developer smoke-test limit; omit to refresh every capital.")
    args = parser.parse_args()
    capitals = read_json(PRELOADED_CAPITALS, default=[])
    if args.limit:
        capitals = capitals[: args.limit]
    existing_payload = read_json(CAPITAL_CLIMATE_CACHE, default={})
    existing_records = existing_payload.get("records", []) if isinstance(existing_payload, dict) else []
    existing_by_name_country = {
        (str(record.get("name")), str(record.get("country"))): record
        for record in existing_records if isinstance(record, dict)
    }
    refreshed: list[dict[str, Any]] = []
    refreshed_keys: set[tuple[str, str]] = set()
    for city in capitals:
        key = (str(city.get("name")), str(city.get("country")))
        record = build_record(dict(city), force=args.force)
        previous = existing_by_name_country.get(key)
        if record.get("climate_classification") == "Unknown" and previous and previous.get("climate_classification") != "Unknown":
            record = previous
        refreshed.append(record)
        refreshed_keys.add(key)
    # A smoke-test --limit refresh must not truncate the authoritative cache.
    records = refreshed + [
        record for key, record in existing_by_name_country.items() if key not in refreshed_keys
    ]
    # Do not strip source/license fields: redistributed Wikipedia-derived labels remain CC BY-SA.
    payload = {"schema_version": 3, "generated_at": datetime.now(timezone.utc).isoformat(), "records": records}
    CAPITAL_CLIMATE_CACHE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} capital climate records to {CAPITAL_CLIMATE_CACHE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
