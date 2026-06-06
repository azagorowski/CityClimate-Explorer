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

from src.climate_parser import parse_climate_classification
from src.config import CAPITAL_CLIMATE_CACHE, PRELOADED_CAPITALS
from src.storage import read_json
from src.wikipedia import _native_article_reference, fetch_article


def _metadata(city: dict[str, Any], article: dict[str, Any] | None, priority: str, note: str | None = None) -> dict[str, Any]:
    language = article.get("language") if article else None
    return {
        "qid": city.get("qid"),
        "name": city.get("name"),
        "country": city.get("country"),
        "source_name": ("English Wikipedia" if language == "en" else "Wikipedia") if article else ("Wikidata" if priority == "wikidata_fallback" else "Local capital climate cache"),
        "source_language": language or ("multilingual" if priority == "wikidata_fallback" else None),
        "source_page_title": article.get("title") if article else city.get("qid"),
        "source_url": article.get("url") if article else (f"https://www.wikidata.org/wiki/{city['qid']}" if city.get("qid") and priority == "wikidata_fallback" else None),
        "source_priority": priority,
        "source_note": note,
    }


def build_record(city: dict[str, Any], force: bool = False) -> dict[str, Any]:
    """Resolve English Wikipedia, native Wikipedia, then bundled Wikidata fallback."""
    candidates: list[tuple[str, str, str]] = []
    if city.get("wikipedia_title"):
        candidates.append(("en", str(city["wikipedia_title"]), "english_primary"))
    native = _native_article_reference(city)
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
                return record
        except Exception as exc:  # continue through documented fallbacks
            errors.append(f"{language}:{title}: {exc}")
    fallback = city.get("wikidata_climate_classification") or city.get("climate_classification")
    fallback_label = city.get("wikidata_climate_classification_label") or city.get("climate_classification_label")
    if fallback or fallback_label:
        record = _metadata(city, None, "wikidata_fallback")
        record["climate_classification"] = fallback or fallback_label
        record["climate_classification_label"] = fallback_label or fallback
        return record
    note = "No usable Wikipedia classification or Wikidata fallback was found."
    if errors:
        note += " Fetch errors: " + " | ".join(errors)
    record = _metadata(city, None, "unavailable", note)
    record["climate_classification"] = "Unknown"
    record["climate_classification_label"] = "Unknown"
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Ignore cached Wikipedia articles.")
    parser.add_argument("--limit", type=int, help="Developer smoke-test limit; omit to refresh every capital.")
    args = parser.parse_args()
    capitals = read_json(PRELOADED_CAPITALS, default=[])
    if args.limit:
        capitals = capitals[: args.limit]
    records = [build_record(dict(city), force=args.force) for city in capitals]
    payload = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(), "records": records}
    CAPITAL_CLIMATE_CACHE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} capital climate records to {CAPITAL_CLIMATE_CACHE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
