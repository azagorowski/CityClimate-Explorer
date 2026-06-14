# CityClimate Explorer

CityClimate Explorer is a Python 3.11+/Streamlit map of worldwide national capitals, first-level regional capitals in the world’s 90 largest sovereign countries by area, polar-border regional/local administrative capitals, and locally cached climate data. It is designed for a fast, reliable startup: all locations, classifications, and lightweight visual climate zones are read from bundled files without startup Wikipedia or Wikidata requests.

## What the app does

- Loads 196 prepackaged national-capital records from `data/preloaded/country_capitals.json`.
- Adds a local top-90-country regional-capital cache from `data/preloaded/regional_capitals_top90_countries.json`. The original 332 reviewed top-15 records remain intact, and ranks 16–90 add reviewed first-level administrative centers structured for later Wikidata enrichment. National records win when the same city has both roles.
- Adds a focused local set of polar-border administrative capitals/centers from `data/preloaded/regional_capitals_polar_border.json`, including Greenland, Scandinavia, Svalbard, Arctic Canada/Alaska/Russia, and southern Argentina/Chile. This is an administrative-center dataset, not a general city list.
- Adds the curated `data/preloaded/regional_capitals_priority_countries.json` snapshot: complete reviewed coverage for Poland, Spain, France (metropolitan and overseas), Norway, Sweden, Finland, all 16 German Länder, all 81 Turkish provinces, all 26 Swiss canton seats, South Africa's nine provincial seats, all nine Austrian state capitals, Angola's 18 provincial capitals, Namibia's 14 regional seats plus Walvis Bay, all 24 Ecuadorian provincial capitals, all 25 Peruvian department/constitutional-province capitals, all 16 Chilean regional capitals, and all 47 Japanese prefectural capitals. These seed lists—not live discovery—control inclusion, so expected centers remain available if optional enrichment fails.
- Tags records with `world_national_capital`, `top90_country_regional_capital`, `polar_border_regional_capital`, or `priority_country_regional_capital` scope so the UI can filter each inclusion rule independently.
- Loads `data/preloaded/climate_zones_simplified.geojson` as a very small, semi-transparent broad-climate visualization behind markers. The layer is explicitly schematic rather than a scientific boundary product.
- Offers a **Climate zone layer** selector with **None**, **Broad groups**, and **Köppen types** modes. Detailed types load from the local `data/preloaded/koppen_climate_zones_simplified.geojson`, a display-oriented CC BY 4.0 derivative of Beck et al. (2018); layer toggling performs no runtime download.
- Joins every capital to the authoritative local `data/capital_climate_cache.json` before rendering the selector or map. Startup classification does not depend on a click or a network request.
- Separates primary Köppen codes from secondary/bordering codes. The primary code alone controls the broad group and marker color; nuanced secondary codes remain visible in popups/details.
- Uses one resolved specific classification consistently in selector labels, marker tooltips/popups, details, climate filtering, and same-climate highlighting.
- Uses QID-first stable marker IDs (with normalized city/country/administrative-region fallbacks) so clicking a Folium marker writes the same `selected_city_id` session state used by the right-panel dropdown and immediately drives the details/monthly-table workflow.
- Keeps the searchable capital selector in the right details panel directly above **Capital details**, leaving the center column focused on the map.
- Colors markers with the cached broad groups **Tropical**, **Dry / Arid**, **Temperate**, **Continental**, **Polar**, **Highland / Mountain**, and **Unknown**, and renders the same groups in the legend.
- Filters only the already-preloaded capitals by continent, country, climate classification, or national/regional capital type. Independent toggles control national capitals, regional capitals, and the climate-zone layer.
- Loads a detailed monthly Wikipedia climate table only after a capital is selected. The table is displayed in Jan–Dec calendar order with Annual last, and does not replace the authoritative startup classification.
- Generates a selected-city annual temperature line chart from the parsed daily-mean row, or from `(average high + average low) / 2` only when both real monthly rows exist. It never plots the Annual column or fabricates missing values; a friendly unavailable message is shown instead.
- Retains classification and table provenance separately so English/native Wikipedia CC BY-SA attribution and Wikidata CC0 metadata stay accurate.

