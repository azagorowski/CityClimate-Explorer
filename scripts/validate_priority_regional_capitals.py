#!/usr/bin/env python3
"""Fail-fast validation for curated priority-country regional capitals."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.locations import load_all_capitals, load_priority_regional_capitals  # noqa: E402
from src.map_view import climate_group  # noqa: E402

REQUIRED = {
    "Poland": {"Białystok", "Bydgoszcz", "Toruń", "Gdańsk", "Gorzów Wielkopolski", "Zielona Góra",
               "Katowice", "Kielce", "Kraków", "Lublin", "Łódź", "Olsztyn", "Opole", "Poznań",
               "Rzeszów", "Szczecin", "Warsaw", "Wrocław"},
    "Germany": {"Berlin", "Bremen", "Dresden", "Düsseldorf", "Erfurt", "Hamburg", "Hanover", "Kiel",
                "Magdeburg", "Mainz", "Munich", "Potsdam", "Saarbrücken", "Schwerin", "Stuttgart", "Wiesbaden"},
    "Spain": {"Madrid", "Barcelona", "Valencia", "Seville", "Zaragoza", "Mérida", "Santiago de Compostela",
              "Oviedo", "Santander", "Logroño", "Pamplona", "Vitoria-Gasteiz", "Valladolid", "Toledo",
              "Murcia", "Palma", "Las Palmas de Gran Canaria", "Santa Cruz de Tenerife", "Ceuta", "Melilla"},
    "France": {"Paris", "Lyon", "Marseille", "Toulouse", "Bordeaux", "Nantes", "Rennes", "Lille",
               "Strasbourg", "Dijon", "Orléans", "Rouen", "Ajaccio", "Basse-Terre", "Cayenne",
               "Fort-de-France", "Saint-Denis", "Mamoudzou"},
    "Norway": {"Oslo", "Bergen", "Stavanger", "Trondheim", "Tromsø", "Bodø", "Vadsø", "Kristiansand",
               "Drammen", "Lillehammer", "Molde", "Steinkjer", "Skien", "Tønsberg", "Hamar", "Leikanger",
               "Hermansverk", "Ålesund"},
    "Sweden": {"Stockholm", "Gothenburg", "Malmö", "Uppsala", "Linköping", "Örebro", "Västerås", "Luleå",
               "Umeå", "Östersund", "Karlstad", "Falun", "Gävle", "Härnösand", "Jönköping", "Kalmar",
               "Karlskrona", "Kristianstad", "Nyköping", "Växjö", "Visby", "Halmstad"},
    "Finland": {"Helsinki", "Turku", "Tampere", "Oulu", "Rovaniemi", "Kuopio", "Jyväskylä", "Lahti",
                "Pori", "Vaasa", "Joensuu", "Hämeenlinna", "Mikkeli", "Seinäjoki", "Kokkola", "Kajaani",
                "Mariehamn", "Lappeenranta"},
}
SUBARCTIC = {"Tromsø", "Vadsø", "Rovaniemi", "Luleå", "Umeå", "Östersund"}


def main() -> int:
    records = load_priority_regional_capitals()
    errors: list[str] = []
    names_by_country: dict[str, set[str]] = {}
    for row in records:
        names_by_country.setdefault(row["country"], set()).add(row["name"])
        for field in ("id", "country", "administrative_region", "administrative_region_type", "latitude", "longitude"):
            if row.get(field) in (None, ""):
                errors.append(f"{row.get('name')}: missing {field}")
        if row.get("climate_classification") in (None, "", "Unknown") and not row.get("climate_extraction_status"):
            errors.append(f"{row['name']}: climate has neither classification nor logged reason")
        if row.get("record_scope") != "priority_country_regional_capital":
            errors.append(f"{row['name']}: incorrect record scope")
    for country, expected in REQUIRED.items():
        missing = expected - names_by_country.get(country, set())
        if missing:
            errors.append(f"{country}: missing {sorted(missing)}")
    turkey = names_by_country.get("Türkiye", set())
    if len(turkey) != 81:
        errors.append(f"Türkiye: expected 81 provincial capitals, found {len(turkey)}")
    for row in records:
        if row["name"] in SUBARCTIC and (row.get("primary_koppen_code") != "Dfc" or climate_group(row) != "Continental"):
            errors.append(f"{row['name']}: expected primary Dfc / Continental")
    runtime = load_all_capitals()
    runtime_names = {row["name"] for row in runtime}
    expected_all = set().union(*REQUIRED.values(), turkey)
    missing_runtime = expected_all - runtime_names
    if missing_runtime:
        errors.append(f"runtime merge removed required cities: {sorted(missing_runtime)}")
    for must_have in ("Kraków", "Stavanger"):
        if must_have not in runtime_names:
            errors.append(f"runtime dataset missing regression city {must_have}")
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
