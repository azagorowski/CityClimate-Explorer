"""Wikipedia/MediaWiki fetching and city climate enrichment."""
from __future__ import annotations

import logging
import re
import time
from typing import Any
from urllib.parse import quote, unquote

import requests

from .climate_parser import parse_climate_classification, parse_climate_data
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


def _language_from_wikipedia_url(url: str | None) -> str | None:
    if not url:
        return None
    match = re.match(r"https?://([a-z-]+)\.wikipedia\.org/", url)
    return match.group(1) if match else None


def _api_url(language: str) -> str:
    return f"https://{language}.wikipedia.org/w/api.php"


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
    params = {"action": "wbgetentities", "ids": qid, "props": "sitelinks", "sitefilter": "enwiki", "format": "json"}
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
    # Bundled capitals and optional Wikidata rows carry the English sitelink
    # resolved when the record was created. Prefer it to avoid a redundant
    # Wikidata request before the on-demand article fetch.
    local_title = city.get("wikipedia_title") or _title_from_wikipedia_url(city.get("wikipedia_url"))
    if local_title:
        return unquote(str(local_title)).replace("_", " ")
    qid = str(city.get("qid") or "").strip()
    if qid:
        try:
            title = fetch_enwiki_title_for_qid(qid, force_refresh=force_refresh)
            if title:
                return title
        except Exception as exc:  # noqa: BLE001 - fall through to safe title search
            LOGGER.warning("Could not resolve English Wikipedia sitelink for %s: %s", qid, exc)
    try:
        return lookup_article_title(str(city.get("name") or ""), city.get("country"), force_refresh=force_refresh)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Could not resolve Wikipedia title for %s, %s: %s", city.get("name"), city.get("country"), exc)
        return None


def resolve_native_article(city: dict[str, Any]) -> tuple[str, str] | None:
    """Return a native-language Wikipedia title only for fallback parsing."""
    lang = city.get("native_wikipedia_language") or city.get("wikipedia_language") or _language_from_wikipedia_url(city.get("native_wikipedia_url"))
    title = city.get("native_wikipedia_title") or _title_from_wikipedia_url(city.get("native_wikipedia_url"))
    if lang and lang != "en" and title:
        return str(lang), str(title)
    return None


def fetch_article(title: str, force_refresh: bool = False, language: str = "en") -> dict[str, Any]:
    """Fetch article wikitext and rendered HTML from Wikipedia with cache."""
    safe_language = language or "en"
    key = cache_key(f"{safe_language}:{title}")
    path = WIKIPEDIA_CACHE_DIR / f"{key}.json"
    if not force_refresh:
        cached = read_json(path)
        if cached:
            return cached
    params = {"action": "parse", "page": title, "prop": "wikitext|text|categories|properties", "format": "json", "formatversion": 2, "redirects": 1}
    data = _request_json(_api_url(safe_language), params, log_label=f"{safe_language} Wikipedia request for {title}")
    if "error" in data:
        raise RuntimeError(data["error"].get("info", data["error"]))
    parsed = data.get("parse", {})
    resolved_title = parsed.get("title", title)
    categories = {
        str(item.get("category") or item.get("*") or "").casefold() if isinstance(item, dict) else str(item).casefold()
        for item in parsed.get("categories", [])
    }
    properties = {
        str(item.get("name") or item.get("*") or "").casefold() if isinstance(item, dict) else str(item).casefold()
        for item in parsed.get("properties", [])
    }
    if "disambiguation pages" in categories or "disambiguation" in properties:
        raise RuntimeError(f"Wikipedia title {resolved_title!r} is a disambiguation page")
    article = {
        "language": safe_language,
        "title": resolved_title,
        "wikitext": parsed.get("wikitext", ""),
        "html": parsed.get("text", ""),
        "url": f"https://{safe_language}.wikipedia.org/wiki/{quote(resolved_title.replace(' ', '_'))}",
    }
    write_json(path, article)
    return article



def _fetch_article(title: str, force_refresh: bool, language: str) -> dict[str, Any]:
    """Call fetch_article with backward-compatible monkeypatch support in tests."""
    try:
        return fetch_article(title, force_refresh=force_refresh, language=language)
    except TypeError as exc:
        if "language" not in str(exc):
            raise
        article = fetch_article(title, force_refresh=force_refresh)
        article.setdefault("language", language)
        return article


def _fallback_classification(city: dict[str, Any]) -> tuple[str | None, str | None, str]:
    classification = city.get("wikidata_climate_classification") or city.get("climate_classification")
    label = city.get("wikidata_climate_classification_label") or city.get("climate_classification_label")
    if classification or label:
        return classification, label, "wikidata_fallback"
    return None, None, "unavailable"


def _article_source_metadata(article: dict[str, Any], role: str) -> dict[str, Any]:
    language = article.get("language", "en")
    return {
        "source_name": "English Wikipedia" if language == "en" else "Wikipedia",
        "source_language": language,
        "source_page_title": article.get("title"),
        "source_url": article.get("url"),
        "source_role": role,
    }