The former optional non-capital city loader, its continent/country loading controls, session state, cache, and runtime merge path have been removed. Normal app startup and interaction never issue a Wikidata SPARQL city-loading request.

## Install and run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On startup, the map contains all bundled capitals, climate-colored markers, classifications in tooltips/popups, source metadata, and the legend. Sidebar filters only narrow this local capital list and never trigger a refresh.

## Top-90 area reference and annual temperature normalization

`data/preloaded/top_90_countries_by_area.json` fixes a deterministic ranks 1–90 sovereign-state list, area values, optional country QIDs, and per-row provenance. The selection rule uses ranked sovereign-state rows from Wikipedia’s *List of countries and dependencies by area* and excludes unranked dependencies, Antarctica, and disputed entries. Runtime never recalculates this list.

The annual chart uses the same on-demand/cache-backed monthly climate table for national, regional, and polar-border records. Supported temperature labels include short average rows such as `Average C`, daily/mean temperature, average high/low, and mean maximum/minimum. Unicode minus signs, references, hidden spans, and non-breaking spaces are normalized before charting. Celsius is preferred; Fahrenheit is used only if Celsius is unavailable.

## Cache design and developer refresh

The runtime and refresh paths are deliberately separate:

- **Runtime startup:** reads the bundled national-capital cache, both regional-capital JSON files, and climate-zone GeoJSON only.
- **On capital selection:** may read a detailed local climate cache or fetch that capital's monthly table from Wikipedia; the preloaded classification remains authoritative for every UI surface.
- **Developer/admin refresh:** the explicit build script may call approved Wikimedia services and writes a reviewed local cache. Streamlit never invokes it.

Refresh all capital classifications from English Wikipedia first, native-language Wikipedia only if English has no usable classification, and bundled Wikidata claims last:

```bash
python scripts/build_capital_climate_cache.py
```

Rebuild the regional-capital and lightweight climate-zone assets independently:

```bash
python scripts/build_top90_country_list.py
python scripts/build_regional_capitals_cache.py
python scripts/build_polar_border_capitals.py
python scripts/build_priority_regional_capitals.py
python scripts/build_climate_zones.py
python scripts/build_koppen_climate_zones.py
python scripts/validate_regional_capitals.py
python scripts/validate_regional_capital_climates.py
python scripts/validate_priority_regional_capitals.py
pytest tests/test_temperature.py
```

The regional builder writes complete record-level provenance and an offline startup flag. Its committed reviewed seed is designed for deterministic builds; maintainers may enrich QIDs, administrative-region QIDs, populations, sitelinks, and specific Köppen classifications from Wikidata and English/native Wikipedia during a reviewed refresh. The broad-zone builder creates a project-authored, low-vertex schematic layer under MIT. The detailed builder regenerates the committed display-oriented Köppen layer from reviewed generalized extents based on Beck et al. (2018), distributed under CC BY 4.0 with attribution retained in the GeoJSON, source documentation, and notices.

Use `--force` to bypass developer-side Wikipedia article caches. `--limit N` is available for smoke tests. The builder also writes `data/capital_climate_cache_report.json` with source totals and a reason for every unresolved capital. Generated records retain source name, language, page title/URL, source priority, extraction status, license, and contributor-history metadata. Run validation and review unresolved records before committing a refreshed cache.

Streamlit keys its startup dataset cache with the SHA-256 digest of `data/capital_climate_cache.json`, so replacing or rebuilding that file automatically invalidates stale `Unknown` values. During development, if another cached UI value needs resetting, stop Streamlit and run `streamlit cache clear` before restarting `streamlit run app.py`.

### Primary and bordering Köppen classifications

The parser recognizes ordered wording such as `Köppen: ET, bordering on Cfc`, `classified as ET`, `with influences of`, and `transitional to`. Records store `primary_koppen_code`, `secondary_koppen_codes`, a concise parsed note, the specific display label, and the broad climate group. Primary `A`, `B`, `C`, `D`, and `E` codes map to Tropical, Dry / Arid, Temperate, Continental, and Polar respectively. A clear primary code overrides generic prose such as “highland influence” and all later bordering codes.

