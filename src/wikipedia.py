"""Wikipedia/MediaWiki fetching and city climate enrichment."""
from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import quote

import requests

from .climate_parser import parse_climate_data
from .config import BACKOFF_SECONDS, CLIMATE_CACHE_DIR, MAX_RETRIES, REQUEST_TIMEOUT, USER_AGENT, WIKIPEDIA_CACHE_DIR
from .storage import cache_key, read_json, write_json

LOGGER = logging.getLogger(__name__)
API_URL = "https://en.wikipedia.org/w/api.php"


def fetch_article(title: str, force_refresh: bool = False) -> dict[str, Any]:
    """Fetch article wikitext and rendered HTML from English Wikipedia with cache."""
    key = cache_key(title)
    path = WIKIPEDIA_CACHE_DIR / f"{key}.json"
    if not force_refresh:
        cached = read_json(path)
        if cached:
            return cached
    headers = {"User-Agent": USER_AGENT}
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext|text",
        "format": "json",
        "formatversion": 2,
        "redirects": 1,
    }
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(API_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise RuntimeError(data["error"].get("info", data["error"]))
            parsed = data.get("parse", {})
            article = {
                "title": parsed.get("title", title),
                "wikitext": parsed.get("wikitext", ""),
                "html": parsed.get("text", ""),
                "url": f"https://en.wikipedia.org/wiki/{quote(parsed.get('title', title).replace(' ', '_'))}",
            }
            write_json(path, article)
            return article
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            LOGGER.warning("Wikipedia request for %s attempt %s failed: %s", title, attempt, exc)
            time.sleep(BACKOFF_SECONDS * attempt)
    raise RuntimeError(f"Wikipedia fetch failed for {title}: {last_error}")


def enrich_city_climate(city: dict[str, Any], force_refresh: bool = False) -> dict[str, Any]:
    """Return a city record with parsed Wikipedia climate data attached."""
    enriched = dict(city)
    title = enriched.get("wikipedia_title")
    if not title:
        enriched.update({"extraction_status": "missing English Wikipedia sitelink", "climate_data": []})
        return enriched
    path = CLIMATE_CACHE_DIR / f"{cache_key(enriched.get('qid') or title)}.json"
    if not force_refresh:
        cached = read_json(path)
        if cached:
            return cached
    try:
        article = fetch_article(title, force_refresh=force_refresh)
        source_url = article.get("url") or enriched.get("wikipedia_url")
        climate_data, status = parse_climate_data(article.get("wikitext", ""), article.get("html", ""), source_url)
        enriched.update({
            "wikipedia_title": article.get("title", title),
            "wikipedia_url": source_url,
            "extraction_status": status,
            "climate_data": climate_data,
        })
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Climate extraction failed for %s", title)
        enriched.update({"extraction_status": f"error: {exc}", "climate_data": []})
    write_json(path, enriched)
    return enriched
