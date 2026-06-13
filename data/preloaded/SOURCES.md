# Preloaded data sources

## Curated classification corrections

`climate_classification_overrides.json` contains a deliberately small set of
reviewed conflict resolutions. Each record retains its Wikimedia source URL,
language, reason, review date, license, and contributor-history attribution.
The runtime applies these records after the local climate cache so a lower
priority code-derived or Wikidata label cannot overwrite verified English
Wikipedia climate prose. This file is not a general substitute for parsing.

## `top_90_countries_by_area.json`

- **Selection/source:** first 90 ranked sovereign-state rows by total area from [Wikipedia: List of countries and dependencies by area](https://en.wikipedia.org/wiki/List_of_countries_and_dependencies_by_area), reviewed 2026-06-08. Unranked Antarctica, dependencies, and disputed entries are excluded.
- **Upstream provenance:** the reference page documents United Nations Statistics Division totals, FAO land/water values, CIA World Factbook reconciliation, and row-specific official sources.
- **License:** Wikipedia text/table compilation is CC BY-SA 4.0; country QIDs and linked structured metadata are Wikidata CC0 1.0.
- **Runtime:** deterministic local JSON only; no API request determines the ranking at startup.
- **Commercial use:** permitted subject to CC BY-SA attribution/share-alike obligations for Wikipedia-derived compilation content.

## `regional_capitals_top90_countries.json`

- **Coverage:** first-level administrative-region capitals/centers for all 90 countries in the local area reference. The complete reviewed top-15 snapshot is retained; ranks 16–90 contain reviewed representative first-level centers and are ready for explicit developer enrichment. This is not a general city dataset.
- **Metadata source/provenance:** Wikidata-compatible region/capital identity, coordinates, country relationships, optional QIDs/populations/sitelinks; CC0 1.0.
- **Climate source order:** English Wikipedia (CC BY-SA 4.0), native-language Wikipedia fallback, then Wikidata final fallback. Unknown startup classifications retain an explicit unavailable reason and are never treated as fabricated climate values.
- **Runtime:** loaded from disk only. Climate tables are requested/cached only after a user selects a city.
- **Build/validation:** `python scripts/build_top90_country_list.py`, `python scripts/build_regional_capitals_cache.py`, `python scripts/validate_regional_capitals.py`, `python scripts/validate_regional_capital_climates.py`, and `pytest tests/test_temperature.py`.

## `regional_capitals_priority_countries.json`

- **Coverage:** maintainer-curated administrative-capital seed lists for Poland, Spain, France, Norway, Sweden, Finland, Germany, and Türkiye. France includes 13 metropolitan and five overseas regional capitals; Türkiye includes all 81 provincial capitals. Shared seats and documented local administrative centers are retained.
- **Inclusion policy:** the committed seed list is authoritative. Developer enrichment may add QIDs, region QIDs, and improved source metadata, but a failed lookup must never delete an expected city.
- **Climate policy:** precomputed English-Wikipedia-reviewed classifications are bundled. English Wikipedia is primary, native-language Wikipedia fallback, and Wikidata final fallback. The primary Köppen code controls the broad group: `Dfc/Dfd/Dwc/Dwd/Dsc/Dsd` are Continental/subarctic, `ET/EF` are Polar, and `Cfc` is Temperate/subpolar oceanic unless an explicit primary `ET` source supersedes it.
- **Runtime:** local JSON only; no Wikipedia or Wikidata discovery runs at startup.
- **Licenses:** linked Wikipedia climate descriptions are CC BY-SA 4.0 with page-history attribution; Wikidata-compatible structured metadata is CC0 1.0. Commercial use is permitted subject to those terms.
- **Build/validation:** `python scripts/build_priority_regional_capitals.py` and `python scripts/validate_priority_regional_capitals.py`.
- **Expanded 2026 priority coverage:** Switzerland, South Africa, Austria, Angola, Namibia, Ecuador, Peru, Chile, and Japan are maintained as explicit country seed lists. Japan contains all 47 prefectural capitals; Switzerland contains all 26 canton seats. Namibia uses Otjiwarongo for Otjozondjupa, Nkurenkuru for Kavango West, Omuthiya for Oshikoto, and Swakopmund for Erongo; Walvis Bay is retained separately as an important local administrative center.
- **Relationship and coordinate provenance:** administrative relationships and city-center coordinates are maintainer-reviewed facts compatible with Wikidata's CC0 metadata model. Optional developer enrichment may refresh QIDs, coordinates, and sitelinks from Wikidata, but failed enrichment never controls inclusion and runtime never performs discovery.
- **Climate provenance:** reviewed primary Köppen classifications are derived from the linked English Wikipedia city pages (CC BY-SA 4.0), with native-language Wikipedia as a developer-only fallback and Wikidata as the final metadata fallback. Primary codes alone control broad groups; secondary/bordering codes cannot replace them. Missing climate information must be retained with an explicit extraction status.
- **Build report:** `data/preloaded/regional_capitals_priority_build_report.json` records countries processed, records created/enriched, missing classifications/coordinates, curated highland overrides, and validation failures.

# Bundled dataset provenance

This directory contains startup seed data, not a proprietary climate database. Factual metadata is bundled to make startup deterministic, while Wikimedia-derived content retains source and license metadata. Do not remove provenance fields when refreshing, caching, exporting, or redistributing these files.

## `country_capitals.json`

Each record has a `provenance` object. The record-level English Wikipedia page is retained as the reviewable city/capital reference. Where a Wikidata entity or country QID was available during compilation, its entity URL is retained as well.

| Bundled field | Upstream/source | License/status | Notes |
|---|---|---|---|
| `name`, `country`, capital relationship | Linked English Wikipedia city page; curated factual seed | CC BY-SA 4.0 for Wikipedia text; bare facts may not be copyrightable | `record_source_*` identifies the linked page and language. |
| `latitude`, `longitude` | Wikidata-oriented seed/refresh workflow | CC0 1.0 | Future refreshes must use documented Wikidata statements or another explicitly reviewed source. |
| `qid`, `country_qid` | Wikidata | CC0 1.0 | Entity URLs are stored when QIDs are present. |
| `continent` / `region`, country relationship | Wikidata-oriented seed/refresh workflow | CC0 1.0 | The UI uses region as continent. |
| `population` | Wikidata-oriented seed/refresh workflow | CC0 1.0 | Values can be absent; no live production lookup is required. |
| `wikipedia_title`, `wikipedia_url` | English Wikipedia sitelink/reference | Link metadata is factual; linked page content is CC BY-SA 4.0 | English is the primary climate source. |
| seed `climate_classification` / label | Wikidata fallback claim where present | CC0 1.0 | It is used only after English and native-language Wikipedia have no usable classification. Runtime classifications come from `../capital_climate_cache.json`. |

Some older seed rows do not yet have a city QID. Their linked English Wikipedia page remains the record-level provenance reference, and the `wikidata_license` field records the license governing fields produced by the Wikidata refresh workflow. Maintainers should populate missing QIDs from Wikidata during a reviewed refresh rather than infer them silently.

## `expected_sovereign_capitals.json`

This is a repository-maintained integrity manifest of country/capital names used to detect accidental removal from the runtime seed. It contains factual names only and is distributed under the application code's MIT license. It must not be treated as a separate authoritative geopolitical dataset.

## Related bundled caches

- `../capital_climate_cache.json`: classification records follow `english_primary`, `native_fallback`, `wikidata_fallback`, or `unavailable`. Wikipedia-derived rows include page URL, title, language, retrieval timestamp, CC BY-SA 4.0 URL, and page-history contributor link. Wikidata fallback rows are CC0 1.0.

## Refresh and validation policy

Allowed primary sources are English Wikipedia, native-language Wikipedia only as fallback, and Wikidata. Do not add a proprietary, paid, non-commercial, research-only, personal-use-only, or unclear-license source. Any proposed source must document its name, URL, license, commercial-use status, and attribution obligations before data is committed.

Run:

```bash
python scripts/validate_provenance.py
python scripts/validate_capitals.py
```

## `regional_capitals_top15_countries.json`

This generated startup cache contains only capitals/seats of first-level administrative divisions for the documented 15-country area list; it is not a general city dataset. Each row includes country and administrative-region identity, region type, coordinates, optional QID/population fields, a linked English Wikipedia title/URL where available, normalized climate fields, `record_type: regional_capital`, and complete provenance/license metadata.

- **Metadata refresh source:** Wikidata, https://www.wikidata.org/, CC0 1.0. Commercial use is permitted.
- **Climate source order:** English Wikipedia (CC BY-SA 4.0), native-language Wikipedia only as fallback, Wikidata (CC0) only as a final fallback. The committed reviewed snapshot uses broad startup classifications and retains a refresh status when a more specific Köppen subtype remains to be resolved.
- **Attribution:** Wikipedia-derived/reviewed rows retain source page, language, URL, license, and page-history contributor link. Wikidata attribution is retained for transparency despite CC0.
- **Processing:** select first-level administrative divisions and their capitals; normalize country/region types; attach coordinates and identity fields; normalize broad climate groups; deduplicate by city QID, then normalized city/country/region; serialize for runtime-only local loading.
- **Limitations:** some optional QIDs, administrative-region QIDs, and populations remain null in the reviewed seed and should be populated only by a verified developer refresh. National-capital rows remain authoritative when roles overlap.

Rebuild and validate:

```bash
python scripts/build_regional_capitals_cache.py
python scripts/validate_regional_capitals.py
```

## `regional_capitals_polar_border.json`

This reviewed local snapshot adds only administrative capitals/centers for countries and territories bordering, containing, or strongly adjacent to polar climate zones. It covers Greenland, Norway, Sweden, Finland, Iceland, Arctic/subarctic Canada, Alaska, Russia, southern Argentina/Chile, Svalbard, and the Faroe Islands. It is not a general city dataset. Records use `record_scope: polar_border_regional_capital` and either `regional_capital` or `local_administrative_center` record type.

- **Metadata/provenance:** reviewed Wikidata-compatible factual seed, CC0 1.0; coordinates, country/territory identity, administrative role, and linked identity fields retain record provenance.
- **Climate source:** linked English Wikipedia page, CC BY-SA 4.0, with page-history attribution. Native-language Wikipedia and Wikidata remain permitted only as the documented fallback order during developer refreshes.
- **Climate model:** `primary_koppen_code` determines `climate_group`; `secondary_koppen_codes` records bordering, transitional, or influence codes without changing marker color. A short normalized note is retained for debugging.
- **Runtime:** the application reads this generated file from disk. The builder and audit are developer-only and are never called during Streamlit startup.
- **Commercial use:** Wikidata CC0 facts and Wikipedia CC BY-SA content are commercially usable subject to the retained attribution/share-alike obligations. No proprietary climate or weather API is used.

Rebuild and audit:

```bash
python scripts/build_polar_border_capitals.py
python scripts/validate_regional_capitals.py
python scripts/validate_regional_capital_climates.py
```

`regional_capital_climate_audit.json` is a generated review report covering both regional datasets. Review findings identify legacy broad classifications without a detected primary subtype; error findings identify missing classifications/groups, primary-code/group mismatches, or conflicting primary/secondary fields.

## `climate_zones_simplified.geojson`

The climate-zone layer is a project-authored, deliberately schematic visualization of broad climate grouping. It uses non-overlapping latitude bands plus a very small number of generalized dry and highland overlays. It is not represented as scientific Köppen-Geiger boundary data and must not be used for site-level analysis.

- **Source name:** CityClimate Explorer generalized broad-climate visualization.
- **Source URL:** https://github.com/azagorowski/CityClimate-Explorer
- **License:** MIT, https://opensource.org/license/mit
- **Commercial use:** permitted.
- **Attribution:** CityClimate Explorer contributors.
- **Processing:** define broad latitude bands; add generalized dry/highland overlays; group into the same seven UI categories; serialize low-vertex GeoJSON. The generated file is about 10 KB and is loaded only from disk.

Rebuild with:

```bash
python scripts/build_climate_zones.py
```

## `koppen_climate_zones_simplified.geojson`

This runtime-only detailed layer is a deliberately low-vertex cartographic generalization of the present-day (1980–2016) Köppen–Geiger map published by Beck et al. (2018). It provides representative polygons with `koppen_code`, `koppen_name`, `climate_group`, and display-color properties. The generalized and sometimes overlapping shapes are for interactive visual context only; they are not site-level or scientific boundary data.

- **Source:** Hylke E. Beck, Niklaus E. Zimmermann, Tim R. McVicar, Noemi Vergopolan, Alexis Berg, and Eric F. Wood, “Present and future Köppen-Geiger climate classification maps at 1-km resolution,” *Scientific Data* 5:180214 (2018).
- **Dataset DOI:** https://doi.org/10.6084/m9.figshare.6396959.v2
- **Article DOI:** https://doi.org/10.1038/sdata.2018.214
- **License:** CC BY 4.0, https://creativecommons.org/licenses/by/4.0/
- **Commercial use:** permitted with attribution.
- **Attribution:** Beck et al. (2018), generalized by CityClimate Explorer contributors.
- **Processing:** review the published present-day 0.5-degree map; generalize representative climate-type extents into low-vertex polygons; attach Köppen codes, names, broad groups, and colors; serialize a compact local GeoJSON.
- **Runtime:** loaded only from `data/preloaded/koppen_climate_zones_simplified.geojson`; startup and layer toggling perform no data download or Wikimedia request.
- **Limitations:** the layer is intentionally simplified, includes overlapping representative extents, and must not be used to classify a precise location.

Rebuild the committed local asset with:

```bash
python scripts/build_koppen_climate_zones.py
```

## `top_90_countries_by_area.json`

- **Source:** English Wikipedia, “List of countries and dependencies by area,” with the upstream official sources identified by that table.
- **License:** CC BY-SA 4.0 for the reference-page presentation; country names, ranks, identifiers, and area facts are retained with row-level source metadata.
- **Selection:** exactly the first 90 ranked sovereign states by total area; dependencies, Antarctica, and unranked/disputed rows are excluded by the documented deterministic rule.
- **Runtime:** local file only; no startup request is made.

## `regional_capitals_top90_countries.json` (schema 3)

The cache contains reviewed first-level administrative capitals for the top-90 reference and an explicit `country_processing_status` entry for every country. Each status records completion state, whether first-level divisions exist, record count, missing-coordinate/climate counts, and a documented coverage reason. Records retain stable IDs, coordinates, administrative-region names/types, record types, climate status, and field-level source/provenance metadata where available.

The refresh order is Wikidata (CC0 1.0) for region/capital metadata, QIDs, coordinates, and sitelinks; English Wikipedia (CC BY-SA 4.0) for climate classification; native-language Wikipedia only as fallback; and Wikidata climate classification only as the final fallback. `scripts/build_regional_capitals_cache.py` is developer-only. Runtime reads the committed JSON and does not perform broad Wikimedia discovery.

Validate with:

```bash
python scripts/validate_regional_capitals_top90.py
```

The generated report lists complete countries, documented no-division/no-capital cases, missing coordinates, missing climate data, duplicate records, and validation errors.

## `country_boundaries_simplified.geojson`

- **Approved boundary source for rebuilds:** Natural Earth, Admin 0 – Countries, 1:110m, https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/
- **License:** public domain; commercial use permitted.
- **Committed processing:** low-vertex country extent features and normalized country lookup fields are stored locally for responsive Leaflet `fitBounds` behavior. The developer normalizer preserves Natural Earth geometry when supplied with the downloaded GeoJSON and strips properties to name, ISO, and Wikidata lookup identifiers.
- **Runtime:** loaded only from disk; no boundary download occurs during startup.
- **Purpose/limitations:** interactive selected-country context and highlighting only, not legal, navigational, or high-resolution cartography.

Rebuild after separately obtaining the approved upstream file:

```bash
python scripts/build_country_boundaries.py /path/to/ne_110m_admin_0_countries.geojson
```

## Monthly climate tables and Celsius chart normalization

Monthly table rows are parsed from the linked Wikipedia climate source under CC BY-SA 4.0 and retain page/source metadata. The annual chart is a derived display: Celsius rows are used directly; Fahrenheit rows are converted with `(F - 32) × 5/9`; Celsius wins when both units are present; only January through December are plotted. No external weather API or guessed values are used.
