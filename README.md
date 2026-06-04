# CityClimate Explorer

CityClimate Explorer is a Python/Streamlit web app that starts quickly with a local, preloaded country-capital map and can optionally visualize additional populated cities by continent. It shows climate classifications plus monthly climate-table data parsed from Wikipedia.

## What it does

- Loads a bundled country-capital dataset immediately on startup; the initial map does not require a live Wikidata query.
- Optionally queries Wikidata for additional cities or human settlements only after the user selects a continent and clicks **Load additional cities**.
- Uses a default additional-city population threshold of 200,000 inhabitants to keep optional Wikidata queries smaller.
- Retrieves each city's QID, name, country, continent/region, population, coordinates, English Wikipedia sitelink, and Wikidata climate classification when available.
- Fetches each city's English Wikipedia article through the MediaWiki API.
- Parses `Weather box` templates first, then rendered HTML climate tables as a fallback.
- Displays city markers on a Folium map in Streamlit.
- Shows climate table rows such as average highs/lows, daily means, precipitation/rainfall/snowfall, humidity, sunshine hours, precipitation days, and record highs/lows when those fields are present in the article.
- Lets users select a city and highlight other displayed cities with the same climate classification.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.11 or newer is recommended.

## Running the app

```bash
streamlit run app.py
```

The app renders the preloaded country-capital map first. To load more cities, choose a **Region / continent** in the sidebar and click **Load additional cities**. Region means continent in this app. Additional loading can take time because it uses Wikidata for the selected continent and may parse Wikipedia climate tables for uncached cities.

## Refreshing data

The app reads the local capital dataset on startup and never fetches all world cities automatically. Optional additional-city results are cached by continent and population threshold. Use the Streamlit **Refresh additional-city cache** button or the CLI script for one continent:

```bash
python refresh_data.py --continent Europe --limit 75 --min-population 200000 --force
```

Omit `--force` to reuse existing Wikidata article/climate caches where possible. The default minimum population is 200,000.

## Data sources

The primary sources are:

- **Wikidata SPARQL endpoint** for city/settlement metadata, population, coordinates, country, English Wikipedia article sitelinks, and Köppen/climate classification (`P2564`) where available.
- **Wikipedia MediaWiki API** for article wikitext and rendered HTML, which are parsed for climate tables and Weather box templates.

No paid APIs are used. External climate APIs are intentionally not enabled by default; they can be added later as optional fallback modules.

## Caching

Local cache files are written under `data/`:

- `data/preloaded/country_capitals.json` stores the startup country-capital dataset.
- `data/cache/wikidata_cities.json` stores optional Wikidata result sets by continent, limit, and population threshold.
- `data/cache/wikipedia/` stores fetched MediaWiki article responses.
- `data/cache/climate/` stores parsed city climate records.
- `data/processed/cities.json` stores the Streamlit-ready enriched dataset.

The startup path uses the preloaded capitals dataset, so Wikidata timeouts cannot crash the initial map. Optional additional-city requests use a descriptive User-Agent, retries, timeouts, backoff, and stale-cache fallback; a failed refresh does not delete working cached data.

## Limitations

Wikipedia climate tables are inconsistent. Some cities do not have climate tables, some use non-standard templates, and some have multiple station tables. The parser preserves what it can extract and marks unavailable/failed pages with an extraction status instead of hiding the city.

Wikidata climate classification availability also varies. Cities without a classification are displayed as `Unknown`. The optional Wikidata query is continent-scoped and excludes broad entities such as countries, continents, states, provinces, and administrative regions before Python applies the same defensive filtering again.

## Same-climate highlighting and future polygon overlays

The current MVP highlights **city markers** that share the selected city's classification. It does **not** draw continuous climate-zone areas, because reliable polygon data is not provided by Wikidata/Wikipedia for every classification and the app does not fake polygons.

A future overlay module can load a verified GeoJSON file of Köppen climate zones and add it as a Folium layer. Keep this optional and document the GeoJSON source/license before enabling it.

## Tests

```bash
pytest
```

Tests cover Weather box parsing, HTML table fallback parsing, monthly normalization, and graceful handling of missing climate fields.
