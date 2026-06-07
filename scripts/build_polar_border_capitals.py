#!/usr/bin/env python3
"""Build the reviewed, local polar-border administrative-capital snapshot.

This developer-only builder deliberately uses a small reviewed seed rather than
performing broad runtime Wikimedia requests. Refresh coordinates/identity from
Wikidata and climate wording from linked Wikipedia pages before changing rows.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "preloaded" / "regional_capitals_polar_border.json"

# name, country/territory, continent, admin region, admin type, lat, lon,
# record type, primary Köppen, secondary codes, concise reviewed label
SEEDS = [
    ("Nuuk", "Greenland", "North America", "Sermersooq", "municipality", 64.1835, -51.7216, "regional_capital", "ET", [], "Tundra climate"),
    ("Sisimiut", "Greenland", "North America", "Qeqqata", "municipality", 66.9395, -53.6735, "local_administrative_center", "ET", [], "Tundra climate"),
    ("Ilulissat", "Greenland", "North America", "Avannaata", "municipality", 69.2198, -51.0986, "local_administrative_center", "ET", [], "Tundra climate"),
    ("Qaqortoq", "Greenland", "North America", "Kujalleq", "municipality", 60.7184, -46.0356, "local_administrative_center", "ET", ["Cfc"], "Tundra climate, bordering subpolar oceanic climate"),
    ("Tasiilaq", "Greenland", "North America", "Sermersooq", "municipality", 65.6145, -37.6368, "local_administrative_center", "ET", [], "Tundra climate"),
    ("Tromsø", "Norway", "Europe", "Troms", "county", 69.6492, 18.9553, "regional_capital", "Dfc", ["Cfc"], "Subarctic climate, bordering subpolar oceanic climate"),
    ("Bodø", "Norway", "Europe", "Nordland", "county", 67.2804, 14.4049, "regional_capital", "Cfc", [], "Subpolar oceanic climate"),
    ("Vadsø", "Norway", "Europe", "Finnmark", "county", 70.0744, 29.7487, "regional_capital", "Dfc", [], "Subarctic climate"),
    ("Alta", "Norway", "Europe", "Finnmark", "municipality", 69.9689, 23.2716, "local_administrative_center", "Dfc", [], "Subarctic climate"),
    ("Longyearbyen", "Svalbard", "Europe", "Svalbard", "territory", 78.2232, 15.6469, "local_administrative_center", "ET", [], "Tundra climate"),
    ("Luleå", "Sweden", "Europe", "Norrbotten County", "county", 65.5848, 22.1547, "regional_capital", "Dfc", [], "Subarctic climate"),
    ("Umeå", "Sweden", "Europe", "Västerbotten County", "county", 63.8258, 20.2630, "regional_capital", "Dfc", [], "Subarctic climate"),
    ("Östersund", "Sweden", "Europe", "Jämtland County", "county", 63.1792, 14.6357, "regional_capital", "Dfc", [], "Subarctic climate"),
    ("Rovaniemi", "Finland", "Europe", "Lapland", "region", 66.5039, 25.7294, "regional_capital", "Dfc", [], "Subarctic climate"),
    ("Oulu", "Finland", "Europe", "North Ostrobothnia", "region", 65.0121, 25.4651, "regional_capital", "Dfc", [], "Subarctic climate"),
    ("Akureyri", "Iceland", "Europe", "Northeastern Region", "region", 65.6885, -18.1262, "local_administrative_center", "Cfc", [], "Subpolar oceanic climate"),
    ("Ísafjörður", "Iceland", "Europe", "Westfjords", "region", 66.0748, -23.1340, "local_administrative_center", "Cfc", ["ET"], "Subpolar oceanic climate, bordering tundra climate"),
    ("Iqaluit", "Canada", "North America", "Nunavut", "territory", 63.7467, -68.5170, "regional_capital", "ET", [], "Tundra climate"),
    ("Yellowknife", "Canada", "North America", "Northwest Territories", "territory", 62.4540, -114.3718, "regional_capital", "Dfc", [], "Subarctic climate"),
    ("Whitehorse", "Canada", "North America", "Yukon", "territory", 60.7212, -135.0568, "regional_capital", "Dfc", [], "Subarctic climate"),
    ("St. John's", "Canada", "North America", "Newfoundland and Labrador", "province", 47.5615, -52.7126, "regional_capital", "Dfb", ["Cfb"], "Humid continental climate with oceanic influence"),
    ("Québec City", "Canada", "North America", "Quebec", "province", 46.8139, -71.2080, "regional_capital", "Dfb", [], "Humid continental climate"),
    ("Juneau", "United States", "North America", "Alaska", "state", 58.3019, -134.4197, "regional_capital", "Cfb", ["Dfb"], "Oceanic climate with continental influence"),
    ("Murmansk", "Russia", "Europe", "Murmansk Oblast", "federal subject", 68.9585, 33.0827, "regional_capital", "Dfc", [], "Subarctic climate"),
    ("Arkhangelsk", "Russia", "Europe", "Arkhangelsk Oblast", "federal subject", 64.5393, 40.5187, "regional_capital", "Dfc", [], "Subarctic climate"),
    ("Salekhard", "Russia", "Asia", "Yamalo-Nenets Autonomous Okrug", "federal subject", 66.5300, 66.6019, "regional_capital", "Dfc", [], "Subarctic climate"),
    ("Yakutsk", "Russia", "Asia", "Sakha", "federal subject", 62.0355, 129.6755, "regional_capital", "Dfd", [], "Extremely cold subarctic climate"),
    ("Anadyr", "Russia", "Asia", "Chukotka Autonomous Okrug", "federal subject", 64.7337, 177.5089, "regional_capital", "Dfc", [], "Subarctic climate"),
    ("Magadan", "Russia", "Asia", "Magadan Oblast", "federal subject", 59.5612, 150.8301, "regional_capital", "Dfc", [], "Subarctic climate"),
    ("Petropavlovsk-Kamchatsky", "Russia", "Asia", "Kamchatka Krai", "federal subject", 53.0370, 158.6559, "regional_capital", "Dfc", [], "Subarctic climate"),
    ("Ushuaia", "Argentina", "South America", "Tierra del Fuego", "province", -54.8019, -68.3030, "regional_capital", "ET", ["Cfc"], "Tundra climate, bordering subpolar oceanic climate"),
    ("Punta Arenas", "Chile", "South America", "Magallanes and Chilean Antarctica", "region", -53.1638, -70.9171, "regional_capital", "Cfc", ["BSk"], "Subpolar oceanic climate with dry influence"),
    ("Puerto Williams", "Chile", "South America", "Chilean Antarctic Province", "province", -54.9333, -67.6167, "local_administrative_center", "ET", ["Cfc"], "Tundra climate, bordering subpolar oceanic climate"),
    ("Tórshavn", "Faroe Islands", "Europe", "Streymoy", "island/municipality", 62.0079, -6.7900, "local_administrative_center", "Cfc", [], "Subpolar oceanic climate"),
]
COUNTRY_QIDS = {"Greenland":"Q223","Norway":"Q20","Svalbard":"Q25231","Sweden":"Q34","Finland":"Q33","Iceland":"Q189","Canada":"Q16","United States":"Q30","Russia":"Q159","Argentina":"Q414","Chile":"Q298","Faroe Islands":"Q4628"}
GROUPS = {"A":"Tropical", "B":"Dry / Arid", "C":"Temperate", "D":"Continental", "E":"Polar"}


def record(seed: tuple) -> dict:
    name, country, continent, admin, admin_type, lat, lon, record_type, primary, secondary, label = seed
    title = name.replace(" ", "_")
    url = f"https://en.wikipedia.org/wiki/{quote(title, safe='_(,).') }"
    return {
        "name": name, "country": country, "country_qid": COUNTRY_QIDS.get(country),
        "administrative_region": admin, "administrative_region_type": admin_type,
        "administrative_region_qid": None, "latitude": lat, "longitude": lon,
        "population": None, "qid": None, "continent": continent, "region": continent,
        "wikipedia_title": name, "wikipedia_url": url, "record_type": record_type,
        "record_scope": "polar_border_regional_capital", "climate_classification": primary,
        "primary_koppen_code": primary, "secondary_koppen_codes": secondary,
        "climate_classification_label": label, "climate_group": GROUPS[primary[0]],
        "climate_source_excerpt": f"Primary Köppen {primary}" + (f"; bordering/secondary {', '.join(secondary)}" if secondary else ""),
        "climate_classification_source": "reviewed_english_wikipedia_snapshot",
        "climate_extraction_status": "reviewed primary/secondary Köppen classification in bundled offline snapshot",
        "climate_classification_source_metadata": {
            "source_name": "English Wikipedia", "source_language": "en", "source_page_title": name,
            "source_url": url, "source_priority": "english_primary", "source_role": "offline_startup_classification",
            "license": "CC BY-SA 4.0", "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "contributors_url": f"{url}?action=history", "retrieved_at": "2026-06-07",
        },
        "provenance": {
            "metadata_source_name": "Wikidata-compatible reviewed seed", "metadata_source_url": "https://www.wikidata.org/",
            "metadata_license": "CC0 1.0", "metadata_license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "climate_source_name": "English Wikipedia", "climate_source_url": url,
            "climate_license": "CC BY-SA 4.0", "climate_license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "commercial_use_status": "permitted with Wikipedia attribution/share-alike compliance",
            "processing_steps": ["review administrative role", "review primary and bordering Köppen codes", "serialize local startup cache"],
        },
    }


def main() -> None:
    payload = {
        "schema_version": 2, "generated_at": datetime.now(timezone.utc).isoformat(),
        "inclusion_rule": "Administrative capitals/centers in countries or territories bordering, containing, or strongly adjacent to polar climate zones; not a general city list.",
        "source_metadata": {"metadata_source": "Wikidata", "metadata_license": "CC0 1.0", "climate_source": "English Wikipedia", "climate_license": "CC BY-SA 4.0", "runtime_network_required": False},
        "records": [record(seed) for seed in SEEDS],
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload['records'])} records to {OUTPUT}")


if __name__ == "__main__":
    main()