Ushuaia is the regression example: its bundled primary code is `ET`, its bordering code is `Cfc`, and its broad group and marker color are Polar. It must never become Temperate merely because `Cfc` appears later in the source wording. Run `python scripts/validate_regional_capital_climates.py` after either regional dataset changes; the generated audit lists missing values, primary/group mismatches, conflicting codes, and broad legacy rows requiring a future reviewed subtype refresh.

The priority validator additionally locks the Nordic regressions. Primary `Dfc`
for Tromsø, Vadsø, Rovaniemi, Luleå, Umeå, and Östersund is Continental
(subarctic), while Bodø's primary `Cfc` remains Temperate/subpolar oceanic.
Primary `ET`/`EF` always maps to Polar. Bogotá remains a separately reviewed
Tropical highland / Highland-Mountain override.

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
python scripts/validate_regional_capitals.py
python scripts/validate_priority_regional_capitals.py
python scripts/validate_provenance.py
```

Tests verify that all capitals have startup climate fields and provenance, the regression capitals have known English-supported classifications, startup is local-only, the legend is rendered, marker groups map to stable colors, the capitals-only UI contains no optional loading path, and monthly columns stay in calendar order.

## Data and licensing

Only open-source libraries and Wikimedia/open map data are used. No paid weather API, proprietary SDK, closed dataset, or non-commercial-use dependency is included.

- Wikipedia content: CC BY-SA 4.0; exact source metadata is retained per cached classification/table.
- Wikidata structured data: CC0 1.0.
- Bundled regional-capital snapshot: record-level Wikidata-compatible CC0 metadata and linked Wikipedia CC BY-SA review provenance.
- Generalized climate-zone GeoJSON: project-authored under MIT; commercial use permitted; visibly labeled as schematic.
- OpenStreetMap map data: ODbL; Carto/OpenStreetMap attribution remains visible on the Folium map.
- Direct Python dependencies: permissive MIT, BSD-3-Clause, or Apache-2.0 licenses.

Commercial use is permitted subject to each source's attribution, notice, and share-alike requirements. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for details. Operators should also comply with their production tile provider's usage policy.

## Monetization readiness and license boundaries

CityClimate Explorer can be used in a commercial/public product, but monetization does not remove upstream obligations:

- **Application source code:** MIT licensed under [`LICENSE`](LICENSE). This applies to the repository's own code, not to third-party packages, Wikimedia content, or map services.
- **Wikipedia climate tables and classifications:** CC BY-SA 4.0. English Wikipedia is primary; native-language Wikipedia is fallback only. Displayed and cached records retain page, language, URL, priority, license, retrieval, and page-history metadata. Adapted/redistributed Wikipedia-derived climate data must preserve attribution and applicable share-alike terms.
- **Wikidata metadata:** CC0 1.0. It supplies QIDs, coordinates, population, relationships, continent mapping, sitelinks, and final-fallback classifications. Attribution is retained for transparency.
- **Map tiles:** provider-specific service and attribution terms apply in addition to the OpenStreetMap data license. The demo layer is not an approved production default.
- **Bundled data:** field-level policy and record provenance are documented in [`data/preloaded/SOURCES.md`](data/preloaded/SOURCES.md).
- **Third-party software:** direct dependency notices are in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). Transitive packages require review before release.

No proprietary weather API, paid climate database, non-commercial/research-only dataset, GPL/AGPL direct dependency, or unclear-license source is approved by the project. A new source must document its name, URL, license, commercial-use status, and attribution obligations before use.

### Reproducible dependencies and license audit

`requirements.txt` remains the development input. `requirements-lock.txt` pins the resolved Python 3.11 environment, including transitive packages. Regenerate it only in a clean Python 3.11 environment after reviewing upgrades:

```bash
python -m venv .venv-lock
. .venv-lock/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip freeze > requirements-lock.txt
```

Install the reviewed lock in production:

```bash
python -m pip install -r requirements-lock.txt
```

List and validate reviewed direct licenses, then inspect installed metadata and all transitive packages:

```bash
python scripts/audit_dependency_licenses.py --installed-metadata
python scripts/validate_provenance.py
```

The audit is intentionally local/open-source and does not send dependency data to a proprietary service.

## Map tiles for production

Tile configuration reads environment variables first and Streamlit secrets second. Never commit an API key.

Development/demo defaults to `cartodb_positron`, with explicit CARTO/OpenStreetMap attribution. Production mode refuses that unreviewed free/demo default. Configure one of `maptiler`, `mapbox`, `stadia`, `self_hosted`, or `custom` after reviewing commercial terms:

```bash
export CITYCLIMATE_DEPLOYMENT=production
export CITYCLIMATE_TILE_PROVIDER=maptiler
export CITYCLIMATE_TILE_API_KEY='replace-at-deploy-time'
```

For a self-hosted or contract-specific CARTO endpoint:

```bash
export CITYCLIMATE_DEPLOYMENT=production
export CITYCLIMATE_TILE_PROVIDER=self_hosted
export CITYCLIMATE_TILE_URL='https://tiles.example.com/{z}/{x}/{y}.png'
export CITYCLIMATE_TILE_ATTRIBUTION='Map data © OpenStreetMap contributors; tiles © Your Company'
```

Equivalent keys can be placed in `.streamlit/secrets.toml`. Confirm the provider allows the expected traffic, caching, branding, and commercial use. Attribution is rendered directly on the Folium/Leaflet map and summarized in the sidebar.

## Wikimedia production User-Agent

Every Wikipedia, MediaWiki, Wikidata API, and Wikidata SPARQL request uses one configurable User-Agent. Set a real product URL and monitored contact before deployment:

```bash
export CITYCLIMATE_APP_VERSION='1.0.0'
export CITYCLIMATE_PROJECT_URL='https://your-product.example/climate'
export CITYCLIMATE_CONTACT='mailto:ops@your-product.example'
# Or fully override it:
export CITYCLIMATE_WIKIMEDIA_USER_AGENT='CityClimateExplorer/1.0.0 (https://your-product.example/climate; contact: ops@your-product.example)'
```

The repository default points to the project/contact issue URLs and no longer uses `example.local` or labels the product as educational.

## Export and cache policy

There is currently no user download/export feature. Any future export of Wikipedia-derived climate data must include the original source page URL/title, source language, source priority, retrieval timestamp when available, CC BY-SA 4.0 notice/link, and a note/link identifying page history as the contributor record. Cache adapters and refresh scripts contain safeguards not to strip this metadata.

## Commercial launch checklist

- [ ] Set a real Wikimedia project URL, version, and monitored contact/User-Agent.
- [ ] Set `CITYCLIMATE_DEPLOYMENT=production` and configure a tile provider with reviewed commercial terms.
- [ ] Verify map attribution against the provider contract and OpenStreetMap requirements.
- [ ] Run `pytest`, `python scripts/validate_capitals.py`, and `python scripts/validate_provenance.py`.
- [ ] Run `python scripts/audit_dependency_licenses.py --installed-metadata` and review every transitive package in `requirements-lock.txt`.
- [ ] Review Wikipedia source links, CC BY-SA notices, and page-history links in the UI.
- [ ] Preserve source/license metadata in caches and any future exports.
- [ ] Review [`data/preloaded/SOURCES.md`](data/preloaded/SOURCES.md) after every bundled-data refresh.

## Celsius-only annual temperature charts

Selected-city annual charts always normalize parsed monthly temperatures to Celsius before Altair receives the data. Reported Celsius average rows (including `Average C`) are preferred, followed by Celsius daily means and then a mean computed from Celsius average highs/lows. Fahrenheit-only equivalents are converted with `C = (F - 32) × 5/9` and rounded to one decimal place. Annual summary columns and non-mean metrics (records, precipitation, sunshine, and humidity) are never plotted. If no valid monthly series exists, the details panel reports that the annual temperature chart is unavailable.

## Local-first regional capitals and selected-country zoom

The normal Streamlit startup reads the committed `data/preloaded/regional_capitals_top90_countries.json` cache, including an explicit processing status for each of the 90 largest sovereign countries by area. Regional-capital discovery and broad Wikimedia requests are developer-only rebuild operations; startup does not invoke them. National capitals and the separate polar-border regional/local-capital cache remain part of the merged map dataset.

Selecting a national, regional, or polar-border capital by marker or dropdown uses the bundled `data/preloaded/country_boundaries_simplified.geojson` asset to fit the map to the selected country and draw a subtle outline. Stable country QIDs/ISO identifiers are preferred, with normalized country-name aliases as fallback. If no country feature is available, the map falls back to the selected marker. The current climate layer, marker filters, and selected details remain in place, and a filtered-out selected marker is retained so it does not disappear during the zoom.

### Developer data rebuilds

These commands are maintenance operations, not application-startup steps:

```bash
# Normalize a reviewed Wikidata/Wikipedia-derived top-90 snapshot.
python scripts/build_regional_capitals_cache.py --source data/preloaded/regional_capitals_top90_countries.json

