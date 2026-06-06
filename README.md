# CityClimate Explorer

CityClimate Explorer is a Python/Streamlit web app that starts quickly with a complete local, preloaded world-capitals map and can optionally visualize up to 10 additional major non-capital cities by selected continent and country. It shows climate classifications plus monthly climate-table data parsed from Wikipedia when a city is selected.

## What it does

- Loads a bundled dataset of sovereign-state world capitals immediately on startup; the initial map does not require a live Wikidata query.
- Optionally queries Wikidata for up to 10 additional major non-capital cities or human settlements only after the user selects both a continent (region) and a country, then clicks **Load additional cities for selected country**.
- Uses a default additional-city population threshold of 200,000 inhabitants to keep optional Wikidata queries smaller; this threshold applies only to additional non-capital cities, never to preloaded capitals.
- Retrieves each city's QID, name, country, continent/region, population, coordinates, English Wikipedia sitelink, and any Wikidata climate classification as fallback metadata only.
- Fetches a selected city's English Wikipedia article through the MediaWiki API first; every preloaded capital attempts climate-data loading on selection even when population, climate classification, or initial climate data is missing.
- Resolves English Wikipedia pages from Wikidata sitelinks when QIDs are available, follows redirects, and falls back to safe city/country title lookup or bundled capital titles.
- Parses `Weather box` templates first, then rendered HTML climate tables as a fallback, and extracts Köppen/classification wording from English Wikipedia before considering Wikidata fallback claims.
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

The app renders the preloaded world-capitals map first and shows **Showing preloaded world capitals.** To load more cities, choose **Select a continent** and then **Select a country** in the sidebar, then click **Load additional cities for selected country**. The hard limit is 10 optional non-capital cities per country. Region means continent in this app. Additional loading can take time because it uses Wikidata for the selected country; Wikipedia climate tables are loaded later when a user selects a city.

## Refreshing data

The app reads the local capital dataset on startup and never fetches all world cities automatically. All capitals remain included regardless of population, missing climate classification, or missing parsed climate table data. Optional additional-city results are cached by continent, country, and population threshold, and the app displays no more than 10 per country. Use the Streamlit **Refresh additional-city cache** button or the CLI script for one country:

```bash
python refresh_data.py --continent Europe --country France --limit 10 --min-population 200000 --force
```

Omit `--force` to reuse existing Wikidata, article, and climate caches where possible. The default minimum population is 200,000 for optional additional cities only; capitals are preloaded regardless of population.

## Data sources

The primary sources are:

- **Wikipedia MediaWiki API** for article wikitext and rendered HTML, which are parsed for climate tables, Weather box templates, and English Wikipedia climate-classification wording. English Wikipedia is the source of truth for climate data and classification. Native-language Wikipedia is used only as a fallback when English climate data is unavailable.
- **Wikidata SPARQL endpoint** for optional city/settlement metadata, population, coordinates, country, English Wikipedia article sitelinks, and Köppen/climate classification (`P2564`) where available. Wikidata climate classification is shown only as a clearly labeled fallback if Wikipedia has no usable classification.

No paid APIs are used. External climate APIs are intentionally not enabled by default; they can be added later as optional fallback modules.

## Caching

Local cache files are written under `data/`:

- `data/preloaded/country_capitals.json` stores the startup sovereign-state world-capitals dataset, including small capitals such as Andorra la Vella, San Marino, Vaduz, Monaco, Ngerulmud, Funafuti, Malé, and Victoria.
- `data/cache/wikidata_cities.json` stores optional Wikidata result sets by continent, country, and population threshold.
- `data/cache/wikipedia/` stores fetched MediaWiki article responses.
- `data/cache/climate/` stores parsed city climate records.
- `data/processed/cities.json` stores the Streamlit-ready enriched dataset.

The startup path uses only the preloaded capitals dataset, so Wikidata timeouts cannot crash the initial map. Optional additional-city requests use a descriptive User-Agent, retries, timeouts, backoff, and stale-cache fallback; a failed refresh does not delete working cached data. Restricting optional requests to a selected country and a hard maximum of 10 results avoids broad global or continent-wide Wikidata requests and reduces timeout risk.

## Limitations

Wikipedia climate tables are inconsistent. Some cities do not have climate tables, some use non-standard templates, and some have multiple station tables. The parser preserves what it can extract and marks unavailable/failed pages with an extraction status instead of hiding the city.

Wikidata climate classification availability also varies and is not treated as the final truth. Cities without a Wikipedia-supported classification or a Wikidata fallback are displayed as `Unknown`. The optional Wikidata query is country-scoped and excludes broad entities such as countries, continents, states, provinces, and administrative regions before Python applies the same defensive filtering again.

## Same-climate highlighting and future polygon overlays

The current MVP highlights **city markers** that share the selected city's classification. It does **not** draw continuous climate-zone areas, because reliable polygon data is not provided by Wikidata/Wikipedia for every classification and the app does not fake polygons.

A future overlay module can load a verified GeoJSON file of Köppen climate zones and add it as a Folium layer. Keep this optional and document the GeoJSON source/license before enabling it.

## Tests

```bash
pytest
```

Tests cover startup capital loading, validation of the bundled sovereign-state capital dataset, country-specific Wikidata query construction, duplicate merging, Bratislava/Budapest HTML climate-table regressions, Weather box parsing, HTML table fallback parsing, monthly normalization, and graceful handling of missing climate fields.

## Open-source and commercial-use licensing

All direct runtime libraries are permissively licensed (MIT, BSD-3-Clause, or Apache-2.0), and the project uses no proprietary SDK or paid climate API. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for the dependency-by-dependency audit, data licenses, attribution requirements, and map-tile deployment considerations.

Wikipedia climate content is fetched on demand under CC BY-SA 4.0 and is always accompanied by source-page metadata in the UI. Wikidata structured metadata is CC0. Commercial use is permitted, but deployments and exported/adapted Wikipedia content must preserve attribution and comply with CC BY-SA share-alike requirements. The local capital seed retains English Wikipedia URLs so source attribution remains available without delaying startup.
