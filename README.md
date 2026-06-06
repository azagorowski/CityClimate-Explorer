# CityClimate Explorer

CityClimate Explorer is a Python 3.11+/Streamlit map of world capitals and city climate data. It is designed for a fast, reliable startup: all bundled capitals and their locally cached climate classifications are rendered immediately, without a click and without startup Wikipedia or Wikidata requests.

## What the app does

- Loads 196 prepackaged capital records from `data/preloaded/country_capitals.json`.
- Joins every capital to `data/capital_climate_cache.json` at startup. Each record has a specific classification or an explicit `Unknown`, plus source name, language, page title, URL, and source priority.
- Colors map markers by broad climate group while preserving specific labels such as `Af`, `BWh`, `Cfb`, `Dfb`, and `ET` in tooltips and popups.
- Shows a climate legend for **Tropical**, **Dry / Arid**, **Temperate**, **Continental**, **Polar**, **Highland / Mountain**, and **Unknown**.
- Loads detailed monthly Wikipedia climate tables only when a city is selected. Existing detailed caches are used first, so this does not delay startup.
- Loads up to 10 population-ranked non-capital cities for a selected continent and country from `data/top_non_capital_cities_by_country.json`. The normal button path never runs Wikidata SPARQL.
- Merges optional cities using Wikidata QID first and normalized city/country second, preserving the bundled capital as authoritative.
- Supports classification filtering and same-climate marker highlighting.

## Install and run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On startup, the map already contains all capitals, climate-colored markers, classifications in tooltips/popups, source metadata, and the legend. In the sidebar, **region means continent**. Select a continent and then a country; the country dropdown updates for that continent and enables **Load cached cities for selected country**. The UI cannot load more than 10 optional cities. If a country has fewer cached records, it loads the available count and reports that count; if none are bundled, it says so without making a slow network request.

The bundled optional-city cache currently includes a complete 10-city Algeria example and is intentionally extensible through the developer refresh command below. Production maintainers can precompute other countries before deployment without changing the runtime design.

## Cache design and refresh workflows

The runtime and refresh paths are deliberately separate:

- **Runtime:** local JSON reads for all startup classifications and optional cities.
- **On city selection:** one city's detailed monthly climate table may be read from the local climate cache or fetched from Wikipedia.
- **Developer/admin refresh:** explicit scripts may call Wikimedia services and then write reviewed local cache files. These scripts are not invoked by Streamlit.

Refresh all capital classifications from English Wikipedia first, native-language Wikipedia only if English has no usable classification, and bundled Wikidata claims last:

```bash
python scripts/build_capital_climate_cache.py
```

Use `--force` to bypass cached Wikipedia articles. `--limit N` is available for developer smoke tests. Missing results are retained as `Unknown` with a source note rather than dropping a capital.

Refresh one country's optional city records from Wikidata as an explicit developer action:

```bash
python scripts/build_optional_city_cache.py \
  --continent Africa \
  --country Algeria \
  --country-qid Q262 \
  --force
```

This command is country-scoped and capped at 10. Review generated records and source metadata before committing them. `refresh_data.py` remains a lower-level country-scoped cache utility, not part of the normal user flow.

## Climate source precedence

Capital cache records follow this priority:

1. `english_primary` — classification parsed from the English Wikipedia city page.
2. `native_fallback` — native-language Wikipedia used only when English has no usable classification.
3. `wikidata_fallback` — Wikidata climate classification used only when Wikipedia has no usable classification.
4. `unavailable` — displayed as `Unknown`, with a note explaining that no usable cached result exists.

Marker colors use broad groups so the legend remains stable. Specific classifications remain visible in the city selector, marker tooltip, popup, and detail panel. Classification metadata and detailed monthly-table metadata are stored separately because they can come from different source pages or refresh times.

## Validation and tests

```bash
pytest
python scripts/validate_capitals.py
```

Tests verify that all capitals have startup climate fields, key Central/South American and European capitals have known English-supported classifications, startup is local-only, the legend is rendered, climate groups map to stable colors, optional selectors are required, Algeria loads locally with at most 10 non-capitals, duplicate capitals remain excluded, and legacy Streamlit container-width arguments are absent.

## Data and licensing

Only open-source libraries and Wikimedia/open map data are used. No paid weather API, proprietary SDK, closed dataset, or non-commercial-use dependency is included.

- Wikipedia content: CC BY-SA 4.0; exact source metadata is retained per cached classification/table.
- Wikidata structured data: CC0 1.0.
- OpenStreetMap map data: ODbL; Carto/OpenStreetMap attribution remains visible on the Folium map.
- Direct Python dependencies: permissive MIT, BSD-3-Clause, or Apache-2.0 licenses.

Commercial use is permitted subject to each source's attribution, notice, and share-alike requirements. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for details. Operators should also comply with their production tile provider's usage policy.