# Validate coverage, coordinates, climate status, identifiers, and duplicates.
python scripts/validate_regional_capitals_top90.py

# Normalize a separately downloaded Natural Earth 1:110m Admin-0 GeoJSON.
python scripts/build_country_boundaries.py /path/to/ne_110m_admin_0_countries.geojson

# Run the focused behavior checks.
python -m pytest tests/test_temperature.py tests/test_regional_capitals.py tests/test_map_interactions.py
```

Approved refresh sources are Wikidata (CC0) for administrative metadata, English Wikipedia (CC BY-SA 4.0) for climate classification, native-language Wikipedia only as fallback, Wikidata climate classification as the final fallback, and Natural Earth Admin-0 boundaries (public domain). Generated files must be reviewed, validated, and committed before deployment.

## Local regional-capital and monthly metric coverage

The committed startup snapshot includes curated governorate/administrative centers for **Egypt**, district and major administrative centers for **Libya**, oblast capitals plus Kyiv, Crimea, and special-status cities for **Ukraine**, and provincial capitals for **Iran**. Ukraine records follow internationally recognized Ukrainian administrative naming; Simferopol and Sevastopol are retained with explicit Ukrainian administrative context without expressing a sovereignty judgment. For Qalyubia, Banha is stored as the governorate seat and Shubra El Kheima as a search alias. Libya uses the district/major-center level because district boundaries and seats have changed repeatedly.

Murmansk and Puno are permanent climate-classification regression cases. Murmansk uses the primary English Wikipedia subarctic (`Dfc`) classification and the Continental broad group. Puno retains its source Köppen code separately but uses the more informative `Highland / Mountain` broad group instead of presenting an Andean high-altitude city as a polar environment.

The sidebar's **Monthly map metric overlay** can show a selected January–December value beside every currently visible marker. Supported normalized metrics are average/high/low and record high/low temperature (always °C), precipitation and rainfall (mm), snowfall (source unit), precipitation and snow days, sunshine hours, and humidity (%). Missing values are omitted. Labels first use `data/preloaded/monthly_climate_metrics_cache.json`, joined by marker ID, Wikidata QID, or normalized city/country/administrative-region identity. Already-parsed local climate rows are a final fallback. Enabling labels never triggers bulk Wikipedia or Wikidata requests.

### Rebuilding local data

```bash
python scripts/build_priority_regional_capitals.py
python scripts/build_capital_climate_cache.py
python scripts/build_monthly_climate_metrics_cache.py
python scripts/validate_priority_regional_capitals.py
python scripts/validate_regional_capital_climates.py
python scripts/validate_monthly_climate_metrics.py
pytest
```

Builders are developer-only. Review source attribution and generated reports before committing refreshed caches; application startup remains local-first.
