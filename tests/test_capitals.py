from src.capitals import (
    SUPPORTED_CONTINENTS,
    countries_for_continent,
    country_identifier,
    load_preloaded_capitals,
    merge_city_datasets,
)
from src.config import DEFAULT_POPULATION_THRESHOLD


def test_startup_capitals_load_from_local_dataset(monkeypatch):
    def fail_request(*args, **kwargs):  # pragma: no cover - should never be called
        raise AssertionError("startup capital loading must not call Wikidata")

    monkeypatch.setattr("urllib.request.urlopen", fail_request)

    capitals = load_preloaded_capitals()

    assert len(capitals) >= 190
    assert {"name", "country", "latitude", "longitude", "qid"}.issubset(capitals[0])
    assert {city["region"] for city in capitals} & set(SUPPORTED_CONTINENTS)


def test_small_capitals_remain_included_below_additional_city_threshold():
    capitals = load_preloaded_capitals()
    by_name = {city["name"]: city for city in capitals}

    for name in ["Andorra la Vella", "San Marino", "Vaduz", "Monaco", "Ngerulmud", "Funafuti", "Malé", "Victoria"]:
        assert name in by_name
        population = by_name[name].get("population")
        assert population is None or population < DEFAULT_POPULATION_THRESHOLD


def test_capitals_not_filtered_by_missing_population_and_unknown_climate():
    capitals = load_preloaded_capitals()

    missing_population = [city for city in capitals if city.get("population") is None]
    unknown_climate = [city for city in capitals if city.get("climate_classification") == "Unknown"]

    assert missing_population
    assert unknown_climate
    assert any(city["name"] == "Funafuti" for city in missing_population)


def test_country_dropdown_options_follow_selected_continent():
    capitals = load_preloaded_capitals()

    europe = countries_for_continent(capitals, "Europe")
    oceania = countries_for_continent(capitals, "Oceania")

    assert "France" in europe
    assert "Palau" not in europe
    assert "Palau" in oceania
    assert countries_for_continent(capitals, None) == []


def test_country_identifier_returns_country_qid_when_available():
    capitals = load_preloaded_capitals()

    assert country_identifier(capitals, "France") == {"country": "France", "country_qid": "Q142"}


def test_merge_city_datasets_deduplicates_by_qid_and_keeps_capital_first():
    capitals = [{"qid": "Q90", "name": "Paris", "country": "France", "source": "preloaded_capitals"}]
    additional = [
        {"qid": "Q90", "name": "Paris", "country": "France", "source": "wikidata"},
        {"qid": "Q64", "name": "Berlin", "country": "Germany", "source": "wikidata"},
    ]

    merged = merge_city_datasets(capitals, additional)

    assert [city["qid"] for city in merged] == ["Q90", "Q64"]
    assert merged[0]["source"] == "preloaded_capitals"


def test_merge_city_datasets_deduplicates_by_name_country_when_qid_missing():
    capitals = [{"name": "Ngerulmud", "country": "Palau", "source": "preloaded_capitals"}]
    additional = [{"qid": "Q516978", "name": "ngerulmud", "country": "palau", "source": "wikidata"}]

    merged = merge_city_datasets(capitals, additional)

    assert len(merged) == 1
    assert merged[0]["source"] == "preloaded_capitals"


def test_merge_city_datasets_fills_missing_capital_fields_from_duplicate_additional_city():
    capitals = [{"qid": "Q1780", "name": "Bratislava", "country": "Slovakia", "population": None, "source": "preloaded_capitals"}]
    additional = [{"qid": "Q1780", "name": "Bratislava", "country": "Slovakia", "population": 475_503, "wikipedia_title": "Bratislava", "source": "wikidata"}]

    merged = merge_city_datasets(capitals, additional)

    assert len(merged) == 1
    assert merged[0]["source"] == "preloaded_capitals"
    assert merged[0]["population"] == 475_503
    assert merged[0]["wikipedia_title"] == "Bratislava"


def test_all_bundled_sovereign_state_capitals_validate():
    from scripts.validate_capitals import validate_capitals

    assert validate_capitals() == []


def test_preloaded_capital_climate_comes_from_local_cache_with_source_metadata():
    capitals = load_preloaded_capitals()
    bogota = next(city for city in capitals if city["name"] == "Bogotá")

    assert bogota["climate_classification"] == "Cfb"
    assert bogota["climate_classification_label"] == "oceanic climate"
    assert bogota["climate_classification_source_metadata"]["source_priority"] == "english_primary"


def test_filter_optional_non_capital_cities_limits_and_excludes_capital():
    from src.capitals import filter_optional_non_capital_cities

    capitals = [{"qid": "Q2841", "name": "Bogotá", "country": "Colombia", "source": "preloaded_capitals"}]
    additional = [{"qid": "Q2841", "name": "Bogotá", "country": "Colombia", "population": 7_400_000}]
    additional += [
        {"qid": f"Q{i}", "name": f"City {i}", "country": "Colombia", "population": 1_000_000 - i}
        for i in range(20)
    ]

    filtered = filter_optional_non_capital_cities(capitals, additional, limit=50)

    assert len(filtered) == 10
    assert all(city["name"] != "Bogotá" for city in filtered)


def test_every_preloaded_capital_has_an_english_wikipedia_title_or_url():
    capitals = load_preloaded_capitals()

    assert capitals
    assert all(city.get("wikipedia_title") or city.get("wikipedia_url") for city in capitals)
