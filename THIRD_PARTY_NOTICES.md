# Third-party software and data notices

CityClimate Explorer is designed for commercial use while respecting the licenses of its dependencies and data sources. This notice covers the project's **direct** dependencies; deployed builds should retain the license notices supplied by all transitive packages.

## Direct software dependencies

| Dependency | Purpose | License | Commercial use | Project/source |
|---|---|---|---|---|
| Streamlit | Web application UI | Apache-2.0 | Permitted; retain notices/license when redistributing | https://github.com/streamlit/streamlit |
| streamlit-folium | Streamlit/Folium bridge | MIT | Permitted; retain copyright/license | https://github.com/randyzwitch/streamlit-folium |
| Folium | Interactive maps | MIT | Permitted; retain copyright/license | https://github.com/python-visualization/folium |
| Requests | HTTP client | Apache-2.0 | Permitted; retain notices/license when redistributing | https://github.com/psf/requests |
| pandas | Climate-table display/data shaping | BSD-3-Clause | Permitted; retain copyright/license | https://github.com/pandas-dev/pandas |
| Beautiful Soup 4 (`beautifulsoup4`) | Rendered HTML parsing | MIT | Permitted; retain copyright/license | https://www.crummy.com/software/BeautifulSoup/ |
| mwparserfromhell | MediaWiki wikitext parsing | MIT | Permitted; retain copyright/license | https://github.com/earwig/mwparserfromhell |
| pytest | Development tests only | MIT | Permitted; retain copyright/license | https://github.com/pytest-dev/pytest |

No proprietary SDK, paid weather API, non-commercial package, GPL, or AGPL direct dependency is used. Package licenses should be rechecked before upgrading or adding dependencies.

## Data and services

### Wikipedia

Capital climate classifications are precomputed into a local cache by a developer script, while detailed monthly climate tables are fetched on demand through the MediaWiki API. Wikipedia text is available under the **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)** license and, for older contributions, the GNU Free Documentation License. Commercial reuse is allowed, but attribution and share-alike obligations apply to adapted Wikipedia content. CityClimate Explorer links to the exact source page and records the page title, URL, language, and source role with parsed results.

- Terms/licensing: https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use
- License: https://creativecommons.org/licenses/by-sa/4.0/

### Wikidata

City metadata, coordinates, country relationships, population, QIDs, and sitelinks originate from Wikidata. Normal runtime optional-city loading reads a reviewed local cache; live SPARQL is limited to an explicit developer refresh script. Wikidata structured data is released under **CC0 1.0**, which permits commercial reuse. The application still attributes Wikidata for transparency.

- Reuse guidance: https://www.wikidata.org/wiki/Wikidata:Data_access
- CC0 dedication: https://creativecommons.org/publicdomain/zero/1.0/

### OpenStreetMap map tiles

Folium's default OpenStreetMap-based tiles and the configured CartoDB Positron layer require attribution to their providers and OpenStreetMap contributors. Folium/Leaflet renders the provider attribution on the map. Production operators must comply with the selected tile provider's usage policy and should use a suitable commercial tile host when traffic exceeds public-service limits; the map data remains OpenStreetMap data under ODbL.

- OpenStreetMap copyright/ODbL: https://www.openstreetmap.org/copyright
- Carto attribution: https://carto.com/attributions

## Bundled and cached records

`data/preloaded/country_capitals.json` is local startup metadata and includes English Wikipedia source links where available. `data/capital_climate_cache.json` provides immediate startup classifications, and `data/top_non_capital_cities_by_country.json` provides bounded optional-city records without runtime SPARQL. These files preserve source name, source language, page title, source URL, and whether the result was English-primary, native-language fallback, Wikidata fallback, or unavailable. Wikipedia-derived cached labels remain subject to CC BY-SA attribution/share-alike; Wikidata fields are CC0. Do not remove source fields when exporting or redistributing records.
