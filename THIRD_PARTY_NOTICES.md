# Third-party software and data notices

CityClimate Explorer application code is licensed separately under the top-level [MIT `LICENSE`](LICENSE). This file covers direct third-party software, Wikimedia content/data, and map services. Commercial use is allowed for every reviewed direct dependency, subject to its notice requirements. Production releases must also inspect transitive dependencies from `requirements-lock.txt`.

## Direct software dependencies

| Package | Purpose | License | Commercial use | Project URL |
|---|---|---|---|---|
| Streamlit | Web application UI | Apache-2.0 | Allowed; retain required notices | https://github.com/streamlit/streamlit |
| streamlit-folium | Streamlit/Folium bridge | MIT | Allowed; retain copyright/license | https://github.com/randyzwitch/streamlit-folium |
| Folium | Interactive Leaflet map construction | MIT | Allowed; retain copyright/license | https://github.com/python-visualization/folium |
| Branca | Folium HTML elements and map legend support | MIT | Allowed; retain copyright/license | https://github.com/python-visualization/branca |
| Requests | Wikimedia HTTP client | Apache-2.0 | Allowed; retain required notices | https://github.com/psf/requests |
| pandas | Climate-table shaping/display | BSD-3-Clause | Allowed; retain copyright/license | https://github.com/pandas-dev/pandas |
| Beautiful Soup 4 (`beautifulsoup4`) | Rendered Wikipedia HTML parsing | MIT | Allowed; retain copyright/license | https://www.crummy.com/software/BeautifulSoup/ |
| mwparserfromhell | MediaWiki wikitext parsing | MIT | Allowed; retain copyright/license | https://github.com/earwig/mwparserfromhell |
| pytest | Development and compliance tests | MIT | Allowed; retain copyright/license | https://github.com/pytest-dev/pytest |

Altair is supplied transitively by Streamlit and is used for the selected-city temperature chart. Altair is BSD-3-Clause licensed and permits commercial use; see https://github.com/vega/altair. It remains pinned in `requirements-lock.txt` rather than duplicated as a direct requirement.

No GPL, AGPL, proprietary, paid, non-commercial, or unclear-license direct dependency is approved. Run `python scripts/audit_dependency_licenses.py --installed-metadata` before release. The reviewed direct-dependency allowlist does **not** replace a transitive dependency review; inspect every package in `requirements-lock.txt` whenever versions change.

## Data sources

### English and native-language Wikipedia

English Wikipedia is the primary source for climate tables and classifications. A native-language Wikipedia page is used only when English has no usable climate content. Wikipedia-derived parsed data is not a closed proprietary dataset.

- License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0); older contributions may also be available under GFDL.
- Commercial use: allowed with attribution and share-alike obligations.
- Attribution retained: source name, language, page title, URL, priority, retrieval timestamp when available, license URL, and page-history contributor link.
- URLs: https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use and https://creativecommons.org/licenses/by-sa/4.0/

Caches and any future export must preserve those fields and state that page history contains contributor attribution.

### Wikidata

Wikidata supplies QIDs, coordinates, population, country relationships, continent/country mapping, Wikipedia sitelinks, and climate classification only as the final fallback when Wikipedia has no usable classification.

- License: CC0 1.0 public-domain dedication.
- Commercial use: allowed.
- Attribution: not required by CC0, but retained for transparency.
- URLs: https://www.wikidata.org/wiki/Wikidata:Data_access and https://creativecommons.org/publicdomain/zero/1.0/

### Map tiles and OpenStreetMap data

The development/demo configuration uses a CARTO Positron endpoint with explicit CARTO and OpenStreetMap attribution. It is intentionally rejected when `CITYCLIMATE_DEPLOYMENT=production`. Production operators must configure a reviewed commercial provider (MapTiler, Mapbox, Stadia Maps, a CARTO paid plan through custom configuration) or self-hosted tiles, comply with provider terms, and retain the attribution shown by the map.

OpenStreetMap database content is under ODbL: https://www.openstreetmap.org/copyright. Provider rendering/service terms are separate and must be reviewed for the expected traffic and monetization model.

## Bundled records

See [`data/preloaded/SOURCES.md`](data/preloaded/SOURCES.md). Bundled Wikimedia-derived climate data remains under its upstream license. Do not strip source, license, retrieval, or contributor-history metadata from cache files or redistributed data.

### Bundled regional capitals and generalized climate zones

The regional-capital cache uses the same reviewed Wikimedia licensing policy described above: Wikidata-compatible structured metadata is CC0, while linked/reviewed Wikipedia material is CC BY-SA 4.0 with page-history attribution retained per record. The generated `climate_zones_simplified.geojson` is project-authored under the repository MIT license, permits commercial use, and is labeled in the UI and metadata as a schematic visual grouping rather than a scientific climate-boundary dataset. No new software dependency or third-party climate dataset was added.

## Beck et al. Köppen–Geiger climate classification data

- **Data:** Present and future Köppen-Geiger climate classification maps at 1-km resolution (present-day 1980–2016 map; locally generalized display derivative)
- **Authors:** Hylke E. Beck, Niklaus E. Zimmermann, Tim R. McVicar, Noemi Vergopolan, Alexis Berg, and Eric F. Wood
- **Dataset:** https://doi.org/10.6084/m9.figshare.6396959.v2
- **Article:** https://doi.org/10.1038/sdata.2018.214
- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/
- **Use in this project:** `data/preloaded/koppen_climate_zones_simplified.geojson`, a low-vertex cartographic generalization for optional map display. Commercial use is permitted with attribution.
