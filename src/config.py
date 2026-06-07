"""Configuration for the CityClimate Explorer application."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

APP_NAME = "CityClimate Explorer"
APP_VERSION = os.getenv("CITYCLIMATE_APP_VERSION", "1.0.0")
DEFAULT_PROJECT_URL = "https://github.com/CityClimate-Explorer/CityClimate-Explorer"
DEFAULT_CONTACT_URL = f"{DEFAULT_PROJECT_URL}/issues"
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
PROCESSED_DIR = DATA_DIR / "processed"
WIKIDATA_CACHE = CACHE_DIR / "wikidata_cities.json"
WIKIPEDIA_CACHE_DIR = CACHE_DIR / "wikipedia"
CLIMATE_CACHE_DIR = CACHE_DIR / "climate"
CITIES_PROCESSED = PROCESSED_DIR / "cities.json"
PRELOADED_CAPITALS = DATA_DIR / "preloaded" / "country_capitals.json"
REGIONAL_CAPITALS = DATA_DIR / "preloaded" / "regional_capitals_top15_countries.json"
POLAR_BORDER_CAPITALS = DATA_DIR / "preloaded" / "regional_capitals_polar_border.json"
CLIMATE_ZONES = DATA_DIR / "preloaded" / "climate_zones_simplified.geojson"
CAPITAL_CLIMATE_CACHE = DATA_DIR / "capital_climate_cache.json"
DEFAULT_POPULATION_THRESHOLD = 200_000
DEFAULT_SAMPLE_LIMIT = 10
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
BACKOFF_SECONDS = 1.5
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
WIKIDATA_REQUEST_TIMEOUT = (10, 60)
WIKIDATA_MAX_RETRIES = 3
WIKIDATA_BACKOFF_BASE_SECONDS = 1.5
WIKIDATA_QUERY_PAGE_SIZE = 100
WIKIDATA_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WIKIPEDIA_LICENSE = "CC BY-SA 4.0"
WIKIPEDIA_LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
WIKIDATA_LICENSE = "CC0 1.0"
WIKIDATA_LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"


def _streamlit_secret(name: str) -> Any | None:
    """Read an optional Streamlit secret without requiring a secrets file."""
    try:
        import streamlit as st

        return st.secrets.get(name)
    except (FileNotFoundError, KeyError, RuntimeError):
        return None


def setting(name: str, default: str | None = None) -> str | None:
    """Read configuration from the environment first, then Streamlit secrets."""
    value = os.getenv(name)
    if value is None:
        secret = _streamlit_secret(name)
        value = str(secret) if secret is not None else None
    return value if value not in (None, "") else default


def wikimedia_user_agent() -> str:
    """Return the informative User-Agent used for every Wikimedia request."""
    override = setting("CITYCLIMATE_WIKIMEDIA_USER_AGENT")
    if override:
        return override
    configured_project_url = setting("CITYCLIMATE_PROJECT_URL")
    configured_contact = setting("CITYCLIMATE_CONTACT")
    if str(setting("CITYCLIMATE_DEPLOYMENT", "development")).casefold() == "production":
        if not configured_project_url or not configured_contact:
            raise ValueError(
                "Production deployment requires CITYCLIMATE_PROJECT_URL and CITYCLIMATE_CONTACT "
                "through environment variables or Streamlit secrets."
            )
    project_url = configured_project_url or DEFAULT_PROJECT_URL
    contact = configured_contact or DEFAULT_CONTACT_URL
    return f"CityClimateExplorer/{APP_VERSION} ({project_url}; contact: {contact})"


# Kept as a public constant for compatibility; production operators should set
# the documented environment variables before importing the HTTP clients.
USER_AGENT = wikimedia_user_agent()


@dataclass(frozen=True)
class TileProvider:
    """Resolved Folium tile layer with explicit provider attribution."""

    name: str
    tiles: str
    attribution: str
    production_approved: bool


_TILE_PROVIDERS = {
    "cartodb_positron": {
        "tiles": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        "attribution": (
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors '
            '&copy; <a href="https://carto.com/attributions">CARTO</a>'
        ),
        "production_approved": False,
    },
    "maptiler": {
        "tiles": "https://api.maptiler.com/maps/streets/{z}/{x}/{y}.png?key={api_key}",
        "attribution": (
            '&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a> '
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        ),
        "production_approved": True,
    },
    "mapbox": {
        "tiles": "https://api.mapbox.com/styles/v1/mapbox/light-v11/tiles/256/{z}/{x}/{y}@2x?access_token={api_key}",
        "attribution": (
            '&copy; <a href="https://www.mapbox.com/about/maps/">Mapbox</a> '
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors '
            '<a href="https://www.mapbox.com/map-feedback/">Improve this map</a>'
        ),
        "production_approved": True,
    },
    "stadia": {
        "tiles": "https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png?api_key={api_key}",
        "attribution": (
            '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a> '
            '&copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> '
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        ),
        "production_approved": True,
    },
}


def get_tile_provider() -> TileProvider:
    """Resolve demo or production tiles without embedding provider credentials."""
    deployment = str(setting("CITYCLIMATE_DEPLOYMENT", "development")).casefold()
    provider_name = str(setting("CITYCLIMATE_TILE_PROVIDER", "cartodb_positron")).casefold()
    if provider_name in {"self_hosted", "custom"}:
        tiles = setting("CITYCLIMATE_TILE_URL")
        attribution = setting("CITYCLIMATE_TILE_ATTRIBUTION")
        if not tiles or not attribution:
            raise ValueError("Custom/self-hosted tiles require CITYCLIMATE_TILE_URL and CITYCLIMATE_TILE_ATTRIBUTION.")
        provider = TileProvider(provider_name, tiles, attribution, production_approved=True)
    else:
        definition = _TILE_PROVIDERS.get(provider_name)
        if definition is None:
            raise ValueError(f"Unsupported tile provider: {provider_name}")
        tiles = str(definition["tiles"])
        if "{api_key}" in tiles:
            api_key = setting("CITYCLIMATE_TILE_API_KEY")
            if not api_key:
                raise ValueError(f"{provider_name} requires CITYCLIMATE_TILE_API_KEY.")
            tiles = tiles.replace("{api_key}", api_key)
        provider = TileProvider(
            provider_name,
            tiles,
            str(definition["attribution"]),
            bool(definition["production_approved"]),
        )
    if deployment == "production" and not provider.production_approved:
        raise ValueError(
            "Production deployment requires an explicitly configured commercial or self-hosted tile provider; "
            "the demo CARTO layer is not an approved production default."
        )
    return provider


for path in (CACHE_DIR, PROCESSED_DIR, WIKIPEDIA_CACHE_DIR, CLIMATE_CACHE_DIR):
    path.mkdir(parents=True, exist_ok=True)
