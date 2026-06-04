"""Wikidata acquisition for populated cities and settlements."""
from __future__ import annotations

import logging
import random
import time
from typing import Any

import requests

from .config import (
    DEFAULT_SAMPLE_LIMIT,
    USER_AGENT,
    WIKIDATA_BACKOFF_BASE_SECONDS,
    WIKIDATA_CACHE,
    WIKIDATA_MAX_RETRIES,
    WIKIDATA_QUERY_PAGE_SIZE,
    WIKIDATA_REQUEST_TIMEOUT,
    WIKIDATA_SPARQL_URL,
    WIKIDATA_TRANSIENT_STATUS_CODES,
)
from .storage import read_json, write_json

LOGGER = logging.getLogger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update({"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT})

# Populated-place classes that should be eligible for display.  The query uses
# subclasses of these classes so that local Wikidata types such as "big city" or
# country-specific municipality classes can still be included.
CITY_LIKE_CLASS_QIDS = {
    "Q515",  # city
    "Q3957",  # town
    "Q486972",  # human settlement
    "Q15284",  # municipality
    "Q1549591",  # big city
    "Q747074",  # commune of France / local commune-like municipalities
}

# Broad political/geographic entities are explicitly excluded in SPARQL and
# checked again in Python.  This prevents countries, continents, states,
# provinces, and administrative regions from becoming selectable map markers even
# when they have population and coordinate statements.
NON_CITY_DIRECT_TYPE_QIDS = {
    "Q6256",  # country
    "Q3624078",  # sovereign state
    "Q3024240",  # historical country
    "Q5107",  # continent
    "Q82794",  # geographic region
    "Q56061",  # administrative territorial entity (generic/broad)
    "Q3455524",  # administrative region
    "Q108640",  # first-level administrative country subdivision
    "Q13220204",  # second-level administrative country subdivision
    "Q34876",  # province
    "Q35657",  # U.S. state / federated state
    "Q7275",  # state
    "Q37057",  # sovereign state-like territorial entity
}


class WikidataRequestError(RuntimeError):
    """Raised when Wikidata cannot be reached after retrying transient failures."""


def _is_transient_http_error(exc: requests.HTTPError) -> bool:
    response = exc.response
    return response is not None and response.status_code in WIKIDATA_TRANSIENT_STATUS_CODES


def _backoff_delay(attempt: int) -> float:
    """Return exponential backoff delay with jitter for a 1-indexed attempt."""
    exponential = WIKIDATA_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
    jitter = random.uniform(0, WIKIDATA_BACKOFF_BASE_SECONDS)
    return exponential + jitter


def _request_with_retries(params: dict[str, Any]) -> dict[str, Any]:
    """Request Wikidata with retries for transient network and HTTP failures."""
    last_error: Exception | None = None
    for attempt in range(1, WIKIDATA_MAX_RETRIES + 1):
        try:
            response = _SESSION.get(WIKIDATA_SPARQL_URL, params=params, timeout=WIKIDATA_REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_error = exc
            LOGGER.warning("Transient Wikidata request attempt %s/%s failed: %s", attempt, WIKIDATA_MAX_RETRIES, exc)
        except requests.HTTPError as exc:
            last_error = exc
            status = exc.response.status_code if exc.response is not None else "unknown"
            if not _is_transient_http_error(exc):
                raise WikidataRequestError(f"Wikidata request failed with non-retryable HTTP status {status}: {exc}") from exc
            LOGGER.warning(
                "Transient Wikidata HTTP status %s on attempt %s/%s: %s",
                status,
                attempt,
                WIKIDATA_MAX_RETRIES,
                exc,
            )
        except requests.RequestException as exc:
            raise WikidataRequestError(f"Wikidata request failed with a non-retryable requests error: {exc}") from exc

        if attempt < WIKIDATA_MAX_RETRIES:
            time.sleep(_backoff_delay(attempt))

    raise WikidataRequestError(f"Wikidata request failed after {WIKIDATA_MAX_RETRIES} attempts: {last_error}")


def build_city_query(limit: int = DEFAULT_SAMPLE_LIMIT, min_population: int = 50_000, offset: int = 0) -> str:
    """Build a bounded SPARQL query for city/human-settlement entities."""
    safe_limit = max(1, min(int(limit), WIKIDATA_QUERY_PAGE_SIZE))
    safe_min_population = max(1, int(min_population))
    safe_offset = max(0, int(offset))
    return f"""
SELECT ?city ?cityLabel ?countryLabel ?population ?coord ?article ?climate ?climateLabel
       (GROUP_CONCAT(DISTINCT ?instanceOfQid; separator=",") AS ?instanceOfQids)
       (GROUP_CONCAT(DISTINCT ?instanceOfLabel; separator="|") AS ?instanceOfLabels)
WHERE {{
  VALUES ?settlementType {{ wd:Q515 wd:Q3957 wd:Q486972 wd:Q15284 wd:Q1549591 wd:Q747074 }}
  VALUES ?excludedType {{ wd:Q6256 wd:Q3624078 wd:Q3024240 wd:Q5107 wd:Q82794 wd:Q3455524 wd:Q108640 wd:Q13220204 wd:Q34876 wd:Q35657 wd:Q7275 wd:Q37057 }}

  ?city wdt:P31 ?instanceOf;
        wdt:P31/wdt:P279* ?settlementType;
        wdt:P1082 ?population;
        wdt:P625 ?coord;
        wdt:P17 ?country.

  # Countries, continents, states/provinces, and administrative regions often
  # have population and coordinates, but they are not city markers.  Excluding
  # broad political/geographic classes here keeps the query focused and the
  # Python validation below repeats this defensively for cached/tested data.
  FILTER NOT EXISTS {{ ?city wdt:P31/wdt:P279* ?excludedType. }}
  FILTER(?population >= {safe_min_population})
  BIND(STRAFTER(STR(?instanceOf), "entity/") AS ?instanceOfQid)

  OPTIONAL {{ ?city wdt:P2564 ?climate. }}
  OPTIONAL {{
    ?article schema:about ?city;
             schema:isPartOf <https://en.wikipedia.org/>.
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?city ?cityLabel ?countryLabel ?population ?coord ?article ?climate ?climateLabel
ORDER BY DESC(?population)
LIMIT {safe_limit}
OFFSET {safe_offset}
"""


def _parse_point(point: str) -> tuple[float | None, float | None]:
    if not point.startswith("Point("):
        return None, None
    lon_lat = point.removeprefix("Point(").removesuffix(")").split()
    if len(lon_lat) != 2:
        return None, None
    return float(lon_lat[1]), float(lon_lat[0])


def _qid_from_uri(value: str) -> str:
    return value.rsplit("/", 1)[-1] if value else ""


def _parse_type_qids(row: dict[str, Any]) -> set[str]:
    qids = row.get("instanceOfQids", {}).get("value", "")
    return {qid for qid in qids.split(",") if qid}


def _is_city_like_row(row: dict[str, Any], lat: float | None, lon: float | None) -> bool:
    """Defensively discard countries, regions, and malformed place rows."""
    qid = _qid_from_uri(row.get("city", {}).get("value", ""))
    type_qids = _parse_type_qids(row)
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        LOGGER.debug("Discarding %s because it lacks valid city-like coordinates", qid)
        return False
    try:
        population = int(float(row.get("population", {}).get("value", 0)))
    except (TypeError, ValueError):
        LOGGER.debug("Discarding %s because it lacks numeric population", qid)
        return False
    if population <= 0:
        LOGGER.debug("Discarding %s because it lacks positive population", qid)
        return False
    if type_qids & NON_CITY_DIRECT_TYPE_QIDS:
        LOGGER.info("Discarding non-city Wikidata entity %s with types %s", qid, sorted(type_qids))
        return False
    return True


def _rows_to_cities(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cities: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        lat, lon = _parse_point(row.get("coord", {}).get("value", ""))
        if not _is_city_like_row(row, lat, lon):
            continue
        qid = _qid_from_uri(row.get("city", {}).get("value", ""))
        if qid in seen:
            continue
        seen.add(qid)
        article_url = row.get("article", {}).get("value")
        wikipedia_title = article_url.rsplit("/wiki/", 1)[-1].replace("_", " ") if article_url else None
        cities.append({
            "qid": qid,
            "name": row.get("cityLabel", {}).get("value"),
            "country": row.get("countryLabel", {}).get("value"),
            "population": int(float(row.get("population", {}).get("value", 0))),
            "latitude": lat,
            "longitude": lon,
            "wikipedia_title": wikipedia_title,
            "wikipedia_url": article_url,
            "wikidata_instance_of_qids": sorted(_parse_type_qids(row)),
            "wikidata_instance_of_labels": row.get("instanceOfLabels", {}).get("value"),
            "climate_classification": row.get("climate", {}).get("value", "").rsplit("/", 1)[-1] or None,
            "climate_classification_label": row.get("climateLabel", {}).get("value"),
        })
    return cities


def _fallback_cached_cities(cache: dict[str, Any], cache_id: str, min_population: int) -> list[dict[str, Any]]:
    if cache_id in cache:
        return cache[cache_id]
    candidates = [city for batch in cache.values() if isinstance(batch, list) for city in batch]
    deduped: dict[str, dict[str, Any]] = {}
    for city in candidates:
        if city.get("population", 0) >= min_population and city.get("qid"):
            deduped[city["qid"]] = city
    return sorted(deduped.values(), key=lambda city: city.get("population", 0), reverse=True)


def fetch_cities(limit: int = DEFAULT_SAMPLE_LIMIT, min_population: int = 50_000, force_refresh: bool = False) -> list[dict[str, Any]]:
    """Fetch or load cached cities from Wikidata."""
    cache = read_json(WIKIDATA_CACHE, default={}) or {}
    cache_id = f"limit={limit};min_population={min_population}"
    if not force_refresh and cache_id in cache:
        return cache[cache_id]

    LOGGER.info("Fetching %s cities with population >= %s from Wikidata", limit, min_population)
    rows: list[dict[str, Any]] = []
    try:
        for offset in range(0, max(0, int(limit)), WIKIDATA_QUERY_PAGE_SIZE):
            page_limit = min(WIKIDATA_QUERY_PAGE_SIZE, int(limit) - offset)
            raw = _request_with_retries({"query": build_city_query(page_limit, min_population, offset), "format": "json"})
            page_rows = raw.get("results", {}).get("bindings", [])
            rows.extend(page_rows)
            if len(page_rows) < page_limit:
                break
    except WikidataRequestError:
        fallback = _fallback_cached_cities(cache, cache_id, min_population)[:limit]
        if fallback:
            LOGGER.warning("Using %s stale cached cities after Wikidata request failure", len(fallback), exc_info=True)
            return fallback
        raise

    cities = _rows_to_cities(rows)[:limit]
    cache[cache_id] = cities
    write_json(WIKIDATA_CACHE, cache)
    return cities
