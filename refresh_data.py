"""Command-line cache refresh for CityClimate Explorer."""
from __future__ import annotations

import argparse
import logging

from src.config import CITIES_PROCESSED, DEFAULT_POPULATION_THRESHOLD, DEFAULT_SAMPLE_LIMIT
from src.storage import write_json
from src.capitals import SUPPORTED_CONTINENTS
from src.wikidata import fetch_cities
from src.wikipedia import enrich_city_climate


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Wikidata and Wikipedia climate caches.")
    parser.add_argument("--limit", type=int, default=DEFAULT_SAMPLE_LIMIT, help="Maximum number of Wikidata city records to fetch.")
    parser.add_argument("--min-population", type=int, default=DEFAULT_POPULATION_THRESHOLD, help="Population threshold for additional cities (default: 200,000).")
    parser.add_argument("--continent", choices=SUPPORTED_CONTINENTS, required=True, help="Continent to refresh; the app never fetches all world cities at once.")
    parser.add_argument("--force", action="store_true", help="Bypass local caches and refetch remote sources.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    cities = fetch_cities(limit=args.limit, min_population=args.min_population, force_refresh=args.force, continent=args.continent)
    enriched = [enrich_city_climate(city, force_refresh=args.force) for city in cities]
    write_json(CITIES_PROCESSED, enriched)
    print(f"Wrote {len(enriched)} city records to {CITIES_PROCESSED}")


if __name__ == "__main__":
    main()
