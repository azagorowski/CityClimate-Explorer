"""Wikidata acquisition for populated cities and settlements."""
from __future__ import annotations

import logging
import time
from typing import Any

import requests

from .config import BACKOFF_SECONDS, DEFAULT_SAMPLE_LIMIT, MAX_RETRIES, REQUEST_TIMEOUT, USER_AGENT, WIKIDATA_CACHE
from .storage import read_json, write_json

LOGGER = logging.getLogger(__name__)
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"


def _request_with_retries(params: dict[str, Any]) -> dict[str, Any]:
    headers = {"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT}
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(WIKIDATA_SPARQL_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001 - log and retry network/parser errors
            last_error = exc
            LOGGER.warning("Wikidata request attempt %s failed: %s", attempt, exc)
            time.sleep(BACKOFF_SECONDS * attempt)
    raise RuntimeError(f"Wikidata request failed after {MAX_RETRIES} attempts: {last_error}")


def build_city_query(limit: int = DEFAULT_SAMPLE_LIMIT, min_population: int = 50_000) -> str:
    """Build the SPARQL query for city/human-settlement entities."""
    return f"""
SELECT ?city ?cityLabel ?countryLabel ?population ?coord ?article ?climate ?climateLabel WHERE {{
  VALUES ?settlementType {{ wd:Q515 wd:Q486972 wd:Q7930989 wd:Q1549591 }}
  ?city wdt:P31/wdt:P279* ?settlementType;
        wdt:P1082 ?population;
        wdt:P625 ?coord;
        wdt:P17 ?country.
  FILTER(?population > {int(min_population)})
  OPTIONAL {{ ?city wdt:P2564 ?climate. }}
  OPTIONAL {{
    ?article schema:about ?city;
             schema:isPartOf <https://en.wikipedia.org/>.
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
ORDER BY DESC(?population)
LIMIT {int(limit)}
"""


def _parse_point(point: str) -> tuple[float | None, float | None]:
    if not point.startswith("Point("):
        return None, None
    lon_lat = point.removeprefix("Point(").removesuffix(")").split()
    if len(lon_lat) != 2:
        return None, None
    return float(lon_lat[1]), float(lon_lat[0])


def fetch_cities(limit: int = DEFAULT_SAMPLE_LIMIT, min_population: int = 50_000, force_refresh: bool = False) -> list[dict[str, Any]]:
    """Fetch or load cached cities from Wikidata."""
    cache = read_json(WIKIDATA_CACHE, default={})
    cache_id = f"limit={limit};min_population={min_population}"
    if not force_refresh and cache_id in cache:
        return cache[cache_id]

    LOGGER.info("Fetching %s cities with population > %s from Wikidata", limit, min_population)
    raw = _request_with_retries({"query": build_city_query(limit, min_population), "format": "json"})
    cities: list[dict[str, Any]] = []
    for row in raw.get("results", {}).get("bindings", []):
        lat, lon = _parse_point(row.get("coord", {}).get("value", ""))
        qid = row.get("city", {}).get("value", "").rsplit("/", 1)[-1]
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
            "climate_classification": row.get("climate", {}).get("value", "").rsplit("/", 1)[-1] or None,
            "climate_classification_label": row.get("climateLabel", {}).get("value"),
        })
    cache[cache_id] = cities
    write_json(WIKIDATA_CACHE, cache)
    return cities
