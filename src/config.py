"""Configuration for the CityClimate Explorer application."""
from __future__ import annotations

from pathlib import Path

APP_NAME = "CityClimate Explorer"
USER_AGENT = "CityClimateExplorer/0.1 (https://example.local; educational Wikipedia/Wikidata climate visualization)"
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
PROCESSED_DIR = DATA_DIR / "processed"
WIKIDATA_CACHE = CACHE_DIR / "wikidata_cities.json"
WIKIPEDIA_CACHE_DIR = CACHE_DIR / "wikipedia"
CLIMATE_CACHE_DIR = CACHE_DIR / "climate"
CITIES_PROCESSED = PROCESSED_DIR / "cities.json"
DEFAULT_POPULATION_THRESHOLD = 50_000
DEFAULT_SAMPLE_LIMIT = 75
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

for path in (CACHE_DIR, PROCESSED_DIR, WIKIPEDIA_CACHE_DIR, CLIMATE_CACHE_DIR):
    path.mkdir(parents=True, exist_ok=True)
