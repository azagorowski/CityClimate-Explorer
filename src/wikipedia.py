"""Wikipedia/MediaWiki fetching and city climate enrichment."""
from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import quote, unquote

import requests

from .climate_parser import parse_climate_data
from .config import BACKOFF_SECONDS, CLIMATE_CACHE_DIR, MAX_RETRIES, REQUEST_TIMEOUT, USER_AGENT, WIKIPEDIA_CACHE_DIR
from .storage import cache_key, read_json, write_json

LOGGER = logging.getLogger(__name__)
API_URL = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"

DISAMBIGUATED_TITLES = {
    ("bratislava", "slovakia"): "Bratislava",
    ("budapest", "hungary"): "Budapest",
    ("luxembourg", "luxembourg"): "Luxembourg City",
    ("luxembourg city", "luxembourg"): "Luxembourg City",
    ("mexico city", "mexico"): "Mexico City",
    ("panama city", "panama"): "Panama City",
    ("kuwait city", "kuwait"): "Kuwait City",
    ("guatemala city", "guatemala"): "Guatemala City",
}


def _request_json(url: str, params: dict[str, Any], *, log_label: str) -> dict[str, Any]:
    headers = {"User-Agent": USER_AGENT}
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            LOGGER.warning("%s attempt %s/%s failed: %s", log_label, attempt, MAX_RETRIES, exc)
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_SECONDS * attempt)
    raise RuntimeError(f"{log_label} failed after {MAX_RETRIES} attempts: {last_error}")


def _title_from_wikipedia_url(url: str | None) -> str | None:
    if not url or "/wiki/" not in url:
        return None
    return unquote(url.rsplit("/wiki/", 1)[-1]).replace("_", " ") or None


def fetch_enwiki_title_for_qid(qid: str, force_refresh: bool = False) -> str | None:
    """Resolve a Wikidata entity to its English Wikipedia title using the sitelink."""
    if not qid:
        return None
    key = f"wikidata-sitelink-{cache_key(qid)}"
    path = WIKIPEDIA_CACHE_DIR / f"{key}.json"
    if not force_refresh:
        cached = read_json(path)
        if cached:
            return cached.get("title")
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "props": "sitelinks",
        "sitefilter": "enwiki",
        "format": "json",
    }
    data = _request_json(WIKIDATA_API_URL, params, log_label=f"Wikidata sitelink lookup for {qid}")
    title = data.get("entities", {}).get(qid, {}).get("sitelinks", {}).get("enwiki", {}).get("title")
    if title:
        write_json(path, {"qid": qid, "title": title})
        LOGGER.debug("Resolved %s to English Wikipedia title %s", qid, title)
    else:
        LOGGER.info("No English Wikipedia sitelink found for %s", qid)
    return title


def lookup_article_title(city_name: str, country: str | None = None, force_refresh: bool = False) -> str | None:
    """Safely resolve a city/country label to an English Wikipedia article title."""
    if not city_name:
        return None
    override = DISAMBIGUATED_TITLES.get((city_name.casefold().strip(), (country or "").casefold().strip()))
    if override:
        return override
    query = f"{city_name} {country}".strip() if country else city_name
    key = f"title-lookup-{cache_key(query)}"
    path = WIKIPEDIA_CACHE_DIR / f"{key}.json"
    if not force_refresh:
        cached = read_json(path)
        if cached:
            return cached.get("title")
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 0,
        "gsrlimit": 3,
        "prop": "info",
        "inprop": "url",
        "redirects": 1,
        "format": "json",
        "formatversion": 2,
    }
    data = _request_json(API_URL, params, log_label=f"Wikipedia title lookup for {query}")
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        LOGGER.info("No English Wikipedia title candidates found for %s", query)
        return None
    city_key = city_name.casefold().strip()
    title = next((page.get("title") for page in pages if str(page.get("title", "")).casefold() == city_key), None)
    title = title or pages[0].get("title")
    if title:
        write_json(path, {"query": query, "title": title})
        LOGGER.debug("Resolved %s to English Wikipedia title %s", query, title)
    return title


def resolve_city_article_title(city: dict[str, Any], force_refresh: bool = False) -> str | None:
    """Choose the best English Wikipedia title for a city record."""
    qid = str(city.get("qid") or "").strip()
    if qid:
        try:
            title = fetch_enwiki_title_for_qid(qid, force_refresh=force_refresh)
            if title:
                return title
        except Exception as exc:  # noqa: BLE001 - fall through to local/fuzzy title
            LOGGER.warning("Could not resolve English Wikipedia sitelink for %s: %s", qid, exc)
    local_title = city.get("wikipedia_title") or _title_from_wikipedia_url(city.get("wikipedia_url"))
    if local_title:
        return str(local_title)
    try:
        return lookup_article_title(str(city.get("name") or ""), city.get("country"), force_refresh=force_refresh)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Could not resolve Wikipedia title for %s, %s: %s", city.get("name"), city.get("country"), exc)
        return None


def fetch_article(title: str, force_refresh: bool = False) -> dict[str, Any]:
    """Fetch article wikitext and rendered HTML from English Wikipedia with cache."""
    key = cache_key(title)
    path = WIKIPEDIA_CACHE_DIR / f"{key}.json"
    if not force_refresh:
        cached = read_json(path)
        if cached:
            return cached
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext|text",
        "format": "json",
        "formatversion": 2,
        "redirects": 1,
    }
    data = _request_json(API_URL, params, log_label=f"Wikipedia request for {title}")
    if "error" in data:
        raise RuntimeError(data["error"].get("info", data["error"]))
    parsed = data.get("parse", {})
    resolved_title = parsed.get("title", title)
    article = {
        "title": resolved_title,
        "wikitext": parsed.get("wikitext", ""),
        "html": parsed.get("text", ""),
        "url": f"https://en.wikipedia.org/wiki/{quote(resolved_title.replace(' ', '_'))}",
    }
    write_json(path, article)
    return article


def enrich_city_climate(city: dict[str, Any], force_refresh: bool = False) -> dict[str, Any]:
    """Return a city record with parsed Wikipedia climate data attached."""
    enriched = dict(city)
    title = resolve_city_article_title(enriched, force_refresh=force_refresh)
    if not title:
        LOGGER.info("Skipping climate extraction for %s because no English Wikipedia article could be resolved", enriched.get("name"))
        enriched.update({"extraction_status": "missing English Wikipedia article", "climate_data": []})
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
        if not climate_data:
            LOGGER.info("No supported climate table was found for %s on %s", enriched.get("name"), article.get("title", title))
            status = "no supported climate table found"
        enriched.update({
            "wikipedia_title": article.get("title", title),
            "wikipedia_url": source_url,
            "extraction_status": status,
            "climate_data": climate_data,
        })
        write_json(path, enriched)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Climate extraction failed for %s", title)
        enriched.update({"wikipedia_title": title, "extraction_status": f"climate extraction error: {exc}", "climate_data": []})
    return enriched
