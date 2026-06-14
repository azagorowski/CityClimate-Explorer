#!/usr/bin/env python3
"""Fail-fast validation for every curated priority-country regional capital."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.locations import fallback_location_key, load_all_capitals, load_priority_regional_capitals  # noqa: E402
from src.map_view import climate_group  # noqa: E402

REQUIRED = {
    "Egypt": {"Cairo", "Alexandria", "Giza", "Banha", "Port Said", "Suez", "Luxor", "Aswan", "Asyut", "Sohag", "Qena", "Minya", "Beni Suef", "Faiyum", "Zagazig", "Mansoura", "Tanta", "Damanhur", "Damietta", "Ismailia", "El Arish", "Hurghada", "Marsa Matruh", "Kharga", "Shibin El Kom", "Kafr El Sheikh"},
    "Libya": {"Tripoli", "Benghazi", "Misrata", "Sabha", "Tobruk", "Derna", "Bayda", "Zawiya", "Zuwara", "Sirte", "Gharyan", "Murzuq", "Ajdabiya", "Al Khums", "Nalut", "Ubari"},
    "Ukraine": {"Kyiv", "Vinnytsia", "Lutsk", "Dnipro", "Donetsk", "Zhytomyr", "Uzhhorod", "Zaporizhzhia", "Ivano-Frankivsk", "Kropyvnytskyi", "Luhansk", "Lviv", "Mykolaiv", "Odesa", "Poltava", "Rivne", "Sumy", "Ternopil", "Kharkiv", "Kherson", "Khmelnytskyi", "Cherkasy", "Chernivtsi", "Chernihiv", "Simferopol", "Sevastopol"},
    "Iran": {"Tehran", "Karaj", "Isfahan", "Shiraz", "Mashhad", "Tabriz", "Ahvaz", "Qom", "Kermanshah", "Urmia", "Rasht", "Zahedan", "Kerman", "Yazd", "Ardabil", "Bandar Abbas", "Bushehr", "Sanandaj", "Zanjan", "Sari", "Gorgan", "Ilam", "Khorramabad", "Bojnord", "Birjand", "Semnan", "Yasuj", "Qazvin", "Arak", "Shahrekord", "Hamedan"},
    "Switzerland": {
        "Aarau", "Appenzell", "Basel", "Bellinzona", "Bern", "Chur", "Delémont", "Frauenfeld",
        "Fribourg", "Geneva", "Glarus", "Herisau", "Lausanne", "Liestal", "Lucerne", "Neuchâtel",
        "Sarnen", "Schaffhausen", "Schwyz", "Sion", "Solothurn", "St. Gallen", "Stans", "Zug",
        "Zürich", "Altdorf",
    },
    "South Africa": {
        "Bhisho", "Bloemfontein", "Cape Town", "Johannesburg", "Kimberley", "Mahikeng",
        "Mbombela", "Pietermaritzburg", "Polokwane",
    },
    "Austria": {
        "Bregenz", "Eisenstadt", "Graz", "Innsbruck", "Klagenfurt", "Linz", "Salzburg",
        "Sankt Pölten", "Vienna",
    },
    "Angola": {
        "Caxito", "Benguela", "Cuito", "Cabinda", "Menongue", "Ndalatando", "Sumbe", "Ondjiva",
        "Huambo", "Lubango", "Luanda", "Dundo", "Saurimo", "Malanje", "Luena", "Moçâmedes",
        "Uíge", "Mbanza-Kongo",
    },
    "Namibia": {
        "Windhoek", "Gobabis", "Otjiwarongo", "Katima Mulilo", "Keetmanshoop", "Mariental",
        "Opuwo", "Oshakati", "Outapi", "Rundu", "Swakopmund", "Eenhana", "Omuthiya", "Nkurenkuru",
    },
    "Ecuador": {
        "Quito", "Guayaquil", "Cuenca", "Ambato", "Azogues", "Babahoyo", "Esmeraldas",
        "Guaranda", "Ibarra", "Latacunga", "Loja", "Macas", "Machala", "Nueva Loja", "Portoviejo",
        "Puerto Baquerizo Moreno", "Puyo", "Riobamba", "Santa Elena", "Santo Domingo", "Tena",
        "Tulcán", "Zamora", "Francisco de Orellana",
    },
    "Peru": {
        "Lima", "Arequipa", "Ayacucho", "Cajamarca", "Callao", "Cerro de Pasco", "Chiclayo",
        "Chachapoyas", "Cusco", "Huancavelica", "Huánuco", "Huaraz", "Ica", "Iquitos", "Moquegua",
        "Moyobamba", "Piura", "Pucallpa", "Puerto Maldonado", "Puno", "Tacna", "Trujillo", "Tumbes",
        "Abancay", "Huancayo",
    },
    "Chile": {
        "Santiago", "Arica", "Iquique", "Antofagasta", "Copiapó", "La Serena", "Valparaíso",
        "Rancagua", "Talca", "Chillán", "Concepción", "Temuco", "Valdivia", "Puerto Montt",
        "Coyhaique", "Punta Arenas",
    },
    "Japan": {
        "Sapporo", "Aomori", "Morioka", "Sendai", "Akita", "Yamagata", "Fukushima", "Mito",
        "Utsunomiya", "Maebashi", "Saitama", "Chiba", "Tokyo", "Yokohama", "Niigata", "Toyama",
        "Kanazawa", "Fukui", "Kōfu", "Nagano", "Gifu", "Shizuoka", "Nagoya", "Tsu", "Ōtsu",
        "Kyoto", "Osaka", "Kobe", "Nara", "Wakayama", "Tottori", "Matsue", "Okayama", "Hiroshima",
        "Yamaguchi", "Tokushima", "Takamatsu", "Matsuyama", "Kōchi", "Fukuoka", "Saga", "Nagasaki",
        "Kumamoto", "Ōita", "Miyazaki", "Kagoshima", "Naha",
    },
}

EXPECTED_GROUPS = {
    "Quito": "Highland / Mountain",
    "Cusco": "Highland / Mountain",
    "Puno": "Highland / Mountain",
    "Punta Arenas": "Temperate",
    "Sapporo": "Continental",
    "Windhoek": "Dry / Arid",
    "Walvis Bay": "Dry / Arid",
    "Swakopmund": "Dry / Arid",
}


def main() -> int:
    records = load_priority_regional_capitals()
    errors: list[str] = []
    names_by_country: dict[str, set[str]] = {}
    by_name = {row["name"]: row for row in records}
    qids: set[str] = set()
    fallback_keys: set[tuple[str, str, str]] = set()
    for row in records:
        names_by_country.setdefault(row["country"], set()).add(row["name"])
        for field in ("id", "country", "administrative_region", "administrative_region_type", "latitude", "longitude"):
            if row.get(field) in (None, ""):
                errors.append(f"{row.get('name')}: missing {field}")
        if row.get("climate_classification") in (None, "", "Unknown") and not row.get("climate_extraction_status"):
            errors.append(f"{row['name']}: climate has neither classification nor logged reason")
        if row.get("record_scope") != "priority_country_regional_capital":
            errors.append(f"{row['name']}: incorrect record scope")
        qid = str(row.get("qid") or "").strip()
        fallback = fallback_location_key(row)
        if qid and qid in qids:
            errors.append(f"{row['name']}: duplicate city QID {qid}")
        if fallback in fallback_keys:
            errors.append(f"{row['name']}: duplicate fallback identity {fallback}")
        qids.add(qid) if qid else None
        fallback_keys.add(fallback)

    for country, expected in REQUIRED.items():
        missing = expected - names_by_country.get(country, set())
        if missing:
            errors.append(f"{country}: missing {sorted(missing)}")
    if len(names_by_country.get("Japan", set())) != 47:
        errors.append(f"Japan: expected 47 prefectural capitals, found {len(names_by_country.get('Japan', set()))}")

    for city, expected_group in EXPECTED_GROUPS.items():
        actual = climate_group(by_name.get(city))
        if actual != expected_group:
            errors.append(f"{city}: expected {expected_group}, found {actual}")

    runtime = load_all_capitals()
    runtime_keys = {fallback_location_key(row) for row in runtime}
    for country, names in REQUIRED.items():
        for name in names:
            source = next((row for row in records if row["country"] == country and row["name"] == name), None)
            if source and fallback_location_key(source) not in runtime_keys:
                # National/regional overlaps merge by city+country and intentionally
                # have no regional fallback key in the authoritative national row.
                if not any(row["country"] == country and row["name"] == name for row in runtime):
                    errors.append(f"runtime merge removed required city: {name}, {country}")

    bogota = next((row for row in runtime if row["name"] == "Bogotá"), None)
    if climate_group(bogota) != "Highland / Mountain":
        errors.append("Bogotá regression: expected Highland / Mountain")

    if errors:
        print("PRIORITY REGIONAL-CAPITAL VALIDATION FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("Priority regional-capital validation passed")
    print(f"Records: {len(records)}; by country: {dict(sorted(Counter(r['country'] for r in records).items()))}")
    print(f"Runtime records: {len(runtime)}; missing required: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
