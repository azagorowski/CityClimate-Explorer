# CityClimate Explorer

CityClimate Explorer is a Python/Streamlit web app that visualizes populated cities on an interactive map and shows climate classifications plus monthly climate-table data parsed from Wikipedia.

## What it does

- Queries Wikidata for cities or human settlements above a population threshold, defaulting to 50,000 inhabitants.
- Retrieves each city's QID, name, country, population, coordinates, English Wikipedia sitelink, and Wikidata climate classification when available.
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

The app supports a manageable sample mode through the sidebar's "Wikidata sample size" slider. Start small while developing because parsing climate tables requires one Wikipedia request per uncached city.

## Refreshing data

The app reads cached/processed data when available. Use the Streamlit **Refresh cached data** button or the CLI script:

```bash
python refresh_data.py --limit 75 --min-population 50000 --force
```

Omit `--force` to reuse existing article/climate caches where possible.

## Data sources

The primary sources are:

- **Wikidata SPARQL endpoint** for city/settlement metadata, population, coordinates, country, English Wikipedia article sitelinks, and Köppen/climate classification (`P2564`) where available.
- **Wikipedia MediaWiki API** for article wikitext and rendered HTML, which are parsed for climate tables and Weather box templates.

No paid APIs are used. External climate APIs are intentionally not enabled by default; they can be added later as optional fallback modules.

## Caching

Local cache files are written under `data/`:

- `data/cache/wikidata_cities.json` stores Wikidata result sets by query parameters.
- `data/cache/wikipedia/` stores fetched MediaWiki article responses.
- `data/cache/climate/` stores parsed city climate records.
- `data/processed/cities.json` stores the Streamlit-ready enriched dataset.

This prevents the app from hitting Wikidata or Wikipedia repeatedly on startup and helps respect API rate limits. Requests use a descriptive User-Agent, retries, and backoff.

## Limitations

Wikipedia climate tables are inconsistent. Some cities do not have climate tables, some use non-standard templates, and some have multiple station tables. The parser preserves what it can extract and marks unavailable/failed pages with an extraction status instead of hiding the city.

Wikidata climate classification availability also varies. Cities without a classification are displayed as `Unknown`.

## Same-climate highlighting and future polygon overlays

The current MVP highlights **city markers** that share the selected city's classification. It does **not** draw continuous climate-zone areas, because reliable polygon data is not provided by Wikidata/Wikipedia for every classification and the app does not fake polygons.

A future overlay module can load a verified GeoJSON file of Köppen climate zones and add it as a Folium layer. Keep this optional and document the GeoJSON source/license before enabling it.

## Tests

```bash
pytest
```

Tests cover Weather box parsing, HTML table fallback parsing, monthly normalization, and graceful handling of missing climate fields.
