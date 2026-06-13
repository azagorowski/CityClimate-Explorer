#!/usr/bin/env python3
"""Build the reviewed, local-first regional-capital snapshot for priority countries.

The rows below are the source of truth.  A future enrichment command may fill
optional QIDs, but must never use discovery results to decide which rows exist.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/preloaded/regional_capitals_priority_countries.json"

# country|city|administrative region|latitude|longitude[|Köppen|type|aliases]
SEEDS = """
Poland|Białystok|Podlaskie Voivodeship|53.1325|23.1688|Dfb
Poland|Bydgoszcz|Kuyavian-Pomeranian Voivodeship|53.1235|18.0084|Dfb
Poland|Toruń|Kuyavian-Pomeranian Voivodeship|53.0138|18.5984|Dfb
Poland|Gdańsk|Pomeranian Voivodeship|54.3520|18.6466|Cfb
Poland|Gorzów Wielkopolski|Lubusz Voivodeship|52.7368|15.2288|Cfb
Poland|Zielona Góra|Lubusz Voivodeship|51.9356|15.5062|Cfb
Poland|Katowice|Silesian Voivodeship|50.2649|19.0238|Cfb
Poland|Kielce|Świętokrzyskie Voivodeship|50.8661|20.6286|Dfb
Poland|Kraków|Lesser Poland Voivodeship|50.0647|19.9450|Cfb|||Krakow
Poland|Lublin|Lublin Voivodeship|51.2465|22.5684|Dfb
Poland|Łódź|Łódź Voivodeship|51.7592|19.4560|Cfb|||Lodz
Poland|Olsztyn|Warmian-Masurian Voivodeship|53.7784|20.4801|Dfb
Poland|Opole|Opole Voivodeship|50.6751|17.9213|Cfb
Poland|Poznań|Greater Poland Voivodeship|52.4064|16.9252|Cfb|||Poznan
Poland|Rzeszów|Podkarpackie Voivodeship|50.0412|21.9991|Dfb
Poland|Szczecin|West Pomeranian Voivodeship|53.4285|14.5528|Cfb
Poland|Warsaw|Masovian Voivodeship|52.2297|21.0122|Dfb
Poland|Wrocław|Lower Silesian Voivodeship|51.1079|17.0385|Cfb|||Wroclaw
Germany|Berlin|Berlin|52.5200|13.4050|Cfb
Germany|Bremen|Bremen|53.0793|8.8017|Cfb
Germany|Dresden|Saxony|51.0504|13.7373|Cfb
Germany|Düsseldorf|North Rhine-Westphalia|51.2277|6.7735|Cfb|||Dusseldorf
Germany|Erfurt|Thuringia|50.9848|11.0299|Cfb
Germany|Hamburg|Hamburg|53.5511|9.9937|Cfb
Germany|Hanover|Lower Saxony|52.3759|9.7320|Cfb|||Hannover
Germany|Kiel|Schleswig-Holstein|54.3233|10.1228|Cfb
Germany|Magdeburg|Saxony-Anhalt|52.1205|11.6276|Cfb
Germany|Mainz|Rhineland-Palatinate|49.9929|8.2473|Cfb
Germany|Munich|Bavaria|48.1351|11.5820|Cfb|||München
Germany|Potsdam|Brandenburg|52.3906|13.0645|Cfb
Germany|Saarbrücken|Saarland|49.2402|6.9969|Cfb|||Saarbrucken
Germany|Schwerin|Mecklenburg-Vorpommern|53.6355|11.4012|Cfb
Germany|Stuttgart|Baden-Württemberg|48.7758|9.1829|Cfb
Germany|Wiesbaden|Hesse|50.0782|8.2398|Cfb
Spain|Madrid|Community of Madrid|40.4168|-3.7038|Csa
Spain|Barcelona|Catalonia|41.3874|2.1686|Csa
Spain|Valencia|Valencian Community|39.4699|-0.3763|Csa
Spain|Seville|Andalusia|37.3891|-5.9845|Csa
Spain|Zaragoza|Aragon|41.6488|-0.8891|BSk
Spain|Mérida|Extremadura|38.9170|-6.3435|Csa|||Merida
Spain|Santiago de Compostela|Galicia|42.8782|-8.5448|Cfb
Spain|Oviedo|Asturias|43.3619|-5.8494|Cfb
Spain|Santander|Cantabria|43.4623|-3.8099|Cfb
Spain|Logroño|La Rioja|42.4627|-2.4449|Cfb|||Logrono
Spain|Pamplona|Navarre|42.8125|-1.6458|Cfb
Spain|Vitoria-Gasteiz|Basque Country|42.8467|-2.6727|Cfb|||Vitoria
Spain|Valladolid|Castile and León|41.6523|-4.7245|Csb
Spain|Toledo|Castilla–La Mancha|39.8628|-4.0273|BSk
Spain|Murcia|Region of Murcia|37.9922|-1.1307|BSh
Spain|Palma|Balearic Islands|39.5696|2.6502|Csa
Spain|Las Palmas de Gran Canaria|Canary Islands|28.1235|-15.4363|BWh
Spain|Santa Cruz de Tenerife|Canary Islands|28.4636|-16.2518|BSh
Spain|Ceuta|Ceuta|35.8894|-5.3213|Csa
Spain|Melilla|Melilla|35.2923|-2.9381|BSh
France|Paris|Île-de-France|48.8566|2.3522|Cfb
France|Lyon|Auvergne-Rhône-Alpes|45.7640|4.8357|Cfa
France|Marseille|Provence-Alpes-Côte d’Azur|43.2965|5.3698|Csa
France|Toulouse|Occitanie|43.6047|1.4442|Cfa
France|Bordeaux|Nouvelle-Aquitaine|44.8378|-0.5792|Cfb
France|Nantes|Pays de la Loire|47.2184|-1.5536|Cfb
France|Rennes|Brittany|48.1173|-1.6778|Cfb
France|Lille|Hauts-de-France|50.6292|3.0573|Cfb
France|Strasbourg|Grand Est|48.5734|7.7521|Cfb
France|Dijon|Bourgogne-Franche-Comté|47.3220|5.0415|Cfb
France|Orléans|Centre-Val de Loire|47.9030|1.9093|Cfb|||Orleans
France|Rouen|Normandy|49.4431|1.0993|Cfb
France|Ajaccio|Corsica|41.9192|8.7386|Csa
France|Basse-Terre|Guadeloupe|15.9958|-61.7292|Af
France|Cayenne|French Guiana|4.9224|-52.3135|Af
France|Fort-de-France|Martinique|14.6161|-61.0588|Af
France|Saint-Denis|Réunion|-20.8789|55.4481|Am
France|Mamoudzou|Mayotte|-12.7806|45.2278|Aw
Norway|Oslo|Oslo|59.9139|10.7522|Dfb
Norway|Bergen|Vestland|60.3913|5.3221|Cfb
Norway|Stavanger|Rogaland|58.9700|5.7331|Cfb
Norway|Trondheim|Trøndelag|63.4305|10.3951|Dfc
Norway|Tromsø|Troms|69.6492|18.9553|Dfc
Norway|Bodø|Nordland|67.2804|14.4049|Cfc
Norway|Vadsø|Finnmark|70.0745|29.7487|Dfc
Norway|Kristiansand|Agder|58.1599|8.0182|Cfb
Norway|Drammen|Buskerud|59.7441|10.2045|Dfb
Norway|Lillehammer|Innlandet|61.1153|10.4662|Dfc
Norway|Molde|Møre og Romsdal|62.7375|7.1607|Cfb
Norway|Steinkjer|Trøndelag|64.0149|11.4954|Dfc|local_administrative_center
Norway|Skien|Telemark|59.2096|9.6090|Dfb
Norway|Tønsberg|Vestfold|59.2675|10.4076|Cfb|||Tonsberg
Norway|Hamar|Innlandet|60.7945|11.0679|Dfb|local_administrative_center
Norway|Leikanger|Vestland|61.1856|6.8508|Cfb|local_administrative_center
Norway|Hermansverk|Vestland|61.1846|6.8500|Cfb|local_administrative_center
Norway|Ålesund|Møre og Romsdal|62.4722|6.1495|Cfb|local_administrative_center|Alesund
Sweden|Stockholm|Stockholm County|59.3293|18.0686|Dfb
Sweden|Gothenburg|Västra Götaland County|57.7089|11.9746|Cfb|||Göteborg
Sweden|Malmö|Skåne County|55.6050|13.0038|Cfb|||Malmo
Sweden|Uppsala|Uppsala County|59.8586|17.6389|Dfb
Sweden|Linköping|Östergötland County|58.4108|15.6214|Dfb
Sweden|Örebro|Örebro County|59.2753|15.2134|Dfb|||Orebro
Sweden|Västerås|Västmanland County|59.6099|16.5448|Dfb|||Vasteras
Sweden|Luleå|Norrbotten County|65.5848|22.1567|Dfc|||Lulea
Sweden|Umeå|Västerbotten County|63.8258|20.2630|Dfc|||Umea
Sweden|Östersund|Jämtland County|63.1767|14.6361|Dfc|||Ostersund
Sweden|Karlstad|Värmland County|59.3793|13.5036|Dfb
Sweden|Falun|Dalarna County|60.6065|15.6355|Dfc
Sweden|Gävle|Gävleborg County|60.6749|17.1413|Dfb|||Gavle
Sweden|Härnösand|Västernorrland County|62.6323|17.9404|Dfc|||Harnosand
Sweden|Jönköping|Jönköping County|57.7826|14.1618|Dfb|||Jonkoping
Sweden|Kalmar|Kalmar County|56.6634|16.3568|Cfb
Sweden|Karlskrona|Blekinge County|56.1612|15.5869|Cfb
Sweden|Kristianstad|Skåne County|56.0294|14.1567|Cfb|local_administrative_center
Sweden|Nyköping|Södermanland County|58.7528|17.0092|Dfb|||Nykoping
Sweden|Växjö|Kronoberg County|56.8790|14.8059|Cfb|||Vaxjo
Sweden|Visby|Gotland County|57.6348|18.2948|Cfb
Sweden|Halmstad|Halland County|56.6745|12.8578|Cfb
Sweden|Kiruna|Kiruna Municipality|67.8558|20.2253|Dfc|local_administrative_center
Finland|Helsinki|Uusimaa|60.1699|24.9384|Dfb
Finland|Turku|Southwest Finland|60.4518|22.2666|Dfb
Finland|Tampere|Pirkanmaa|61.4978|23.7610|Dfb
Finland|Oulu|North Ostrobothnia|65.0121|25.4651|Dfc
Finland|Rovaniemi|Lapland|66.5039|25.7294|Dfc
Finland|Kuopio|North Savo|62.8924|27.6770|Dfc
Finland|Jyväskylä|Central Finland|62.2426|25.7473|Dfc|||Jyvaskyla
Finland|Lahti|Päijät-Häme|60.9827|25.6615|Dfb
Finland|Pori|Satakunta|61.4851|21.7974|Dfb
Finland|Vaasa|Ostrobothnia|63.0951|21.6165|Dfb
Finland|Joensuu|North Karelia|62.6010|29.7636|Dfc
Finland|Hämeenlinna|Kanta-Häme|60.9959|24.4643|Dfb|||Hameenlinna
Finland|Mikkeli|South Savo|61.6878|27.2736|Dfc
Finland|Seinäjoki|South Ostrobothnia|62.7903|22.8403|Dfb|||Seinajoki
Finland|Kokkola|Central Ostrobothnia|63.8385|23.1307|Dfb
Finland|Kajaani|Kainuu|64.2273|27.7285|Dfc
Finland|Mariehamn|Åland|60.0973|19.9348|Cfb
Finland|Lappeenranta|South Karelia|61.0587|28.1887|Dfb
""".strip()

# Full 81-province seed. Coordinates are reviewed city-centre coordinates,
# intentionally bundled so a failed enrichment cannot remove a province.
TURKEY = """
Adana,37.0000,35.3213;Adıyaman,37.7648,38.2786;Afyonkarahisar,38.7507,30.5567;Ağrı,39.7191,43.0503;Aksaray,38.3687,34.0370;Amasya,40.6499,35.8353;Ankara,39.9334,32.8597;Antalya,36.8969,30.7133;Ardahan,41.1105,42.7022;Artvin,41.1828,41.8183;Aydın,37.8450,27.8396;Balıkesir,39.6484,27.8826;Bartın,41.5811,32.4610;Batman,37.8812,41.1351;Bayburt,40.2552,40.2249;Bilecik,40.1501,29.9831;Bingöl,38.8854,40.4980;Bitlis,38.4006,42.1095;Bolu,40.7395,31.6116;Burdur,37.7203,30.2908;Bursa,40.1885,29.0610;Çanakkale,40.1553,26.4142;Çankırı,40.6013,33.6134;Çorum,40.5506,34.9556;Denizli,37.7765,29.0864;Diyarbakır,37.9144,40.2306;Düzce,40.8438,31.1565;Edirne,41.6818,26.5623;Elazığ,38.6810,39.2264;Erzincan,39.7500,39.5000;Erzurum,39.9043,41.2679;Eskişehir,39.7767,30.5206;Gaziantep,37.0662,37.3833;Giresun,40.9128,38.3895;Gümüşhane,40.4386,39.5086;Hakkâri,37.5744,43.7408;Hatay,36.2025,36.1606;Iğdır,39.8880,44.0048;Isparta,37.7648,30.5566;Istanbul,41.0082,28.9784;İzmir,38.4237,27.1428;Kahramanmaraş,37.5753,36.9228;Karabük,41.2061,32.6204;Karaman,37.1759,33.2287;Kars,40.6013,43.0975;Kastamonu,41.3887,33.7827;Kayseri,38.7312,35.4787;Kilis,36.7184,37.1212;Kırıkkale,39.8468,33.5153;Kırklareli,41.7351,27.2252;Kırşehir,39.1425,34.1709;Kocaeli,40.8533,29.8815;Konya,37.8746,32.4932;Kütahya,39.4167,29.9833;Malatya,38.3552,38.3095;Manisa,38.6191,27.4289;Mardin,37.3212,40.7245;Mersin,36.8121,34.6415;Muğla,37.2153,28.3636;Muş,38.9462,41.7539;Nevşehir,38.6244,34.7239;Niğde,37.9698,34.6766;Ordu,40.9839,37.8764;Osmaniye,37.0742,36.2478;Rize,41.0201,40.5234;Sakarya,40.7569,30.3781;Samsun,41.2867,36.3300;Şanlıurfa,37.1674,38.7955;Siirt,37.9333,41.9500;Sinop,42.0231,35.1531;Sivas,39.7477,37.0179;Şırnak,37.4187,42.4918;Tekirdağ,40.9780,27.5110;Tokat,40.3167,36.5500;Trabzon,41.0015,39.7178;Tunceli,39.1079,39.5401;Uşak,38.6823,29.4082;Van,38.4891,43.4089;Yalova,40.6500,29.2667;Yozgat,39.8181,34.8147;Zonguldak,41.4564,31.7987
""".strip()

COUNTRY_META = {
    "Poland": ("Q36", "Europe", "voivodeship"),
    "Germany": ("Q183", "Europe", "federal state"),
    "Spain": ("Q29", "Europe", "autonomous community or autonomous city"),
    "France": ("Q142", "Europe", "region"),
    "Norway": ("Q20", "Europe", "county"),
    "Sweden": ("Q34", "Europe", "county"),
    "Finland": ("Q33", "Europe", "region"),
    "Türkiye": ("Q43", "Asia", "province"),
}

KOPPEN_LABELS = {
    "Af": "Tropical rainforest climate", "Am": "Tropical monsoon climate", "Aw": "Tropical savanna climate",
    "BWh": "Hot desert climate", "BSh": "Hot semi-arid climate", "BSk": "Cold semi-arid climate",
    "Csa": "Hot-summer Mediterranean climate", "Csb": "Warm-summer Mediterranean climate",
    "Cfa": "Humid subtropical climate", "Cfb": "Temperate oceanic climate", "Cfc": "Subpolar oceanic climate",
    "Dfb": "Warm-summer humid continental climate", "Dfc": "Subarctic climate",
}


def broad_group(code: str) -> str:
    if code.startswith("A"):
        return "Tropical"
    if code.startswith("B"):
        return "Dry / Arid"
    if code in {"ET", "EF"}:
        return "Polar"
    if code.startswith("D"):
        return "Continental"
    return "Temperate"


def parse_seeds() -> list[tuple[str, str, str, float, float, str, str, list[str]]]:
    rows = []
    for line in SEEDS.splitlines():
        parts = line.split("|")
        parts += [""] * (8 - len(parts))
        country, city, region, lat, lon, code, record_type = parts[:7]
        aliases = parts[-1] if len(parts) > 8 else parts[7]
        rows.append((country, city, region, float(lat), float(lon), code, record_type or "regional_capital",
                     [alias for alias in aliases.split(",") if alias]))
    dry = {"Adana", "Adıyaman", "Ankara", "Batman", "Diyarbakır", "Gaziantep", "Iğdır", "Kilis",
           "Konya", "Mardin", "Şanlıurfa", "Siirt"}
    continental = {"Ağrı", "Ardahan", "Bayburt", "Erzincan", "Erzurum", "Kars", "Sivas"}
    aliases = {"İzmir": ["Izmir"], "Şanlıurfa": ["Sanliurfa"], "Diyarbakır": ["Diyarbakir"],
               "Eskişehir": ["Eskisehir"], "Istanbul": ["İstanbul"]}
    for item in TURKEY.split(";"):
        city, lat, lon = item.split(",")
        code = "BSk" if city in dry else "Dfb" if city in continental else "Csa"
        rows.append(("Türkiye", city, f"{city} Province", float(lat), float(lon), code,
                     "regional_capital", aliases.get(city, [])))
    return rows


def build_record(row: tuple[str, str, str, float, float, str, str, list[str]]) -> dict:
    country, city, region, lat, lon, code, record_type, aliases = row
    country_qid, continent, region_type = COUNTRY_META[country]
    title = city
    url = f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
    return {
        "id": f"priority:{country.casefold()}:{region.casefold()}:{city.casefold()}",
        "name": city, "ascii_name": aliases[0] if aliases else None, "aliases": aliases,
        "country": country, "country_qid": country_qid, "continent": continent, "region": continent,
        "administrative_region": region, "administrative_region_type": region_type,
        "administrative_region_qid": None, "latitude": lat, "longitude": lon, "qid": None,
        "wikipedia_title": title, "wikipedia_url": url,
        "climate_classification": KOPPEN_LABELS[code], "climate_classification_label": KOPPEN_LABELS[code],
        "primary_koppen_code": code, "secondary_koppen_codes": [], "climate_group": broad_group(code),
        "climate_classification_source": "curated_english_wikipedia_snapshot",
        "climate_classification_source_metadata": {
            "source_name": "English Wikipedia", "source_language": "en", "source_page_title": title,
            "source_url": url, "source_priority": "english_primary", "source_role": "offline_startup_classification",
            "source_note": "Curated seed retained independently of optional enrichment.",
            "license": "CC BY-SA 4.0", "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "contributors_url": f"{url}?action=history",
        },
        "climate_extraction_status": "curated primary Köppen classification in bundled offline snapshot",
        "extraction_status": "curated primary Köppen classification in bundled offline snapshot",
        "record_type": record_type, "record_scope": "priority_country_regional_capital",
        "provenance": {
            "selection_method": "maintainer-reviewed country seed list; not runtime discovery",
            "administrative_note": "Shared/co-located administrative centers are retained as separate records where applicable.",
            "metadata_source_name": "Wikidata-compatible curated seed", "metadata_license": "CC0 1.0",
            "metadata_license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "climate_source_name": "English Wikipedia", "climate_source_url": url,
            "climate_license": "CC BY-SA 4.0",
            "climate_license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        },
    }


def main() -> None:
    records = [build_record(row) for row in parse_seeds()]
    payload = {
        "schema_version": 1, "generated_at": datetime.now(UTC).isoformat(),
        "coverage": {
            "countries": list(COUNTRY_META),
            "france_scope": "13 metropolitan and 5 overseas regional capitals",
            "turkiye_scope": "all 81 provincial capitals",
            "runtime_network_required": False,
        },
        "source_metadata": {
            "selection_source": "project-maintained curated seed lists",
            "enrichment_sources": ["English Wikipedia", "native-language Wikipedia fallback", "Wikidata fallback"],
            "runtime_network_required": False,
            "licenses": ["CC BY-SA 4.0 (Wikipedia-derived climate descriptions)", "CC0 1.0 (Wikidata-compatible metadata)"],
        },
        "records": records,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} records to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