def _apply_classification(enriched: dict[str, Any], articles: list[tuple[dict[str, Any], str]]) -> None:
    """Apply Wikipedia classification first, then a labeled Wikidata fallback."""
    for article, role in articles:
        parsed = parse_climate_classification(article.get("wikitext", ""), article.get("html", ""))
        if not parsed:
            continue
        enriched["climate_classification"] = parsed.get("code") or parsed.get("description")
        enriched["climate_classification_label"] = parsed.get("description") or parsed.get("code")
        enriched["climate_classification_source"] = "wikipedia_primary" if article.get("language") == "en" else "wikipedia_native_fallback"
        enriched["climate_classification_source_metadata"] = _article_source_metadata(article, role)
        return
    classification, label, source = _fallback_classification(enriched)
    enriched["climate_classification"] = classification
    enriched["climate_classification_label"] = label
    enriched["climate_classification_source"] = source
    enriched["climate_classification_source_metadata"] = (
        {
            "source_name": "Wikidata",
            "source_language": "multilingual",
            "source_page_title": enriched.get("qid"),
            "source_url": f"https://www.wikidata.org/wiki/{enriched.get('qid')}" if enriched.get("qid") else None,
            "source_role": "wikidata_fallback",
        }
        if source == "wikidata_fallback"
        else None
    )


def _source_metadata(article: dict[str, Any], priority: str) -> dict[str, Any]:
    metadata = _article_source_metadata(article, priority)
    return {
        "climate_source_name": metadata["source_name"],
        "climate_source_language": metadata["source_language"],
        "climate_source_title": metadata["source_page_title"],
        "climate_source_url": metadata["source_url"],
        "climate_source_priority": priority,
        "climate_table_source_metadata": metadata,
    }


def _parse_article_for_climate(article: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    return parse_climate_data(article.get("wikitext", ""), article.get("html", ""), article.get("url"))


def enrich_city_climate(city: dict[str, Any], force_refresh: bool = False) -> dict[str, Any]:
    """Fetch and parse climate details on demand, always trying English first."""
    enriched = dict(city)
    cache_basis = enriched.get("qid") or enriched.get("wikipedia_title") or f"{enriched.get('name')}:{enriched.get('country')}"
    path = CLIMATE_CACHE_DIR / f"{cache_key(str(cache_basis))}.json"
    if not force_refresh:
        cached = read_json(path)
        if cached:
            LOGGER.info("Climate cache hit for %s, %s", enriched.get("name"), enriched.get("country"))
            return cached

    LOGGER.info(
        "Selected city: %s, %s (qid=%s); beginning English-first climate lookup",
        enriched.get("name"), enriched.get("country"), enriched.get("qid") or "none",
    )
    english_article: dict[str, Any] | None = None
    native_article: dict[str, Any] | None = None
    used_article: dict[str, Any] | None = None
    climate_data: list[dict[str, Any]] = []
    status = "missing English Wikipedia article"
    priority = "english_primary"

    title = resolve_city_article_title(enriched, force_refresh=force_refresh)
    LOGGER.info("English Wikipedia attempted for %s using title %r", enriched.get("name"), title)
    if title:
        try:
            english_article = _fetch_article(title, force_refresh, "en")
            LOGGER.info("English Wikipedia page used: %s", english_article.get("url"))
            climate_data, status = _parse_article_for_climate(english_article)
            used_article = english_article
            LOGGER.info("English climate table found=%s for %s (status=%s)", bool(climate_data), enriched.get("name"), status)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("English Wikipedia parsing failed for %s: %s", title, exc)
            status = f"English Wikipedia unavailable: {type(exc).__name__}"

    if not climate_data:
        native = resolve_native_article(enriched)
        LOGGER.info("Native-language Wikipedia fallback considered for %s: %s", enriched.get("name"), native or "not configured")
        if native:
            native_language, native_title = native
            try:
                native_article = _fetch_article(native_title, force_refresh, native_language)
                native_data, native_status = _parse_article_for_climate(native_article)
                LOGGER.info("Native fallback page %s climate table found=%s (status=%s)", native_article.get("url"), bool(native_data), native_status)
                if native_data:
                    climate_data = native_data
                    status = native_status
                    used_article = native_article
                    priority = "native_fallback"
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Native-language Wikipedia fallback failed for %s:%s: %s", native_language, native_title, exc)

    if used_article:
        enriched.update(_source_metadata(used_article, priority))
        if used_article.get("language") == "en":
            enriched["wikipedia_title"] = used_article.get("title")
            enriched["wikipedia_url"] = used_article.get("url")
    else:
        enriched.update({
            "climate_source_name": None,
            "climate_source_language": None,
            "climate_source_title": None,
            "climate_source_url": None,
            "climate_source_priority": "unavailable",
            "climate_table_source_metadata": None,
        })

    classification_articles: list[tuple[dict[str, Any], str]] = []
    if english_article:
        classification_articles.append((english_article, "english_primary"))
    if native_article:
        classification_articles.append((native_article, "native_fallback"))
    _apply_classification(enriched, classification_articles)
    if not climate_data:
        LOGGER.info("No supported climate table found for %s after all Wikipedia attempts", enriched.get("name"))
    if enriched.get("climate_classification_source") == "wikidata_fallback":
        LOGGER.info("Wikidata climate classification used as fallback for %s", enriched.get("name"))
    elif enriched.get("climate_classification_source") == "unavailable":
        LOGGER.info("Climate classification parsing failed for %s after all supported sources", enriched.get("name"))
    enriched.update({"extraction_status": status, "climate_data": climate_data})
    write_json(path, enriched)
    return enriched
