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
